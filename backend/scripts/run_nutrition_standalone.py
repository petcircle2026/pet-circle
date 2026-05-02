"""
Standalone nutrition analysis — no database required.

Runs the COMBINED_MEAL_SYSTEM_PROMPT from nutrition_service.py against a
manually-specified diet and prints:
  1. The exact user-prompt sent to the LLM
  2. The raw LLM output
  3. Parsed JSON summary

Usage:
  cd backend
  ANTHROPIC_API_KEY=sk-ant-... python scripts/run_nutrition_standalone.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# ─── Load env ────────────────────────────────────────────────────────────────
import re as _re

ENV_FILE = Path(__file__).parent.parent / "envs" / ".env.production"
if not os.environ.get("OPENAI_API_KEY") and ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not _re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
            continue
        # Strip inline comments (e.g. "value  # comment")
        value = _re.sub(r"\s+#.*$", "", value).strip()
        if key not in os.environ:
            os.environ[key] = value

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY not set.")
    print("Run: OPENAI_API_KEY=sk-... python scripts/run_nutrition_standalone.py")
    sys.exit(1)

# ─── Pet profile (edit as needed) ────────────────────────────────────────────
PET = {
    "species": "dog",
    "breed": "Labrador Retriever",
    "age": "3 years",
    "weight_kg": 28.0,
    "gender": "male",
    "conditions": [],
}

# ─── Diet items ──────────────────────────────────────────────────────────────
# Each item: label, type ("packaged" | "homemade"), portion_g (daily total) or detail (free-text qty)
DIET_ITEMS = [
    {
        "label": "Royal Canin Adult kibble",
        "type": "packaged",
        "portion_g": 150,       # 50g × 3 times a day
        "detail": "50g × 3 times a day",
    },
    {
        "label": "Small treat",
        "type": "packaged",
        "portion_g": None,
        "detail": "small treat in the evening",
    },
]

# ─── System prompt (copied verbatim from nutrition_service.py) ────────────────
COMBINED_MEAL_SYSTEM_PROMPT = (
    "You are a board-certified veterinary nutritionist.\n"
    "Your task: Given food items, pet details, and optionally user-provided quantities, estimate\n"
    "DAILY nutritional intake and identify the most important nutritional gaps.\n\n"
    "-----------------------------------\n"
    "STEP 1 — RESOLVE FOOD IDENTITY\n"
    "-----------------------------------\n"
    "- Identify the most likely specific product based on: food name, species, age (puppy / adult / senior)\n"
    "  Example: \"Pedigree\" + adult dog → Pedigree Adult Dog Food\n"
    "- If multiple variants are possible, choose the most common one for that species and age,\n"
    "  and note it in resolved_name. Reduce product_confidence only — do NOT reduce overall\n"
    "  analysis confidence if serving size can still be determined via brand feeding guidelines (see Step 2 Case B).\n"
    "- If product identity cannot be resolved to any specific brand at all, reduce confidence and apply the Fail-Safe.\n"
    "- Before determining life stage, estimate age-to-life-stage mapping using breed-specific thresholds —\n"
    "  large and giant breeds are considered senior earlier (6–7 years) than small breeds (10–11 years).\n"
    "- If user mentions a vet-prescribed diet, extract and store the prescription_context\n"
    "  (e.g., \"low protein for kidney disease\", \"hypoallergenic for allergies\").\n"
    "- This context must carry forward into gap analysis and improvement framing.\n\n"
    "-----------------------------------\n"
    "STEP 2 — DETERMINE SERVING SIZE\n"
    "-----------------------------------\n\n"
    "CASE A: USER PROVIDED QUANTITY (any food)\n"
    "- Use EXACTLY the user-provided quantity (e.g., \"2 cups/day\", \"1 bowl/day\").\n"
    "- Do NOT override, scale, or reinterpret it.\n\n"
    "CASE B: COMMERCIAL / PACKAGED FOOD, NO QUANTITY PROVIDED\n"
    "- Use ONLY official brand feeding guidelines.\n"
    "- Use pet weight and age ONLY to select the correct feeding range.\n"
    "- Choose a reasonable midpoint within that range.\n"
    "- Do NOT invent or extrapolate beyond brand guidance.\n\n"
    "⚠ If the pet's age and weight are provided, this is sufficient to determine serving size from brand\n"
    "feeding guidelines. Set confidence ≥ 0.75 in this case. Do NOT treat the absence of a user-provided\n"
    "quantity as missing serving size — brand guidelines ARE the serving size source for commercial food.\n\n"
    "CASE C: HOMEMADE / GENERIC FOOD, NO QUANTITY PROVIDED\n"
    "- DO NOT estimate or assume any serving size.\n"
    "- Mark portion as UNKNOWN.\n"
    "If serving size cannot be determined with confidence:\n"
    "- Set confidence < 0.6.\n"
    "- RETURN NO ANALYSIS (see Fail-Safe).\n"
    "⚠ This does NOT apply to Case B when age and weight are provided. Commercial packaged food with\n"
    "known brand guidelines never has a \"missing\" serving size if the pet's weight and age are available.\n\n"
    "-----------------------------------\n"
    "STEP 3 — MIXED DIET HANDLING\n"
    "-----------------------------------\n\n"
    "If BOTH commercial food AND homemade food are present:\n"
    "Treat commercial food as the PRIMARY diet anchor:\n"
    "- Use it for calories_per_day and macronutrient percentages.\n"
    "For homemade food WITHOUT quantity:\n"
    "- DO NOT include in calories or macronutrient calculations.\n"
    "- ONLY use it for qualitative micronutrient signals if possible.\n"
    "If homemade food HAS quantity:\n"
    "- Include it fully in all calculations.\n\n"
    "-----------------------------------\n"
    "STEP 4 — NUTRITION ESTIMATION\n"
    "-----------------------------------\n"
    "- Estimate TOTAL DAILY intake based on determined serving size.\n"
    "- Ensure values are realistic and internally consistent.\n"
    "- Prevent extreme or biologically impossible outputs.\n"
    "- Total calories must fall within realistic daily intake ranges.\n"
    "- For protein_pct, fat_pct, carbs_pct, fibre_pct: express each as\n"
    "  % of the pet's DAILY REQUIREMENT met by this diet (NOT % of calories).\n"
    "  Example: if a 22kg adult dog needs 50g protein/day and the diet provides 33g → protein_pct = 66.\n"
    "  Values can exceed 100 if the diet overshoots the requirement.\n\n"
    "-----------------------------------\n"
    "STEP 5 — SHOW WARNING FLAG\n"
    "-----------------------------------\n\n"
    "Set show_warning: true ONLY if ANY of the following apply:\n"
    "- Diet includes homemade or generic food (with or without quantity).\n"
    "- Diet is mixed (commercial + homemade).\n"
    "- Commercial food was identified without an exact SKU (brand-level match only).\n"
    "- Confidence < 0.6.\n\n"
    "Set show_warning: false if:\n"
    "- Diet is 100% commercial food AND exact SKU was matched with confidence.\n\n"
    "When show_warning is true, select warning_message based on diet type:\n"
    "  Homemade / generic food only:\n"
    "    \"Estimates vary by portion, cooking method and ingredient type.\"\n"
    "  Mixed diet (commercial + homemade):\n"
    "    \"Commercial values from brand data; home-cooked portions are approximated.\"\n"
    "  Commercial food, brand-level match only (no exact SKU):\n"
    "    \"Values based on brand averages. May vary by product variant.\"\n"
    "  Confidence < 0.6:\n"
    "    \"Insufficient data for diet analysis. Share food portions and/or brand SKU on WhatsApp.\"\n\n"
    "When show_warning is false:\n"
    "  Omit warning_message from output entirely.\n\n"
    "-----------------------------------\n"
    "STEP 6 — MICRONUTRIENT GAP ANALYSIS\n"
    "-----------------------------------\n\n"
    "SUPPLEMENT COVERAGE RULE (Check First):\n"
    "Before assigning any nutrient status, check the supplements input.\n"
    "For any nutrient covered by a supplement, assign status \"sufficient\" with a low severity_score (0.1–0.2).\n"
    "Do NOT flag it as a gap and do NOT recommend it in top_improvements.\n\n"
    "- Identify micronutrient gaps dynamically based on pet nutritional requirements, current diet\n"
    "  composition, and pet life stage.\n\n"
    "Life stage MUST influence severity scoring:\n"
    "- Puppies: prioritise calcium, phosphorus, omega_3 (DHA), zinc.\n"
    "- Adults: prioritise omega_3, taurine, fibre, zinc.\n"
    "- Seniors: prioritise omega_3, glucosamine, vitamin_d3, fibre.\n\n"
    "Use ONLY this controlled list of nutrient names:\n"
    "  omega_3, omega_6, vitamin_e, vitamin_d3, glucosamine, calcium, phosphorus, iron, zinc, taurine, fibre\n\n"
    "- For each nutrient, assign ONLY one of: \"sufficient\", \"low\", \"missing\".\n"
    "- DO NOT output \"unknown\" under any condition.\n"
    "- DO NOT include nutrients where status cannot be confidently determined.\n"
    "- DO NOT output numeric values, units, or requirements for micronutrients.\n"
    "- Micronutrients are strictly qualitative signals.\n\n"
    "Assign a severity_score (0–1) based on:\n"
    "- Deficiency severity (missing > low > sufficient).\n"
    "- Relevance to pet conditions and life stage.\n"
    "- Confidence in assessment.\n\n"
    "If a nutrient gap is intentional due to a vet-prescribed diet:\n"
    "- Do NOT increase severity_score for that nutrient.\n"
    "- Add prescribed: true to that nutrient's output.\n\n"
    "-----------------------------------\n"
    "STEP 7 — SELECT TOP 3 PRIORITY IMPROVEMENTS\n"
    "-----------------------------------\n\n"
    "Identify the TOP 3 most important improvements across ALL of:\n"
    "- Calorie adequacy (is total intake significantly above or below daily requirement?).\n"
    "- Macronutrients (protein, fat, carbs, fibre — flag only if meaningfully off target).\n"
    "- Micronutrients (from gap analysis, life-stage weighted).\n\n"
    "Rank by clinical importance to this specific pet.\n"
    "For each improvement:\n"
    "- title: short label (e.g. \"Protein too low\", \"Calcium missing\", \"Calories under target\").\n"
    "- detail: ONE line only — specific, actionable, no more than 15 words.\n"
    "- severity: \"high\" | \"medium\" | \"prescribed\".\n\n"
    "If an improvement relates to a prescribed nutrient gap:\n"
    "- DO NOT suppress it — include it.\n"
    "- Set severity to \"prescribed\".\n"
    "- Frame detail neutrally, e.g. \"Low by prescription — continue monitoring with your vet\".\n"
    "- Never suggest correcting a prescribed gap.\n\n"
    "- DO NOT pad to 3 if fewer than 3 genuine issues exist.\n"
    "- DO NOT include improvements for nutrients already marked sufficient.\n"
    "top_improvements must span calories, macros, AND micros — do not pull from one category only.\n\n"
    "-----------------------------------\n"
    "CRITICAL RULES\n"
    "-----------------------------------\n\n"
    "- NEVER estimate serving size arbitrarily.\n"
    "- NEVER assume portion size for homemade food.\n"
    "- NEVER scale portions beyond brand guidelines.\n"
    "- NEVER include homemade food in calorie or macro calculations unless quantity is provided.\n"
    "- NEVER fabricate precision where data is missing.\n"
    "- NEVER suggest correcting a gap that is vet-prescribed.\n"
    "- Maintain internal consistency across all outputs.\n"
    "- top_improvements must span calories, macros, AND micros — do not pull from one category only.\n"
    "- detail in top_improvements must be ONE line, max 15 words, specific and actionable.\n\n"
    "-----------------------------------\n"
    "FAIL-SAFE\n"
    "-----------------------------------\n\n"
    "Return INSUFFICIENT_DATA ONLY IF no food in the list has determinable identity AND serving size.\n"
    "If at least ONE commercial food can be analysed via brand feeding guidelines, return results based\n"
    "on what is known — do NOT return INSUFFICIENT_DATA because homemade or generic add-ons lack quantities.\n\n"
    "Trigger INSUFFICIENT_DATA only when ALL foods in the list meet one of these conditions:\n"
    "  (a) Cannot be resolved to any specific brand at all, OR\n"
    "  (b) Are homemade/generic with no user-provided quantity.\n\n"
    "⚠ Homemade or generic foods without quantities do NOT trigger this fail-safe.\n"
    "  They follow Case C rules: excluded from calorie/macro calculations, show_warning set to true.\n"
    "⚠ For commercial packaged food where the pet's age and weight are provided, serving size is NEVER\n"
    "  treated as missing. Brand feeding guidelines apply and the Fail-Safe does not trigger on this basis alone.\n\n"
    '{"confidence": <value>, "show_warning": true, '
    '"warning_message": "Insufficient data for diet analysis. Share food portions and/or brand SKU on WhatsApp.", '
    '"error": "INSUFFICIENT_DATA"}\n\n'
    "-----------------------------------\n"
    "OUTPUT FORMAT\n"
    "-----------------------------------\n\n"
    "Return ONLY valid JSON with these exact keys:\n\n"
    "{\n"
    '  "resolved_name": string,\n'
    '  "confidence": float (0-1),\n'
    '  "serving_description": string,\n'
    '  "prescription_context": string (omit if not applicable),\n'
    '  "show_warning": boolean,\n'
    '  "warning_message": string (omit if show_warning is false),\n'
    '  "calories_per_day": int,\n'
    '  "calorie_target": int,\n'
    '  "calorie_gap_pct": int (positive = over, negative = under),\n'
    '  "protein_pct": float (% of daily protein REQUIREMENT met, e.g. 65 means 65% of need — NOT % of calories),\n'
    '  "fat_pct": float (% of daily fat REQUIREMENT met),\n'
    '  "carbs_pct": float (% of daily carbohydrate REQUIREMENT met),\n'
    '  "fibre_pct": float (% of daily fibre REQUIREMENT met),\n'
    '  "micronutrient_gaps": [\n'
    '    {\n'
    '      "name": string,\n'
    '      "status": "sufficient" | "low" | "missing",\n'
    '      "severity_score": float (0-1),\n'
    '      "prescribed": boolean (omit if false)\n'
    '    }\n'
    "  ],\n"
    '  "top_improvements": [\n'
    '    {\n'
    '      "title": string,\n'
    '      "detail": string (ONE line, max 15 words),\n'
    '      "severity": "high" | "medium" | "prescribed"\n'
    '    }\n'
    "  ]\n"
    "}\n\n"
    "CRITICAL:\n"
    "- severity_score MUST be a float between 0.0 and 1.0 (e.g. 0.72, NOT 7 or 72)\n"
    "- top_improvements MUST be an array (empty array [] if no improvements needed)\n"
    "- Return ONLY the JSON object — no text, notes, or recommendations after the closing brace\n"
    "- No extra fields beyond the schema\n"
    "- No markdown, no code fences, no explanation"
)


def build_user_prompt(pet: dict, items: list[dict]) -> str:
    parts = []
    if pet.get("species"):
        parts.append(f"Species: {pet['species']}")
    if pet.get("breed"):
        parts.append(f"Breed: {pet['breed']}")
    if pet.get("age"):
        parts.append(f"Age: {pet['age']}")
    if pet.get("weight_kg"):
        parts.append(f"Weight: {float(pet['weight_kg']):.1f} kg")
    if pet.get("gender"):
        parts.append(f"Gender: {pet['gender']}")
    if pet.get("conditions"):
        parts.append(f"Conditions: {', '.join(pet['conditions'])}")

    parts.append("\nDiet items (complete daily intake):")
    for i, item in enumerate(items, 1):
        line = f"{i}. {item['label']} (type: {item['type']})"
        if item.get("portion_g"):
            line += f" -- Daily portion: {item['portion_g']}g"
        if item.get("detail") and str(item["detail"]).strip():
            line += f" -- User-provided quantity: {item['detail'].strip()}"
        if not item.get("portion_g") and not item.get("detail"):
            line += " -- Quantity: not specified"
        parts.append(line)

    return "\n".join(parts)


def strip_fences(raw: str) -> str:
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[-1] if "\n" in s else s[3:]
        if s.endswith("```"):
            s = s[: s.rfind("```")]
    return s.strip()


async def main():
    import openai

    user_prompt = build_user_prompt(PET, DIET_ITEMS)

    print("=" * 70)
    print("USER PROMPT SENT TO LLM")
    print("=" * 70)
    print(user_prompt)

    print("\n" + "=" * 70)
    print("CALLING LLM (gpt-4.1-mini)...")
    print("=" * 70)

    client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    response = await client.chat.completions.create(
        model="gpt-4.1-mini",
        max_tokens=1024,
        temperature=0.0,
        messages=[
            {"role": "system", "content": COMBINED_MEAL_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    raw = response.choices[0].message.content

    print("\n" + "=" * 70)
    print("RAW LLM OUTPUT")
    print("=" * 70)
    print(raw)

    print("\n" + "=" * 70)
    print("PARSED RESULT")
    print("=" * 70)
    try:
        parsed = json.loads(strip_fences(raw))
        print(json.dumps(parsed, indent=2))

        print("\n" + "-" * 70)
        print("SUMMARY")
        print("-" * 70)
        if parsed.get("error"):
            print(f"  INSUFFICIENT_DATA: {parsed.get('message', parsed.get('warning_message', ''))}")
        else:
            print(f"  resolved_name    : {parsed.get('resolved_name')}")
            print(f"  confidence       : {parsed.get('confidence')}")
            print(f"  serving_desc     : {parsed.get('serving_description')}")
            print(f"  show_warning     : {parsed.get('show_warning')}")
            if parsed.get("warning_message"):
                print(f"  warning_message  : {parsed.get('warning_message')}")
            print(f"  calories_per_day : {parsed.get('calories_per_day')}")
            print(f"  calorie_target   : {parsed.get('calorie_target')}")
            print(f"  calorie_gap_pct  : {parsed.get('calorie_gap_pct')}%")
            print(f"  protein_pct      : {parsed.get('protein_pct')}%  of daily requirement")
            print(f"  fat_pct          : {parsed.get('fat_pct')}%  of daily requirement")
            print(f"  carbs_pct        : {parsed.get('carbs_pct')}%  of daily requirement")
            print(f"  fibre_pct        : {parsed.get('fibre_pct')}%  of daily requirement")
            gaps = parsed.get("micronutrient_gaps", [])
            print(f"\n  micronutrient gaps ({len(gaps)}):")
            for g in gaps:
                print(f"    * {g.get('name'):15} {g.get('status'):10} severity={g.get('severity_score')}")
            improvements = parsed.get("top_improvements", [])
            print(f"\n  top improvements ({len(improvements)}):")
            for imp in improvements:
                print(f"    [{imp.get('severity'):10}] {imp.get('title')}: {imp.get('detail')}")
    except json.JSONDecodeError as exc:
        print(f"[WARNING] Could not parse as JSON: {exc}")
        print("Raw output above.")


asyncio.run(main())
