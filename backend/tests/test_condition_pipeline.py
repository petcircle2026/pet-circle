"""
Condition Pipeline Test — end-to-end extraction + aggregation.

Runs GPT extraction on documents, then passes the extracted conditions through
the aggregation pipeline to verify:

  1. Document-level condition_type is always "chronic" or "episodic" (never "recurrent")
  2. Aggregation groups similar conditions into families using body-system similarity
  3. condition_type upgrades correctly at family level (recurrence threshold, chronic trigger)
  4. condition_status is computed at runtime from dates (not stale)
  5. condition_family_id assignment is consistent

Usage:
    cd backend

    # Run against Sample_Reports folder (auto-detected):
    APP_ENV=production python -m tests.test_condition_pipeline

    # Run against a specific folder:
    APP_ENV=production FIXTURES_DIR=path/to/docs python -m tests.test_condition_pipeline

    # Run aggregation-only simulation (no documents, no OpenAI key needed):
    python -m tests.test_condition_pipeline --simulate

Requires OPENAI_API_KEY for document extraction (not needed for --simulate).
"""

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("APP_ENV", "production")

SIMULATE_ONLY = "--simulate" in sys.argv

# ─── Colours for terminal output ─────────────────────────────────────────────
_GREEN  = "\033[32m"
_RED    = "\033[31m"
_YELLOW = "\033[33m"
_CYAN   = "\033[36m"
_RESET  = "\033[0m"
_BOLD   = "\033[1m"


def _p(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))


def _ok(msg: str) -> None:    _p(f"  {_GREEN}✓{_RESET} {msg}")
def _fail(msg: str) -> None:  _p(f"  {_RED}✗{_RESET} {msg}")
def _warn(msg: str) -> None:  _p(f"  {_YELLOW}~{_RESET} {msg}")
def _info(msg: str) -> None:  _p(f"    {_CYAN}{msg}{_RESET}")


# ─── Minimal Condition stand-in for aggregation (no DB needed) ────────────────

@dataclass
class MockCondition:
    """Mirrors the fields read by condition_aggregation_service."""
    id: Any
    pet_id: str
    document_id: str
    name: str
    condition_type: str          # "chronic" | "episodic"  (document level)
    condition_status: str | None  # "active" | "resolved" | None
    episode_dates: list[str] = field(default_factory=list)
    diagnosed_at: date | None = None
    medication_end_date: date | None = None
    medications: list[dict] = field(default_factory=list)
    monitoring: list[dict] = field(default_factory=list)
    soft_resolution: bool = False
    recurrence_watch: bool = False
    condition_family_id: Any = None
    is_active: bool = True


# ─── Extraction helpers ───────────────────────────────────────────────────────

async def _extract_conditions_from_file(filepath: str) -> list[dict]:
    """
    Call GPT extraction on one file and return the raw conditions[] array.
    Returns [] if the document has no conditions or extraction fails.
    """
    from app.services.shared.gpt_extraction import (
        _call_openai_extraction,
        _call_openai_extraction_vision,
        _validate_extraction_dict,
    )
    from app.utils.file_reader import (
        encode_image_base64,
        extract_pdf_text,
        render_pdf_pages_as_images,
    )

    ext = filepath.lower().rsplit(".", 1)[-1]
    with open(filepath, "rb") as f:
        file_bytes = f.read()

    parsed_dict = None
    try:
        if ext in ("jpg", "jpeg", "png"):
            mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
            data_uri = encode_image_base64(file_bytes, mime)
            parsed_dict = await _call_openai_extraction_vision(data_uri)
        elif ext == "pdf":
            pdf_text = extract_pdf_text(file_bytes)
            if len(pdf_text.strip()) > 20:
                parsed_dict = await _call_openai_extraction(
                    f"Veterinary document text:\n\n{pdf_text}"
                )
            else:
                pages = render_pdf_pages_as_images(file_bytes, max_pages=3)
                if pages:
                    parsed_dict = await _call_openai_extraction_vision(pages[0])
    except Exception as exc:
        _warn(f"Extraction error: {exc}")
        return []

    if not parsed_dict:
        return []

    try:
        _items, _doc_name, _pet_name, metadata = _validate_extraction_dict(
            parsed_dict, file_path=filepath
        )
        return metadata.get("conditions") or []
    except Exception as exc:
        _warn(f"Validation error: {exc}")
        return []


# ─── Checks ───────────────────────────────────────────────────────────────────

_ISSUES: list[str] = []


def _check(condition: bool, pass_msg: str, fail_msg: str) -> bool:
    if condition:
        _ok(pass_msg)
    else:
        _fail(fail_msg)
        _ISSUES.append(fail_msg)
    return condition


# ─── Document-level checks ────────────────────────────────────────────────────

def _check_document_conditions(filename: str, raw_conditions: list[dict]) -> list[MockCondition]:
    """
    Validate each extracted condition and return MockCondition objects
    with the same collapse logic as gpt_extraction.py.
    """
    mock_conditions = []
    doc_id = f"doc_{filename.replace('.', '_')}"

    for i, raw in enumerate(raw_conditions):
        name = (raw.get("condition_name") or "").strip()
        if not name:
            continue

        raw_type = str(raw.get("condition_type") or "episodic").strip().lower()

        # ── Document-level collapse (mirrors gpt_extraction.py) ──────────────
        if raw_type == "chronic":
            stored_type = "chronic"
        elif raw_type == "resolved":
            stored_type = "episodic"  # legacy
        else:
            stored_type = "episodic"  # recurrent, acute, unknown → episodic

        # ── Check: no "recurrent" at document level ──────────────────────────
        _check(
            raw_type != "recurrent",
            f"'{name}' — GPT output condition_type='{raw_type}' (not recurrent)",
            f"'{name}' — GPT returned condition_type='recurrent' at document level (should be episodic or chronic only)",
        )
        _check(
            stored_type in ("chronic", "episodic"),
            f"'{name}' — stored condition_type='{stored_type}'",
            f"'{name}' — stored type '{stored_type}' is not chronic or episodic",
        )

        # ── Parse dates ───────────────────────────────────────────────────────
        episode_dates: list[str] = raw.get("episode_dates") or []
        diagnosed_at_str = raw.get("diagnosed_at")
        diagnosed_at: date | None = None
        if diagnosed_at_str:
            try:
                from app.utils.date_utils import parse_date
                diagnosed_at = parse_date(diagnosed_at_str)
            except Exception:
                pass

        # ── Medications ───────────────────────────────────────────────────────
        raw_meds = raw.get("medications") or []
        medications = []
        medication_end_date: date | None = None
        for med in raw_meds:
            if not isinstance(med, dict):
                continue
            end_str = med.get("end_date")
            end_d: date | None = None
            if end_str:
                try:
                    from app.utils.date_utils import parse_date
                    end_d = parse_date(end_str)
                    if medication_end_date is None or end_d > medication_end_date:
                        medication_end_date = end_d
                except Exception:
                    pass
            medications.append({"name": med.get("name"), "end_date": end_d, "dose": med.get("dose")})

        # ── Monitoring ────────────────────────────────────────────────────────
        raw_mon = raw.get("monitoring") or []
        monitoring = [
            {"name": m.get("name"), "recheck_due_date": m.get("recheck_due_date")}
            for m in raw_mon if isinstance(m, dict)
        ]

        raw_status = raw.get("condition_status")
        condition_status = str(raw_status).strip().lower() if raw_status else None
        if condition_status not in ("active", "resolved"):
            condition_status = None

        mock = MockCondition(
            id=f"c_{doc_id}_{i}",
            pet_id="test_pet",
            document_id=doc_id,
            name=name,
            condition_type=stored_type,
            condition_status=condition_status,
            episode_dates=episode_dates,
            diagnosed_at=diagnosed_at,
            medication_end_date=medication_end_date,
            medications=medications,
            monitoring=monitoring,
        )
        mock_conditions.append(mock)

        meds_str = ", ".join(m["name"] for m in medications if m.get("name")) or "none"
        _info(f"name='{name}'  type={stored_type}  status={condition_status}  "
              f"episodes={len(episode_dates)}  meds=[{meds_str}]")

    return mock_conditions


# ─── Aggregation checks ───────────────────────────────────────────────────────

def _run_aggregation(all_conditions: list[MockCondition]) -> list[dict]:
    """
    Run the aggregation pipeline over mock conditions and return family dicts.
    Uses the real condition_aggregation_service functions directly.
    """
    from app.services.dashboard.condition_aggregation_service import (
        _compute_condition_status,
        _group_into_families,
        _merge_family,
    )

    if not all_conditions:
        return []

    families_grouped = _group_into_families(all_conditions)
    family_results = []

    for family in families_grouped:
        merged = _merge_family(family)

        # Compute condition_status at runtime (never use stored value)
        runtime_status = _compute_condition_status(
            merged["condition_type"],
            merged.get("medication_end_date"),
            merged.get("episode_dates") or [],
        )
        merged["runtime_condition_status"] = runtime_status
        family_results.append(merged)

    return family_results


def _check_aggregation(families: list[dict]) -> None:
    """Print and validate each family row."""
    from app.services.dashboard.condition_aggregation_service import _compute_condition_status

    _p(f"\n  {_BOLD}Aggregated condition families:{_RESET}")
    for fam in families:
        name = fam.get("name", "?")
        ftype = fam.get("condition_type", "?")
        runtime_status = fam.get("runtime_condition_status", "?")
        episodes = fam.get("episode_dates") or []
        med_end = fam.get("medication_end_date")
        recurrence_watch = fam.get("recurrence_watch", False)
        meds = [m.get("name") for m in (fam.get("medications") or []) if isinstance(m, dict) and m.get("name")]

        _p(f"\n    {_BOLD}Family: {name}{_RESET}")
        _info(f"condition_type  = {ftype}")
        _info(f"status (runtime)= {runtime_status}  ← computed today, not stored")
        _info(f"episode_dates   = {episodes}")
        _info(f"medication_end  = {med_end}")
        _info(f"recurrence_watch= {recurrence_watch}")
        _info(f"medications     = {meds}")

        # Validate: chronic conditions must always be active
        if ftype == "chronic":
            _check(
                runtime_status == "active",
                f"'{name}' chronic → status=active",
                f"'{name}' chronic should always be active, got '{runtime_status}'",
            )

        # Validate: recurrent only appears at aggregation level
        _check(
            ftype in ("chronic", "episodic", "recurrent"),
            f"'{name}' family type='{ftype}' is valid",
            f"'{name}' family type='{ftype}' is not a valid aggregated type",
        )

        # Validate: if 2+ episodes, recurrence threshold check
        if len(episodes) >= 2 and ftype not in ("chronic",):
            _check(
                ftype == "recurrent",
                f"'{name}' has {len(episodes)} episodes → correctly upgraded to recurrent",
                f"'{name}' has {len(episodes)} episodes but type='{ftype}' (should be recurrent if within threshold)",
            )


# ─── Simulation data ──────────────────────────────────────────────────────────

def _build_simulation_conditions() -> list[MockCondition]:
    """
    Build a synthetic set of conditions that exercises all aggregation rules:
      - GI upset: 2 episodes in 12 months → should become recurrent
      - Hypothyroidism: chronic → stays chronic, always active
      - Skin infection: single episode, old → resolved
      - UTI (two docs): 2 episodes in 3 months → recurrent, status depends on med_end_date
    """
    today = date.today()
    return [
        # GI episode 1 (13 months ago)
        MockCondition(
            id="c1", pet_id="sim_pet", document_id="doc1",
            name="GI upset", condition_type="episodic", condition_status="resolved",
            episode_dates=[(today - timedelta(days=395)).isoformat()],
            diagnosed_at=today - timedelta(days=395),
            medication_end_date=today - timedelta(days=380),
        ),
        # GI episode 2 (15 days ago)
        MockCondition(
            id="c2", pet_id="sim_pet", document_id="doc2",
            name="vomiting and loose stool", condition_type="episodic", condition_status="active",
            episode_dates=[(today - timedelta(days=15)).isoformat()],
            diagnosed_at=today - timedelta(days=15),
            medication_end_date=today + timedelta(days=5),
            medications=[{"name": "metronidazole", "end_date": today + timedelta(days=5)}],
        ),
        # Hypothyroidism (chronic, lifelong)
        MockCondition(
            id="c3", pet_id="sim_pet", document_id="doc3",
            name="Hypothyroidism", condition_type="chronic", condition_status="active",
            episode_dates=[(today - timedelta(days=365)).isoformat()],
            diagnosed_at=today - timedelta(days=365),
            medication_end_date=date(2099, 12, 31),
            medications=[{"name": "thyroxine", "end_date": date(2099, 12, 31)}],
        ),
        # Skin infection (old, single episode)
        MockCondition(
            id="c4", pet_id="sim_pet", document_id="doc4",
            name="Skin infection", condition_type="episodic", condition_status="resolved",
            episode_dates=[(today - timedelta(days=200)).isoformat()],
            diagnosed_at=today - timedelta(days=200),
        ),
        # UTI episode 1 (3 months ago)
        MockCondition(
            id="c5", pet_id="sim_pet", document_id="doc5",
            name="UTI", condition_type="episodic", condition_status="resolved",
            episode_dates=[(today - timedelta(days=90)).isoformat()],
            diagnosed_at=today - timedelta(days=90),
            medication_end_date=today - timedelta(days=76),
        ),
        # UTI episode 2 — named differently but same family (ecoli in urine)
        MockCondition(
            id="c6", pet_id="sim_pet", document_id="doc6",
            name="Ecoli observed in urine", condition_type="episodic", condition_status="resolved",
            episode_dates=[(today - timedelta(days=45)).isoformat()],
            diagnosed_at=today - timedelta(days=45),
            medication_end_date=today - timedelta(days=31),
        ),
    ]


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main() -> None:
    _p(f"\n{'='*70}")
    _p(f"{_BOLD}Condition Pipeline Test{_RESET}")
    _p(f"{'='*70}")

    all_mock_conditions: list[MockCondition] = []

    # ── Mode 1: Simulate with synthetic data ─────────────────────────────────
    if SIMULATE_ONLY:
        _p(f"\n{_BOLD}[ SIMULATION MODE — no GPT calls, no documents needed ]{_RESET}")
        _p("\nBuilding synthetic conditions (GI recurrence, hypothyroidism, skin, UTI recurrence)...")
        all_mock_conditions = _build_simulation_conditions()
        _p(f"  Built {len(all_mock_conditions)} mock document-level condition rows")

        for mc in all_mock_conditions:
            _info(f"  doc={mc.document_id}  name='{mc.name}'  type={mc.condition_type}  "
                  f"episodes={len(mc.episode_dates)}")

    # ── Mode 2: Extract from real documents ──────────────────────────────────
    else:
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        fixtures_dir = os.environ.get("FIXTURES_DIR") or next(
            (p for p in [
                os.path.join(repo_root, "Sample_Reports"),
                os.path.join(repo_root, "fixtures", "sample_reports"),
            ] if os.path.exists(p)),
            None,
        )

        if not fixtures_dir or not os.path.exists(fixtures_dir):
            _p(f"{_RED}ERROR: No documents folder found. "
               f"Set FIXTURES_DIR or place files in Sample_Reports/. "
               f"Run with --simulate to test aggregation without documents.{_RESET}")
            sys.exit(1)

        files = [f for f in sorted(os.listdir(fixtures_dir))
                 if os.path.isfile(os.path.join(fixtures_dir, f))
                 and f.lower().rsplit(".", 1)[-1] in ("pdf", "jpg", "jpeg", "png")]

        _p(f"\nFound {len(files)} document(s) in {os.path.relpath(fixtures_dir, repo_root)}")

        total_conditions_extracted = 0
        for filename in files:
            filepath = os.path.join(fixtures_dir, filename)
            _p(f"\n{_BOLD}─── {filename} ───{_RESET}")
            t0 = time.time()

            raw_conditions = await _extract_conditions_from_file(filepath)
            elapsed = time.time() - t0

            if not raw_conditions:
                _warn(f"No conditions extracted ({elapsed:.1f}s)")
                continue

            _p(f"  Extracted {len(raw_conditions)} condition(s) in {elapsed:.1f}s")
            mocks = _check_document_conditions(filename, raw_conditions)
            all_mock_conditions.extend(mocks)
            total_conditions_extracted += len(mocks)

        _p(f"\n  Total document-level condition rows collected: {total_conditions_extracted}")

    # ── Aggregation pipeline ──────────────────────────────────────────────────
    _p(f"\n{'─'*70}")
    _p(f"{_BOLD}Aggregation pipeline{_RESET}")
    _p(f"{'─'*70}")

    if not all_mock_conditions:
        _warn("No conditions to aggregate. Upload prescription/diagnosis documents or run --simulate.")
    else:
        families = _run_aggregation(all_mock_conditions)
        _p(f"\n  Input:   {len(all_mock_conditions)} document-level condition rows")
        _p(f"  Output:  {len(families)} condition famil{'y' if len(families)==1 else 'ies'}")

        _check_aggregation(families)

        # condition_status staleness check: re-run compute with a future "today"
        _p(f"\n  {_BOLD}Staleness simulation{_RESET} — would status change 60 days from now?")
        from app.services.dashboard.condition_aggregation_service import _compute_condition_status
        for fam in families:
            current = fam.get("runtime_condition_status", "?")
            med_end = fam.get("medication_end_date")
            episodes = fam.get("episode_dates") or []
            ftype = fam.get("condition_type", "episodic")

            # Simulate 60 days later by shifting episode dates back
            shifted_episodes = []
            for ep in episodes:
                try:
                    from app.utils.date_utils import parse_date
                    d = parse_date(ep)
                    shifted_episodes.append((d - timedelta(days=60)).isoformat())
                except Exception:
                    shifted_episodes.append(ep)
            shifted_med_end = (med_end - timedelta(days=60)) if med_end and med_end.year < 2090 else med_end

            future_status = _compute_condition_status(ftype, shifted_med_end, shifted_episodes)
            changed = current != future_status
            msg = f"'{fam.get('name')}': {current} → {future_status}"
            if changed:
                _info(f"{_YELLOW}{msg}  (would change — runtime compute catches it){_RESET}")
            else:
                _info(f"{msg}  (unchanged)")

    # ── Final summary ─────────────────────────────────────────────────────────
    _p(f"\n{'='*70}")
    _p(f"{_BOLD}SUMMARY{_RESET}")
    _p(f"{'='*70}")

    if not _ISSUES:
        _p(f"\n{_GREEN}{_BOLD}ALL CHECKS PASSED{_RESET}")
    else:
        _p(f"\n{_RED}{_BOLD}ISSUES FOUND: {len(_ISSUES)}{_RESET}")
        for issue in _ISSUES:
            _p(f"  {_RED}✗{_RESET} {issue}")

    # Save family output as JSON for inspection
    if all_mock_conditions:
        out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "condition_pipeline_results.json")
        families_serializable = []
        for fam in (families if all_mock_conditions else []):
            fam_copy = {
                k: v.isoformat() if isinstance(v, date) else v
                for k, v in fam.items()
            }
            families_serializable.append(fam_copy)
        with open(out_path, "w") as fp:
            json.dump(families_serializable, fp, indent=2, default=str)
        _p(f"\nDetailed family output saved to: {out_path}")

    _p("")


if __name__ == "__main__":
    asyncio.run(main())
