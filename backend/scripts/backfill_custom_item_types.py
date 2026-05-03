"""
Backfill item_type for existing custom_preventive_items where item_type IS NULL.

Uses GPT to classify each item name into 'vaccine', 'deworming', 'tick_flea',
or 'other' so the cadence builder no longer relies on keyword matching for
names like 'ARV', '10 in 1', 'Milbemax', etc.

Usage:
    cd backend
    APP_ENV=production python scripts/backfill_custom_item_types.py

    # Dry run (print classifications without writing to DB):
    APP_ENV=production python scripts/backfill_custom_item_types.py --dry-run
"""

import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.preventive.custom_preventive_item import CustomPreventiveItem

_BATCH_SIZE = 20

_CLASSIFY_PROMPT = """\
You are a veterinary data assistant. Classify each preventive item name into exactly one category:
- "vaccine": any vaccination (rabies, dhppi, combo shots, anti-rabies, etc.)
- "deworming": any deworming/anthelmintic medication (milbemax, panacur, drontal, etc.)
- "tick_flea": any flea, tick, or external parasite prevention/treatment (nexgard, bravecto, frontline, etc.)
- "other": anything else (supplements, diagnostics, grooming, etc.)

Return ONLY a JSON object mapping each item name to its category. Example:
{"ARV": "vaccine", "10 in 1": "vaccine", "Milbemax": "deworming", "Nexgard": "tick_flea"}

Items to classify:
"""


def _classify_batch_with_gpt(item_names: list[str]) -> dict[str, str]:
    """Call GPT to classify a batch of item names. Returns {name: category}."""
    from app.utils.ai_client import get_sync_ai_client

    client = get_sync_ai_client()
    prompt = _CLASSIFY_PROMPT + json.dumps(item_names, ensure_ascii=False)

    # Support both OpenAI and Anthropic sync clients
    if hasattr(client, "chat"):
        # OpenAI
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=512,
        )
        raw = response.choices[0].message.content or "{}"
    else:
        # Anthropic
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text if response.content else "{}"

    # Strip markdown fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        print(f"  [WARN] Could not parse GPT response: {raw!r}")
        return {}

    valid = {"vaccine", "deworming", "tick_flea", "other"}
    return {k: v for k, v in result.items() if v in valid}


def main(dry_run: bool = False) -> None:
    db = SessionLocal()
    try:
        items = (
            db.query(CustomPreventiveItem)
            .filter(CustomPreventiveItem.item_type == None)  # noqa: E711
            .order_by(CustomPreventiveItem.created_at)
            .all()
        )

        if not items:
            print("No custom preventive items with missing item_type found.")
            return

        print(f"Found {len(items)} custom items to classify.")
        updated = 0

        for batch_start in range(0, len(items), _BATCH_SIZE):
            batch = items[batch_start : batch_start + _BATCH_SIZE]
            names = [item.item_name for item in batch]
            print(f"\nClassifying batch {batch_start // _BATCH_SIZE + 1}: {names}")

            classifications = _classify_batch_with_gpt(names)

            for item in batch:
                category = classifications.get(item.item_name)
                if not category:
                    print(f"  [SKIP] No classification for '{item.item_name}'")
                    continue
                print(f"  {item.item_name!r} → {category}")
                if not dry_run:
                    item.item_type = category
                    updated += 1

        if not dry_run:
            db.commit()
            print(f"\nDone. Updated {updated} of {len(items)} items.")
        else:
            print(f"\nDry run complete. Would update {updated} of {len(items)} items.")

    except Exception as exc:
        db.rollback()
        print(f"Error: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill item_type for custom preventive items")
    parser.add_argument("--dry-run", action="store_true", help="Print classifications without writing to DB")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
