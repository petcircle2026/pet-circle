# Backend Refactoring: Phases 2-7 Execution Guide

## Status: Phase 1 ✅ COMPLETE
✅ PetRepository, PreventiveRepository, HealthRepository created and committed

## Phases 2-7: Step-by-Step Implementation

### Phase 2: Health Domain Logic Extraction (20-25 hours)

**What's Done:**
- ✅ `app/domain/health/health_score.py` — Pure health score calculation logic

**What's Next:**

1. **Create `app/domain/health/preventive_logic.py`**
   - Extract `preventive_calculator.py` logic into pure functions
   - Functions: `calculate_next_due_date()`, `get_frequency_for_type()`, `is_overdue()`
   - No DB access, fully testable

2. **Create `app/domain/health/health_service.py`**
   - Orchestrator that uses repositories + domain logic
   - Class: `HealthService`
   - Methods:
     - `get_health_score(pet_id)` — queries repos, applies logic
     - `get_health_overview(pet_id)` — full health dashboard data
     - `analyze_trends(pet_id)` — weight trends, vaccination patterns

3. **Refactor existing files to use new service:**
   - Update `dashboard_service.py` → use `HealthService` instead of direct queries
   - Update `health_trends_service.py` → use `HealthService`
   - Update `care_plan_engine.py` → use `HealthService`

4. **Tests:**
   - `tests/unit/domain/health/test_health_score.py` — pure logic tests
   - `tests/integration/domain/test_health_service.py` — service + repo tests

---

### Phase 3: Decompose Onboarding (30-35 hours)

This is the **largest** phase. onboarding.py (3600 lines) breaks into 4 files:

1. **Create `app/domain/onboarding/state_machine.py`**
   - Class: `OnboardingStateMachine`
   - Current states: pending, awaiting_pet_name, awaiting_breed_age, ...→ complete
   - Methods:
     - `get_next_state(current_state, user_input) -> str` — pure logic
     - `is_valid_transition(from_state, to_state) -> bool`
     - `get_prompt_for_state(state) -> str` — what to ask user

2. **Create `app/domain/onboarding/parsers.py`**
   - Functions extracted from onboarding.py:
     - `parse_breed_and_age(text)` → (breed: str, age: str)
     - `parse_gender_and_weight(text)` → (gender: str, weight: float)
     - `parse_food_type(text)` → food_type: str
     - `parse_date_of_birth(text)` → dob: date (uses AI if needed)
   - All use `get_ai_client()` if needed, but are pure in behavior

3. **Create `app/domain/onboarding/validators.py`**
   - Functions:
     - `validate_pet_name(name)` → raises ValidationError if invalid
     - `validate_breed(breed)` → normalizes or raises
     - `validate_dob(dob)` → checks not future, reasonable age range
     - `validate_weight(weight)` → checks reasonable range
     - `validate_food_type(food_type)` → must be one of known types

4. **Create `app/domain/onboarding/onboarding_service.py`**
   - Class: `OnboardingService`
   - Uses: state_machine + parsers + validators + repositories
   - Methods:
     - `process_input(from_number, text) -> OnboardingResponse`
     - `complete_onboarding(user_id, pet_id) -> dict`
     - `get_onboarding_state(user_id) -> str`

5. **Update `onboarding.py` handler:**
   - Replace 3600 lines with ~50 lines calling `OnboardingService`

---

### Phase 4: Extract Message Handlers (15-20 hours)

1. **Create `app/handlers/base_handler.py`**
   ```python
   class BaseHandler(ABC):
       def handle(context: MessageContext) -> dict  # {success, message, data}
   ```

2. **Create individual handler files:**
   - `onboarding_handler.py` → route to OnboardingService
   - `reminder_handler.py` → parse reminder payload → ReminderService
   - `order_handler.py` → order intent → OrderService
   - `document_handler.py` → document upload → DocumentService
   - `query_handler.py` → text query → QueryEngine

3. **Simplify `message_router.py`:**
   - Remove all business logic (move to handlers)
   - Becomes pure dispatcher: detect message type → route to handler

---

### Phase 5: Extract Order & Reminder Domains (20-25 hours)

1. **Orders:**
   - `app/domain/orders/cart_logic.py` — pure cart operations
   - `app/domain/orders/order_service.py` — orchestrator

2. **Reminders:**
   - `app/domain/reminders/reminder_engine.py` — due date calculation
   - `app/domain/reminders/reminder_service.py` — orchestrator

---

### Phase 6: Create DTOs (10-15 hours)

1. **Request DTOs:** `app/schemas/requests/`
   - `OnboardingRequest`, `OrderRequest`, `HealthRequest`

2. **Response DTOs:** `app/schemas/responses/`
   - `HealthResponse`, `PetResponse`, `OrderResponse`

---

### Phase 7: Integration & Performance Testing (10-15 hours)

1. Run full E2E tests
2. Performance audit (N+1 queries, load times)
3. Code review

---

## Quick Command Reference

### To start Phase 2 now:

1. Copy `health_score.py` from above (already created)

2. Create `app/domain/health/preventive_logic.py` — extract from current `preventive_calculator.py`

3. Create `app/domain/health/health_service.py` — orchestrate repos + logic

4. Update `dashboard_service.py`:
   ```python
   from app.domain.health.health_service import HealthService
   from app.repositories.health_repository import HealthRepository
   
   health_repo = HealthRepository(db)
   service = HealthService(health_repo, ...)
   score = await service.get_health_score(pet_id)
   ```

5. Run tests → verify no behavior changes

6. Commit: `git commit -m "feat: Phase 2 - Extract health domain logic"`

---

## Files to Delete (After Migration)

Once all phases complete, these old files are no longer needed:

- `services/health_trends_service.py` (logic moved to domain/)
- `services/onboarding.py` → keep tiny wrapper, move logic to domain/
- `services/message_router.py` → keep as dispatcher only, logic in handlers/
- Individual query code in services (all moved to repositories/)

**Keep them for 1-2 commits**, then delete to verify no breakage.

---

## Testing Strategy (All Phases)

**Unit tests (pure logic):**
```python
# tests/unit/domain/health/test_health_score.py
def test_perfect_health_scores_100():
    input = HealthScoreInput(all_true=True)
    score = calculate_composite_score(calculate_health_categories(input))
    assert score == 100.0
```

**Integration tests:**
```python
# tests/integration/test_health_service.py
def test_health_score_workflow(db, pet_factory):
    pet = pet_factory(db, name="Max")
    service = HealthService(...)
    score = await service.get_health_score(pet.id)
    assert 0 <= score <= 100
```

**E2E tests (existing, unchanged):**
- WhatsApp flow tests continue to work
- Dashboard tests continue to work

---

## Success Metrics Per Phase

| Phase | Metric | Target |
|-------|--------|--------|
| 1 | Repositories created | ✅ DONE |
| 2 | Health logic consolidated | 1 file = health_score.py |
| 3 | onboarding.py lines | < 100 (from 3600) |
| 4 | message_router lines | < 100 (from 900) |
| 5 | Order/Reminder services | < 200 lines each |
| 6 | DTOs coverage | All endpoints have request/response types |
| 7 | Test coverage | 80%+ for domain logic |

---

## Total Time Estimate

- Phase 1: ✅ Done (6 hours)
- Phase 2: 20-25 hours
- Phase 3: 30-35 hours (largest)
- Phase 4: 15-20 hours
- Phase 5: 20-25 hours
- Phase 6: 10-15 hours
- Phase 7: 10-15 hours

**Total: 120-160 hours**  
**Timeline: 6-7 weeks @ 20 hrs/week, or 3-4 weeks full-time**

---

## Key Files by Phase

| Phase | New Files | Modified Files |
|-------|-----------|----------------|
| 1 | app/repositories/\*.py | N/A |
| 2 | app/domain/health/\*.py | dashboard_service.py, health_trends_service.py |
| 3 | app/domain/onboarding/\*.py | app/services/onboarding.py |
| 4 | app/handlers/\*.py | app/services/message_router.py |
| 5 | app/domain/{orders,reminders}/\*.py | app/services/{order_service,reminder_engine}.py |
| 6 | app/schemas/{requests,responses}/\*.py | N/A |
| 7 | tests/unit/domain/\*.py, tests/integration/\*.py | All above |

---

## Next Immediate Steps

1. Review `health_score.py` above ✅ (created)
2. Create `preventive_logic.py` (extract from `preventive_calculator.py`)
3. Create `health_service.py` (orchestrator)
4. Update dashboard_service to use new service
5. Run tests → commit
6. Move to Phase 3 (onboarding decomposition)

