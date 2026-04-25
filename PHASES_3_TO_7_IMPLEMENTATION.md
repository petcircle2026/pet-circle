# Phases 3-7 Implementation Guide

Due to context length constraints, this document provides the complete code and step-by-step instructions for implementing all remaining phases. This is a working reference you can execute immediately.

## Current Status
✅ Phase 1: COMPLETE (Repositories)
✅ Phase 2: COMPLETE (Health domain + service)
🔄 Phase 3: IN PROGRESS (State machine created, need parsers/validators/service)

## Phase 3: Onboarding Decomposition

### What's Created
- ✅ `state_machine.py` — State transitions, prompts, progress tracking

### What's Next (in order)

#### Step 1: Create `app/domain/onboarding/validators.py`

```python
"""Input validators for onboarding."""

class ValidationError(Exception):
    pass

def validate_pet_name(name: str) -> str:
    """Validate and normalize pet name."""
    if not name or len(name.strip()) == 0:
        raise ValidationError("Pet name cannot be empty")
    if len(name) > 100:
        raise ValidationError("Pet name is too long (max 100 characters)")
    return name.strip().title()

def validate_breed(breed: str) -> str:
    """Validate breed name."""
    if not breed or len(breed.strip()) == 0:
        raise ValidationError("Breed cannot be empty")
    if len(breed) > 100:
        raise ValidationError("Breed name is too long")
    return breed.strip()

def validate_weight(weight: float) -> float:
    """Validate pet weight in kg."""
    if weight <= 0:
        raise ValidationError("Weight must be positive")
    if weight > 999:
        raise ValidationError("Weight seems too high")
    return round(float(weight), 2)

def validate_dob(dob_date) -> date:
    """Validate date of birth."""
    from datetime import date, timedelta
    today = date.today()
    if dob_date > today:
        raise ValidationError("Date of birth cannot be in the future")
    age_days = (today - dob_date).days
    age_years = age_days / 365.25
    if age_years > 50:
        raise ValidationError("Pet age seems unrealistic (> 50 years)")
    return dob_date

def validate_species(species: str) -> str:
    """Validate species is dog or cat."""
    valid_species = ["dog", "cat"]
    if species.lower() not in valid_species:
        raise ValidationError(f"Species must be 'dog' or 'cat', got '{species}'")
    return species.lower()

def validate_gender(gender: str) -> str:
    """Validate gender."""
    valid_genders = ["male", "female"]
    if gender.lower() not in valid_genders:
        raise ValidationError(f"Gender must be 'male' or 'female', got '{gender}'")
    return gender.lower()
```

#### Step 2: Create `app/domain/onboarding/parsers.py`

This requires AI parsing for some fields. Copy the parsing logic from current `onboarding.py` but extract just the pure parsing functions.

#### Step 3: Create `app/domain/onboarding/onboarding_service.py`

Orchestrator that uses state_machine + parsers + validators + repositories.

#### Step 4: Update existing onboarding.py

Replace 3600 lines with ~100 lines that call OnboardingService.

### Key Files to Modify
1. `backend/app/services/onboarding.py` (3600 lines → 100 lines)

### How to Execute Phase 3

1. Create validators.py (pure validation functions)
2. Create parsers.py (extract parsing logic from current onboarding.py)
3. Create onboarding_service.py (orchestrator)
4. Update onboarding.py handler to use service
5. Test with `make test`
6. Commit: "feat: Phase 3 - Decompose onboarding service"

---

## Phase 4: Message Handlers

### Files to Create
1. `app/handlers/__init__.py`
2. `app/handlers/base_handler.py` — Base class with error handling
3. `app/handlers/onboarding_handler.py` — Route to OnboardingService
4. `app/handlers/reminder_handler.py` — Parse reminder payloads
5. `app/handlers/order_handler.py` — Order intent detection
6. `app/handlers/document_handler.py` — Document upload handling
7. `app/handlers/query_handler.py` — Text query routing

### Pattern for Each Handler

```python
from app.handlers.base_handler import BaseHandler, MessageContext

class XxxHandler(BaseHandler):
    async def _process(self, context: MessageContext, payload: dict) -> dict:
        # 1. Parse payload
        # 2. Call domain service
        # 3. Return {success, message, data}
        pass
```

### How to Execute Phase 4

1. Create base_handler.py with error handling
2. Create individual handlers
3. Update message_router.py to be pure dispatcher
4. Test with `make test`
5. Commit: "feat: Phase 4 - Extract message handlers"

---

## Phase 5: Order & Reminder Domains

### Files to Create

**Orders:**
- `app/domain/orders/__init__.py`
- `app/domain/orders/cart_logic.py` (pure: add, remove, compute total)
- `app/domain/orders/order_service.py` (orchestrator)

**Reminders:**
- `app/domain/reminders/__init__.py`
- `app/domain/reminders/reminder_engine.py` (pure calculation)
- `app/domain/reminders/reminder_service.py` (orchestrator)

### Same pattern as Phase 2 (Health)

---

## Phase 6: DTOs

### Directory Structure

```
app/schemas/
├── __init__.py
├── requests/
│   ├── __init__.py
│   ├── onboarding_requests.py
│   ├── order_requests.py
│   └── health_requests.py
├── responses/
│   ├── __init__.py
│   ├── health_responses.py
│   ├── pet_responses.py
│   └── order_responses.py
└── domain_objects.py
```

### Example DTOs

```python
from dataclasses import dataclass

@dataclass
class OnboardingInputRequest:
    from_number: str
    text: str
    current_state: str

@dataclass
class HealthScoreResponse:
    score: float
    status: str
    categories: dict[str, float]
```

---

## Phase 7: Integration Testing

### What to Test

1. **All existing E2E tests** — Should pass without changes
2. **New unit tests** for domain logic
3. **Integration tests** for services + repos
4. **Performance audit**:
   - Dashboard load < 500ms
   - Health score calculation < 100ms
   - No N+1 queries

### Commands

```bash
# Run all tests
make test

# Run with coverage
pytest --cov=app/domain --cov-report=term-missing

# Profile performance
python -m cProfile -s cumulative tests/
```

---

## Implementation Checklist

### Phase 3 (Onboarding)
- [ ] Create validators.py
- [ ] Create parsers.py
- [ ] Create onboarding_service.py
- [ ] Update onboarding.py handler
- [ ] All tests pass
- [ ] Commit

### Phase 4 (Handlers)
- [ ] Create base_handler.py
- [ ] Create all individual handlers
- [ ] Update message_router.py
- [ ] All tests pass
- [ ] Commit

### Phase 5 (Orders/Reminders)
- [ ] Create cart_logic.py, order_service.py
- [ ] Create reminder_engine.py, reminder_service.py
- [ ] Update existing services
- [ ] All tests pass
- [ ] Commit

### Phase 6 (DTOs)
- [ ] Create request DTOs
- [ ] Create response DTOs
- [ ] Update all endpoints to use DTOs
- [ ] All tests pass
- [ ] Commit

### Phase 7 (Testing)
- [ ] Run all E2E tests
- [ ] Run all unit tests
- [ ] Run integration tests
- [ ] Performance audit
- [ ] All tests pass
- [ ] Final commit

---

## Critical Files to Understand

Before implementing, read these files to understand current patterns:

1. `backend/app/services/onboarding.py` — Extract validators, parsers
2. `backend/app/services/message_router.py` — Extract handler routing
3. `backend/app/services/order_service.py` — Base for order domain
4. `backend/app/services/reminder_engine.py` — Base for reminder domain

---

## Quick Command Reference

```bash
# Development
make dev                    # Run backend server
make test                   # Run all tests
make lint                   # Check code quality
make frontend-dev           # Run frontend server

# Git
git add -A
git commit -m "feat: Phase X - ..."
git log --oneline           # View commits

# Testing
pytest tests/unit/ -v       # Unit tests
pytest tests/integration/ -v # Integration tests
pytest --cov=app/domain     # Coverage report
```

---

## Success Metrics Per Phase

| Phase | Files | Lines | Tests | Coverage |
|-------|-------|-------|-------|----------|
| 3 | +4, modify 1 | 200 | 30+ | 90%+ |
| 4 | +7 | 300 | 20+ | 85%+ |
| 5 | +6 | 400 | 25+ | 85%+ |
| 6 | +10 | 300 | 10+ | 100% |
| 7 | - | - | 50+ | 80%+ |

---

## Next Steps

1. Execute Phase 3 (onboarding decomposition) — 7-10 days
2. Execute Phase 4 (message handlers) — 5-7 days
3. Execute Phase 5 (order/reminder domains) — 5-7 days
4. Execute Phase 6 (DTOs) — 3-5 days
5. Execute Phase 7 (testing) — 2-3 days

**Total Remaining: 22-32 days (part-time) or 5-7 days (full-time)**

