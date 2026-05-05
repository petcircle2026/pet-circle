# Gap Analysis — Implementation Status

Sources: `Health_Condition_040526_vf.docx.pdf` (PDF) + `Code_Fixes_V3 (1).xlsx` (Excel)

---

## SECTION 1 — Already Implemented (confirmed in codebase, no action needed)

| Gap | What was confirmed |
|-----|--------------------|
| Gap 3 — recurrence_watch DB column | `Condition` model line 66, `AggregatedCondition` line 51 |
| Gap 4 — canonical_condition_id | `AggregatedCondition` line 54 |
| Gap 5 — DB migration for recurrent enum | Model comment + default at line 51 |
| Gap 6 — health_trends_service recurrent filter | `_ASK_VET_CONDITION_TYPES = {"chronic", "episodic", "recurrent"}` at line 33; UNTREATED banner line 623 |
| Gap 7 — condition_service recurrent logic + constants | `if cond.condition_type in {"chronic", "recurrent"}` at line 426; constants imported at line 24 |
| Gap 12 — soft_resolution vs vet_resolved | Populated at `AggregatedCondition:50` by aggregation service |
| Gap 14 — Aggregation service | Fully implemented in `condition_aggregation_service.py` |

---

## SECTION 2 — Ready to Implement (fully specified by Excel and/or PDF)

All information needed to write the code is present. No open questions.

### Gap 1 — "acute" vs "episodic" in extraction prompt and service constant
**Source:** Excel → Changes_across_files  
**Fix:**
- `ai_insights_service.py:709` — change `"type": "chronic | recurrent | acute"` to `"type": "chronic | recurrent | episodic"`
- `gpt_extraction.py` extraction prompt — change valid values listed for `condition_type` from `chronic | acute | episodic | recurrent` to `chronic | episodic | recurrent`; add instruction that a single episode with no prior history = `episodic`
- `gpt_extraction.py` collapse logic — remove the `recurrent → episodic` collapse; keep only `unknown/invalid → episodic` as fallback; `acute → episodic` collapse can remain as legacy safety net per Excel

---

### Gap 2 — Monitoring window: wrong field name and wrong threshold
**Source:** Excel → Condition_Type_Status sheet  
**Fix in `ai_insights_service.py:925` and `precompute_service.py:250`:**
- Field: use `episode_date` (not `last_record_date`) for the no-medication path
- Threshold: `<= 30 days → monitoring`, `> 30 days → resolved` (change 45 → 30 everywhere)
- Full no-medication status logic:
  - `(today − episode_date) <= 30 days` → `monitoring`
  - `(today − episode_date) > 30 days` → `resolved`

---

### Gap 8 / Gap 18 — Extraction prompt still emits "acute"
**Source:** Excel → Changes_across_files  
**Fix in `gpt_extraction.py`:**
- Remove `acute` from valid `condition_type` values in the extraction instruction
- Remove the collapse block that maps `recurrent → episodic` (this was destroying recurrent before it reached DB)
- Store all three values — `chronic | episodic | recurrent` — as valid DB values
- Keep `unknown/invalid → episodic` fallback only

---

### Gap 9 — FIX_B: null end_date medication treated as always active
**Source:** Excel → FIX_B_Active_Medication sheet  
**Fix in `precompute_service.py:281` and `ai_insights_service.py:955`:**
- Do not include null-end-date medications unconditionally
- Filter in Python using `is_medication_active()` (already correct in `condition_aggregation_service.py`)
- Active rule: `end_date IS NULL AND (today − episode_dates[latest]) <= 30 days`
- Inactive rule: `end_date IS NULL AND (today − episode_dates[latest]) > 30 days`

---

### Gap 11 — Case 1 (zero records) short-circuits GPT, no breed insight
**Source:** PDF → Corner Cases, Case 1 (pages 7–8)  
**Fix in `ai_insights_service.py:754–769`:**
- Remove the early return that returns a hardcoded generic upload nudge before any GPT call
- `pet_profile` already contains `breed`, `age_years`, `life_stage` — pass these to GPT
- GPT will produce the Case 1 output: opens with "No health records have been shared for [name] yet." then surfaces a breed- and age-specific proactive watch (e.g. MVD check for Cavaliers, joint screen for senior Labs)

---

### Gap 13 / Gap 17 — Monitoring data never passed to GPT payload
**Source:** Excel → Aggregation layer (monitoring field merge definitions)  
**Fix in `precompute_service.py:215–235` and `ai_insights_service.py:890–910`:**
- Add `ac.monitoring` to the SQL SELECT for aggregated conditions
- Add `"monitoring": row.monitoring or []` to each condition entry in `conditions_payload`
- Each monitoring item must carry `name` and `recheck_due_date` (MAX per monitoring type as defined in Aggregation layer sheet)

---

### Gap 15 — Spurious "active" state in no-medication compute_status
**Source:** Excel → Condition_Type_Status sheet (only two states exist: monitoring / resolved for no-medication path)  
**Fix in `condition_aggregation_service.py:179–191`:**
- Remove the `active` branch (`<= 30 days → active`)
- Correct two-state logic: `<= 30 days → monitoring`, `> 30 days → resolved`
- All three implementations (aggregation, precompute, ai_insights) must agree on 30 days with no active state for the no-medication case

---

### Gap 16 — DietItem.is_active filter missing
**Source:** PDF describes `current_diet[]` as "active diet items" (implied filter)  
**Fix in `precompute_service.py:322` and `ai_insights_service.py:993`:**
- Add `DietItem.is_active == True` to the diet query filter (currently filters only by `pet_id`)

---

### Item A / Gap 10 — Medication dedup: wrong sort column and NULLS direction
**Source:** Excel → Aggregation layer ("per medication name — take MAX end_date")  
**Fix in `precompute_service.py` and `ai_insights_service.py` medication dedup SQL:**
- Change `ORDER BY LOWER(cm.name), c.diagnosed_at DESC NULLS LAST`
- To `ORDER BY LOWER(cm.name), cm.end_date DESC NULLS FIRST`
- Rationale: null end_date = lifelong prescription = must win the dedup; `c.diagnosed_at` is the condition's first diagnosis date, not the prescription date — wrong column for recurrent conditions with multiple courses

---

### Item B — ConditionMedication.status property ignores FIX_B rule
**Source:** Excel → FIX_B_Active_Medication sheet  
**Fix in `condition_medication.py:51`:**
- Current: returns `"active"` for every null-end-date row unconditionally
- Correct: consult `is_medication_active()` logic — null end_date is only active if `(today − episode_date) <= 30 days`

---

### Item E — Frontend schema not updated (old field names)
**Source:** PDF → pages 10–11 (exact TSX field mapping table + code block)  
**Two changes required:**

**Change 1 — `HealthConditionsCard.tsx:50`:**
- Remove `HEADLINE_STATE_LABEL` map lookup
- Render `health.headline_state` directly as a plain styled heading (it is already a human-readable phrase)

**Change 2 — `HealthConditionsCard.tsx` (after subtitle, before `allConditions.map()`):**
```tsx
{health.summary_body && (
  <div style={{
    fontSize: 13,
    color: "var(--t2)",
    lineHeight: 1.6,
    marginBottom: 12,
    paddingBottom: 12,
    borderBottom: "1px solid var(--border)"
  }}>
    {health.summary_body}
  </div>
)}
```

**`api.ts:252–271`:** align type definitions with new aggregated_conditions shape — add `summary_body: string`, `monitoring`, `canonical_condition_id`, `recurrence_watch`, `soft_resolution` fields

---

### Item F — health_conditions_v2 cache not invalidated after aggregation
**Source:** Excel → Aggregation layer, step 6  
**Fix in `condition_aggregation_service.py` — end of `aggregate_conditions_for_pet()`:**
- Add explicit cache invalidation for `health_conditions_v2` keyed by `pet_id`
- Ensures next dashboard load triggers a fresh Claude call with the newly aggregated data instead of serving stale insights

---

## SECTION 3 — Need Additional Information (cannot implement without clarification)

### Item C — Extraction prompt missing canonical drug name normalisation
**Why it is blocked:**  
Neither the PDF nor the Excel defines a drug alias table or normalisation rules. Without this, "Vetmedin" and "Pimobendan" remain as two separate medications in the dedup pass.

**What is needed:**
1. A canonical drug name list (or instruction to normalise to generic INN name)
2. Whether normalisation should happen inside the GPT extraction prompt, in Python post-processing, or via a lookup table
3. Scope decision: only lifelong/chronic drugs, or all medications?

---

### Item D — Extraction prompt missing Rx-must-map-to-condition rule
**Why it is blocked:**  
Neither document defines what to do when a prescribed drug cannot be linked to any condition row in the same document. The rule "every medication must map to a condition" is called out as missing but not specified.

**What is needed:**
1. Should the extraction prompt instruct Claude to always create a condition row if a prescription is present but no diagnosis is named?
2. If a drug maps to an inferred condition, should `inferred_from_medication = true` be set (this field already exists in the PDF prompt schema)?
3. What condition name/tags should be inferred — e.g. from the drug's known indication — or should it be left as a generic placeholder?

---

## Summary Count

| Category | Count |
|----------|-------|
| Already implemented | 7 |
| Ready to implement | 12 |
| Need additional information | 2 |
| **Total gaps** | **21** |
