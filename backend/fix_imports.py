#!/usr/bin/env python3
"""
Fix imports in 25 service files by consolidating moved model imports.

This script:
1. Finds all uses of moved models (PreventiveMaster, ProductFood, etc.)
2. Removes direct imports of those models
3. Consolidates them into a single `from app.models import (...)` block
"""

import re
from pathlib import Path
from typing import Optional

MOVED_MODELS = {
    "PreventiveMaster",
    "ProductFood",
    "ProductMedicines",
    "ProductSupplement",
    "BreedConsequenceLibrary",
    "NudgeConfig",
    "NudgeMessageLibrary",
    "WhatsappTemplateConfig",
    "DashboardVisit",
    "FoodNutritionCache",
    "HygieneTipCache",
    "IdealWeightCache",
    "NudgeDeliveryLog",
    "NudgeEngagement",
    "NutritionTargetCache",
}

FILES_TO_FIX = [
    "app/services/admin/nudge_engine.py",
    "app/services/admin/nudge_scheduler.py",
    "app/services/admin/nudge_sender.py",
    "app/services/admin/preventive_seeder.py",
    "app/services/admin/reminder_engine.py",
    "app/services/dashboard/ai_insights_service.py",
    "app/services/dashboard/cart_service.py",
    "app/services/dashboard/health_trends_service.py",
    "app/services/dashboard/hygiene_service.py",
    "app/services/dashboard/medicine_recurrence_service.py",
    "app/services/dashboard/nutrition_service.py",
    "app/services/dashboard/signal_resolver.py",
    "app/services/dashboard/weight_service.py",
    "app/services/shared/care_plan_engine.py",
    "app/services/shared/gpt_extraction.py",
    "app/services/shared/preventive_calculator.py",
    "app/services/shared/recommendation_service.py",
    "app/services/whatsapp/agentic_edit.py",
    "app/services/whatsapp/birthday_service.py",
    "app/services/whatsapp/message_router.py",
    "app/services/whatsapp/onboarding.py",
    "app/services/whatsapp/order_service.py",
    "app/services/whatsapp/query_engine.py",
    "app/services/whatsapp/reminder_response.py",
    "app/services/whatsapp/whatsapp_sender.py",
]


def find_docstring_end(lines):
    """Find the line index after the module docstring ends."""
    if not lines or not lines[0].strip().startswith(('"""', "'''")):
        return 0

    quote = '"""' if '"""' in lines[0] else "'''"

    if lines[0].count(quote) >= 2:
        return 1

    for i in range(1, len(lines)):
        if quote in lines[i]:
            return i + 1

    return len(lines)


def extract_models_used(content):
    """Extract which MOVED_MODELS are used in the file."""
    used = set()
    for model in MOVED_MODELS:
        if re.search(rf'\b{re.escape(model)}\b', content):
            used.add(model)
    return used


def remove_direct_imports(lines):
    """Remove direct imports of moved models."""
    removed = set()
    result = []
    pattern = re.compile(r'^from app\.models\.[\w_]+ import (\w+)$')

    for line in lines:
        match = pattern.match(line.rstrip('\n').strip())
        if match:
            imported_name = match.group(1)
            if imported_name in MOVED_MODELS:
                removed.add(imported_name)
                continue
        result.append(line)

    return result, removed


def build_models_import_statement(models):
    """Build a `from app.models import (...)` statement."""
    if not models:
        return ""

    sorted_models = sorted(models)

    if len(sorted_models) <= 3:
        return f"from app.models import {', '.join(sorted_models)}\n"
    else:
        formatted = "from app.models import (\n"
        for model in sorted_models:
            formatted += f"    {model},\n"
        formatted += ")\n"
        return formatted


def fix_file(file_path):
    """Fix a single file. Returns (success, message)."""
    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.splitlines(keepends=True)

        docstring_end = find_docstring_end([line.rstrip('\n') for line in lines])
        used_models = extract_models_used(content)

        if not used_models:
            return True, f"  {file_path.name}: No changes needed"

        lines, removed_imports = remove_direct_imports(lines)

        # Find existing from app.models import block
        import_line = None
        for i in range(docstring_end, len(lines)):
            if lines[i].strip().startswith('from app.models import (') or \
               (lines[i].strip().startswith('from app.models import') and 'app.models.' not in lines[i]):
                import_line = i
                break

        # Build new import statement
        new_import = build_models_import_statement(used_models)

        if import_line is not None:
            # Replace existing block
            if '(' in lines[import_line]:
                # Multi-line block, find end
                end_line = import_line
                while end_line < len(lines) and ')' not in lines[end_line]:
                    end_line += 1
                del lines[import_line:end_line+1]
                lines.insert(import_line, new_import)
            else:
                lines[import_line] = new_import
        else:
            # Insert after docstring
            lines.insert(docstring_end, new_import)

        file_path.write_text(''.join(lines), encoding='utf-8')
        return True, f"  {file_path.name}: Fixed ({len(used_models)} models)"

    except Exception as e:
        return False, f"  {file_path.name}: ERROR - {e}"


def main():
    backend_dir = Path.cwd()

    if not (backend_dir / "app" / "models" / "__init__.py").exists():
        print(f"Error: Not in backend directory")
        return

    print(f"Fixing {len(FILES_TO_FIX)} service files...\n")

    success_count = 0
    for file_path_str in FILES_TO_FIX:
        file_path = backend_dir / file_path_str
        if not file_path.exists():
            print(f"  {file_path.name}: NOT FOUND")
            continue

        success, message = fix_file(file_path)
        print(message)
        if success:
            success_count += 1

    print(f"\nCompleted: {success_count}/{len(FILES_TO_FIX)} files fixed")


if __name__ == "__main__":
    main()
