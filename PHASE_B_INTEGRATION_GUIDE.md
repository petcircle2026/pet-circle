# Phase B: Integration Guide — How to Use Repositories

**Goal**: Replace all direct database queries with repository calls
**Scope**: 25+ files across services, routers, and handlers
**Pattern**: Dependency injection via FastAPI `Depends`

---

## Pattern Overview

All repository access flows through `get_repositories()` dependency:

```python
from fastapi import Depends
from app.database import get_db
from app.repositories.repository_factory import get_repositories, Repositories

# In any endpoint/service
async def my_handler(..., repos: Repositories = Depends(get_repositories)):
    pet = repos.pet.find_by_id(pet_id)           # Instead of db.query(Pet)...
    records = repos.preventive.find_by_pet_id(pet_id)  # Instead of db.query(PreventiveRecord)...
    return {"pet": pet, "records": records}
```

---

## File Migration Checklist

### Admin Services (6 files)

#### 1. **nudge_engine.py**
```python
# BEFORE (Direct queries)
pet = db.query(Pet).filter(Pet.id == pet_id).first()
preventive = db.query(PreventiveRecord).filter(...).all()
conditions = db.query(Condition).filter(...).all()

# AFTER (Repository pattern)
def generate_nudges(pet_id: UUID, repos: Repositories):
    pet = repos.pet.find_by_id(pet_id)
    preventive = repos.preventive.find_by_pet_id(pet_id)
    conditions = repos.health.find_active_conditions(pet_id)
```

**Queries to Replace**: 15+
**Key Methods**:
- `repos.pet.find_by_id()`
- `repos.preventive.find_by_pet_id()`
- `repos.health.find_active_conditions()`
- `repos.preventive_master.find_by_species()`
- `repos.nudge.find_active_for_pet()`

#### 2. **nudge_scheduler.py**
**Queries to Replace**: 12+
**Key Methods**:
- `repos.user.find_all_active()`
- `repos.pet.find_by_user_id()`
- `repos.nudge.log_delivery()`
- `repos.nudge.count_deliveries_today()`

#### 3. **reminder_engine.py**
**Queries to Replace**: 8+
**Key Methods**:
- `repos.reminder.find_due_today()`
- `repos.reminder.find_pending()`
- `repos.reminder.mark_sent()`
- `repos.user.find_by_id()`

#### 4. **conflict_expiry.py**
**Queries to Replace**: 3+
**Key Methods**:
- `repos.audit.find_active_conflicts()`
- `repos.audit.mark_conflict_resolved()`

#### 5. **nudge_config_service.py**
**Queries to Replace**: 2+
**Key Methods**:
- `repos.config.get_config()`
- `repos.config.set_config()`

#### 6. **preventive_seeder.py**
**Queries to Replace**: 2+
**Key Methods**:
- `repos.preventive_master.find_all()`
- `repos.user.find_all_active()`

### Shared Services (6 files)

#### 7. **care_plan_engine.py**
**Queries to Replace**: 5+
**Key Methods**:
- `repos.preventive.find_by_pet_id()`
- `repos.health.find_active_conditions()`
- `repos.pet.find_by_id()`

#### 8. **recommendation_service.py**
**Queries to Replace**: 3+
**Key Methods**:
- `repos.preventive_master.find_foods_by_species()`
- `repos.preventive_master.find_supplements_by_type()`

#### 9. **preventive_calculator.py**
**Queries to Replace**: 2+
**Key Methods**:
- `repos.preventive.find_by_pet_id()`
- `repos.preventive_master.find_by_category()`

#### 10. **gpt_extraction.py**
**Queries to Replace**: 2+
**Key Methods**:
- `repos.document.update_extraction_status()`
- `repos.preventive.find_by_pet_id()`

#### 11. **diet_service.py**
**Queries to Replace**: 3+
**Key Methods**:
- `repos.diet.find_by_pet_id()`
- `repos.diet.create()`
- `repos.diet.delete()`

#### 12. **document_upload.py**
**Queries to Replace**: 2+
**Key Methods**:
- `repos.document.create()`
- `repos.document.find_by_pet_id()`

### WhatsApp Handlers (6 files)

#### 13. **onboarding_handler.py**
**Queries to Replace**: 4+
**Key Methods**:
- `repos.user.find_by_whatsapp_id()`
- `repos.pet.find_by_user_id()`
- `repos.pet.create()`

#### 14. **order_handler.py**
**Queries to Replace**: 3+
**Key Methods**:
- `repos.cart.find_by_user_id()`
- `repos.order.create()`
- `repos.cart.clear_cart()`

#### 15. **document_handler.py**
**Queries to Replace**: 2+
**Key Methods**:
- `repos.document.create()`
- `repos.document.find_by_pet_id()`

#### 16. **query_handler.py**
**Queries to Replace**: 2+
**Key Methods**:
- `repos.pet.find_by_user_id()`
- `repos.health.find_active_conditions()`

#### 17. **reminder_handler.py**
**Queries to Replace**: 2+
**Key Methods**:
- `repos.reminder.find_by_id()`
- `repos.reminder.mark_acknowledged()`

#### 18. **conflict_handler.py**
**Queries to Replace**: 2+
**Key Methods**:
- `repos.audit.log_conflict()`
- `repos.audit.find_conflicts_by_pet()`

### Routers (4 files)

#### 19. **dashboard.py** (Largest file)
**Queries to Replace**: 10+
**Key Methods**:
- `repos.pet.find_by_id()`
- `repos.preventive.find_by_pet_id()`
- `repos.cart.find_by_user_id()`
- `repos.health.find_active_conditions()`
- `repos.diet.find_by_pet_id()`
- `repos.care.find_weight_history()`
- `repos.reminder.find_pending_for_pet()`

#### 20. **admin.py**
**Queries to Replace**: 8+
**Key Methods**:
- `repos.user.find_all_active()`
- `repos.pet.find_by_id()`
- `repos.user.count_all()`
- `repos.pet.count_all()`

#### 21. **webhook.py**
**Queries to Replace**: 2+
**Key Methods**:
- `repos.document.log_message()`
- `repos.user.find_by_whatsapp_id()`

#### 22. **internal.py**
**Queries to Replace**: 2+
**Key Methods**:
- `repos.reminder.find_due_today()`
- `repos.nudge.find_by_user_id()`

---

## Refactoring Steps (Phase B)

### For Each File:

1. **Add Import**
   ```python
   from app.repositories.repository_factory import get_repositories, Repositories
   ```

2. **Add `repos` Parameter**
   ```python
   # For services passed to routers
   async def my_service(pet_id: UUID, db: Session) -> Result:
       # BECOMES
       async def my_service(pet_id: UUID, db: Session, repos: Repositories) -> Result:

   # For routers with Depends
   @app.get("/pet/{pet_id}")
   async def get_pet(pet_id: UUID, repos = Depends(get_repositories)):
       # Now use repos instead of db
   ```

3. **Replace All Queries**
   ```python
   # BEFORE
   pet = db.query(Pet).filter(Pet.id == pet_id).first()
   
   # AFTER
   pet = repos.pet.find_by_id(pet_id)
   ```

4. **Remove db Parameter** (if only used for queries)
   ```python
   # If db is only for direct queries, you can remove it
   # If db is used for session management, keep it
   ```

---

## Testing the Integration

### Unit Test Template

```python
from unittest.mock import Mock, MagicMock
from app.repositories.repository_factory import Repositories
from app.services.admin.nudge_engine import generate_nudges

def test_nudge_generation():
    # Mock repositories
    mock_repos = Mock(spec=Repositories)
    mock_repos.pet = Mock()
    mock_repos.preventive = Mock()
    mock_repos.health = Mock()
    
    # Setup return values
    mock_repos.pet.find_by_id.return_value = Pet(id=..., name="Buddy")
    mock_repos.preventive.find_by_pet_id.return_value = [...]
    
    # Test with mocked repos
    result = generate_nudges(pet_id, mock_repos)
    
    # Verify repository was called
    mock_repos.pet.find_by_id.assert_called_once_with(pet_id)
```

---

## Verification Checklist

After refactoring each file:

- [ ] All `db.query()` calls removed
- [ ] No direct `.filter()` or `.where()` calls
- [ ] `repos` parameter added where needed
- [ ] All imports updated
- [ ] Type hints included for `repos: Repositories`
- [ ] Unit tests pass
- [ ] No new direct queries introduced

---

## Common Patterns

### Finding a Pet with Health Data
```python
# Old
pet = db.query(Pet).filter(Pet.id == pet_id).options(selectinload(...)).first()

# New
pet = repos.pet.find_by_id_with_relations(pet_id)  # Built-in eager loading
```

### Listing User's Pets
```python
# Old
pets = db.query(Pet).filter(Pet.user_id == user_id).all()

# New
pets = repos.pet.find_by_user_id(user_id)
```

### Checking Pet Status
```python
# Old
has_diet = db.query(DietItem).filter(DietItem.pet_id == pet_id).first() is not None

# New
has_diet = repos.diet.has_diet(pet_id)
```

### Batch Operations
```python
# Old
db.add_all(reminders)
db.commit()

# New
repos.reminder.bulk_create(reminders)
```

---

## Priority Order for Refactoring

**High Priority** (Most queries):
1. dashboard.py (10+ queries)
2. nudge_engine.py (15+ queries)
3. nudge_scheduler.py (12+ queries)
4. admin.py (8+ queries)

**Medium Priority** (5-10 queries):
5. reminder_engine.py
6. CareRepository users
7. health_trends_service

**Low Priority** (1-5 queries):
8. Remaining handlers and services

---

## Success Metrics

✅ All 25+ files refactored
✅ Zero direct queries outside repositories
✅ All tests passing
✅ Pre-commit hook prevents new violations
✅ Codebase is 100% repository-pattern compliant

