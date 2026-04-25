# Repository Pattern Adoption — Execution Plan

**Timeline**: 3-4 days | **Effort**: 40-50 hours | **Team**: 1 engineer

---

## Phase A: Foundation (Day 1)

### A1: Repository Base Class & Factory

Create `app/repositories/base_repository.py` with:
- Generic CRUD interface
- Common query patterns (find_by_id, find_all, create, update, delete)
- Eager loading helpers
- Transaction support

Create `app/repositories/repository_factory.py` for DI:
```python
def get_repositories(db: Session) -> Repositories:
    return Repositories(
        pet=PetRepository(db),
        preventive=PreventiveRepository(db),
        user=UserRepository(db),
        # ... all 12
    )
```

### A2: Lookup Repositories (2/12)

**PreventiveMasterRepository** (`app/repositories/preventive_master_repository.py`)
```
Methods:
  - find_by_species(species: str) -> List[PreventiveMaster]
  - find_all() -> List[PreventiveMaster]
  - find_by_id(id: UUID) -> PreventiveMaster
  - find_products_by_type(type: str) -> List[Product*]
  - get_breed_consequences(breed: str) -> List[BreedConsequence]
  - find_nudge_messages(level: int, breed: str) -> List[NudgeMessage]
  - get_template_config(template_name: str) -> WhatsAppTemplate
```

**ConfigRepository** (`app/repositories/config_repository.py`)
```
Models: NudgeConfig, NudgeMessageLibrary, WhatsAppTemplateConfig, BreedConsequenceLibrary
Methods:
  - get_config(key: str) -> NudgeConfig
  - set_config(key: str, value: str) -> None
  - find_nudge_messages_by_criteria(level, breed, category) -> List
  - get_template_by_name(name: str) -> WhatsAppTemplate
```

### A3: User/Contact Repositories (2/12)

**UserRepository** (`app/repositories/user_repository.py`)
```
Models: User, DashboardToken
Methods:
  - find_by_id(id: UUID) -> User
  - find_by_whatsapp_id(phone: str) -> User
  - find_all_active() -> List[User]
  - find_by_email(email: str) -> User
  - create(user: CreateUserRequest) -> User
  - update(id: UUID, data: dict) -> User
  - soft_delete(id: UUID) -> None
  - create_dashboard_token(pet_id: UUID) -> DashboardToken
  - find_token_by_value(token: str) -> DashboardToken
  - revoke_token(token_id: UUID) -> None
```

**ContactRepository** (`app/repositories/contact_repository.py`)
```
Models: Contact
Methods:
  - find_by_pet_id(pet_id: UUID) -> List[Contact]
  - find_by_id(id: UUID) -> Contact
  - find_by_pet_and_type(pet_id: UUID, type: str) -> List[Contact]
  - create(pet_id: UUID, data: dict) -> Contact
  - update(id: UUID, data: dict) -> Contact
  - delete(id: UUID) -> None
  - get_primary_vet(pet_id: UUID) -> Contact | None
```

### A4: Order/Cart Repositories (2/12)

**OrderRepository** (`app/repositories/order_repository.py`)
```
Models: Order, OrderRecommendation
Methods:
  - find_by_id(id: UUID) -> Order
  - find_by_pet_id(pet_id: UUID) -> List[Order]
  - find_by_user_id(user_id: UUID) -> List[Order]
  - find_pending() -> List[Order]
  - find_by_status(status: str) -> List[Order]
  - create(order: CreateOrderRequest) -> Order
  - update_status(id: UUID, status: str, notes: str = None) -> Order
  - delete(id: UUID) -> None
  - add_recommendation(order_id: UUID, product_id: UUID) -> OrderRecommendation
  - get_recommendations(order_id: UUID) -> List[OrderRecommendation]
```

**CartRepository** (`app/repositories/cart_repository.py`)
```
Models: CartItem
Methods:
  - find_by_user_id(user_id: UUID) -> List[CartItem]
  - find_by_id(id: UUID) -> CartItem
  - find_item(user_id: UUID, product_id: UUID) -> CartItem | None
  - add_item(user_id: UUID, product_id: UUID, quantity: int) -> CartItem
  - update_quantity(id: UUID, quantity: int) -> CartItem
  - remove_item(id: UUID) -> None
  - clear_cart(user_id: UUID) -> None
  - get_cart_total(user_id: UUID) -> float
  - bulk_add(user_id: UUID, items: List[CartItemData]) -> List[CartItem]
```

### A5: Health/Diet Repositories (2/12)

**DietRepository** (`app/repositories/diet_repository.py`)
```
Models: DietItem, FoodNutritionCache, NutritionTargetCache
Methods:
  - find_by_pet_id(pet_id: UUID) -> List[DietItem]
  - find_by_id(id: UUID) -> DietItem
  - create(pet_id: UUID, data: dict) -> DietItem
  - update(id: UUID, data: dict) -> DietItem
  - delete(id: UUID) -> None
  - get_nutrition_profile(pet_id: UUID) -> NutritionSummary
  - find_food_by_name(name: str) -> ProductFood
  - get_nutrition_cache(food_id: UUID) -> FoodNutritionCache
  - get_target_cache(pet_id: UUID) -> NutritionTargetCache
```

**CareRepository** (`app/repositories/care_repository.py`)
```
Models: HygienePreference, DiagnosticTestResult, WeightHistory
Methods:
  - find_hygiene_preference(pet_id: UUID) -> HygienePreference
  - create_or_update_hygiene(pet_id: UUID, data: dict) -> HygienePreference
  - find_diagnostics_by_pet(pet_id: UUID) -> List[DiagnosticTestResult]
  - find_diagnostic_by_id(id: UUID) -> DiagnosticTestResult
  - create_diagnostic(pet_id: UUID, data: dict) -> DiagnosticTestResult
  - get_last_checkup(pet_id: UUID) -> DiagnosticTestResult | None
  - find_weight_history(pet_id: UUID) -> List[WeightHistory]
  - add_weight_record(pet_id: UUID, weight: float) -> WeightHistory
  - get_ideal_weight_cache(pet_id: UUID) -> IdealWeightCache
```

### A6: Reminder/Nudge Repositories (2/12)

**ReminderRepository** (`app/repositories/reminder_repository.py`)
```
Models: Reminder
Methods:
  - find_by_pet_id(pet_id: UUID) -> List[Reminder]
  - find_by_id(id: UUID) -> Reminder
  - find_pending() -> List[Reminder]
  - find_pending_for_pet(pet_id: UUID) -> List[Reminder]
  - find_due_today() -> List[Reminder]
  - create(reminder: CreateReminderRequest) -> Reminder
  - update_status(id: UUID, status: str) -> Reminder
  - delete_expired() -> int  # returns count deleted
  - get_by_preventive_record_id(record_id: UUID) -> Reminder | None
  - mark_sent(id: UUID) -> Reminder
```

**NudgeRepository** (`app/repositories/nudge_repository.py`)
```
Models: Nudge, NudgeDeliveryLog, NudgeEngagement
Methods:
  - find_by_pet_id(pet_id: UUID) -> List[Nudge]
  - find_active_for_pet(pet_id: UUID) -> List[Nudge]
  - find_by_id(id: UUID) -> Nudge
  - create(nudge: CreateNudgeRequest) -> Nudge
  - update_status(id: UUID, dismissed: bool = None, acted_on: bool = None) -> Nudge
  - get_delivery_logs(nudge_id: UUID) -> List[NudgeDeliveryLog]
  - log_delivery(nudge_id: UUID, user_id: UUID) -> NudgeDeliveryLog
  - get_engagement_metrics(pet_id: UUID) -> NudgeEngagementStats
  - find_by_engagement(pet_id: UUID) -> NudgeEngagement
  - clear_inactive(days: int) -> int  # returns count cleared
```

### A7: Document/Message Repositories (2/12)

**DocumentRepository** (`app/repositories/document_repository.py`)
```
Models: Document, MessageLog
Methods:
  - find_by_pet_id(pet_id: UUID) -> List[Document]
  - find_by_id(id: UUID) -> Document
  - find_by_status(status: str) -> List[Document]
  - find_by_storage_backend(backend: str) -> List[Document]
  - create(document: CreateDocumentRequest) -> Document
  - update_extraction_status(id: UUID, status: str, extracted_data: dict = None) -> Document
  - mark_synced(id: UUID, backend: str) -> Document
  - find_unsynced_documents() -> List[Document]
  - log_message(message: MessageLog) -> MessageLog
  - find_message_logs(pet_id: UUID, limit: int = 100) -> List[MessageLog]
```

**AuditRepository** (`app/repositories/audit_repository.py`)
```
Models: ConflictFlag, DeferredCarePlanPending, PetAIInsight, AgentOrderSession, DashboardVisit
Methods:
  - log_conflict(pet_id: UUID, conflict_data: dict) -> ConflictFlag
  - find_conflicts_by_pet(pet_id: UUID) -> List[ConflictFlag]
  - find_active_conflicts() -> List[ConflictFlag]
  - clear_expired_conflicts(days: int) -> int
  - create_deferred_plan(pet_id: UUID, plan_data: dict) -> DeferredCarePlanPending
  - find_deferred_plans(pet_id: UUID) -> List[DeferredCarePlanPending]
  - log_ai_insight(pet_id: UUID, insight_data: dict) -> PetAIInsight
  - create_order_session(session_data: dict) -> AgentOrderSession
  - log_dashboard_visit(token_id: UUID) -> DashboardVisit
  - get_engagement_summary(pet_id: UUID) -> EngagementSummary
```

---

## Phase B: Bulk Refactoring (Days 2-3)

### B1: Admin Services Refactoring

**nudge_engine.py** (60 lines → 40 lines)
```python
# OLD
pet = db.query(Pet).filter(Pet.id == pet_id).first()
preventive = db.query(PreventiveRecord).filter(...).first()
conditions = db.query(Condition).filter(...).all()

# NEW
pet = repos.pet.find_by_id(pet_id)
preventive = repos.preventive.find_latest_by_pet_and_type(pet_id, type)
conditions = repos.health.find_active_conditions(pet_id)
```

**nudge_scheduler.py** (80 lines → 50 lines)
```python
# OLD
users = db.query(User).filter(User.is_deleted == False).all()
pets = db.query(Pet).filter(Pet.user_id == user.id).all()

# NEW
users = repos.user.find_all_active()
for user in users:
    pets = repos.pet.find_by_user_id(user.id)
```

**reminder_engine.py** (50 lines → 30 lines)
```python
# OLD
reminders = db.query(Reminder).filter(Reminder.status == "pending").all()

# NEW
reminders = repos.reminder.find_pending()
```

### B2: Shared Services Refactoring

**care_plan_engine.py**
```python
# OLD
records = db.query(PreventiveRecord).filter(PreventiveRecord.pet_id == pet_id).all()
conditions = db.query(Condition).filter(Condition.pet_id == pet_id).all()

# NEW
records = repos.preventive.find_by_pet_id(pet_id)
conditions = repos.health.find_active_conditions(pet_id)
```

**recommendation_service.py**
```python
# OLD
products = db.query(ProductFood).filter(ProductFood.suitable_for == species).all()

# NEW
products = repos.preventive_master.find_products_by_species(species)
```

**diet_service.py**
```python
# OLD
diet_items = db.query(DietItem).filter(DietItem.pet_id == pet_id).all()

# NEW
diet_items = repos.diet.find_by_pet_id(pet_id)
```

### B3: WhatsApp Handlers Refactoring

**onboarding.py**
```python
# OLD
user = db.query(User).filter(User.whatsapp_id == phone).first()

# NEW
user = repos.user.find_by_whatsapp_id(phone)
```

**order_service.py**
```python
# OLD
cart = db.query(CartItem).filter(CartItem.user_id == user_id).all()

# NEW
cart = repos.cart.find_by_user_id(user_id)
```

**query_engine.py**
```python
# OLD
pet = db.query(Pet).filter(Pet.id == pet_id).first()

# NEW
pet = repos.pet.find_by_id(pet_id)
```

### B4: Routers Refactoring

**dashboard.py** (200 lines → 120 lines)
```python
# OLD
pet = db.query(Pet).filter(Pet.id == pet_id).first()
preventive = db.query(PreventiveRecord).filter(...).all()
cart = db.query(CartItem).filter(CartItem.user_id == user_id).all()

# NEW
pet = repos.pet.find_by_id(pet_id)
preventive = repos.preventive.find_by_pet_id(pet_id)
cart = repos.cart.find_by_user_id(user_id)
```

**admin.py** (180 lines → 110 lines)
```python
# OLD
stats = {
    "users": db.query(User).count(),
    "pets": db.query(Pet).count(),
}

# NEW
stats = {
    "users": repos.user.count_all(),
    "pets": repos.pet.count_all(),
}
```

---

## Phase C: Verification (Day 4)

### C1: Codebase Scan
```bash
# Should return ZERO hits
grep -r "db\.query\|session\.query" backend/app --exclude-dir=repositories
grep -r "\.filter\|\.where" backend/app/services --exclude-dir=repositories
```

### C2: Pre-Commit Hook
Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
if grep -r "db\.query\|session\.query" backend/app/services backend/app/routers backend/app/handlers backend/app/domain 2>/dev/null; then
    echo "❌ ERROR: Direct database queries found outside repositories"
    exit 1
fi
```

### C3: Documentation Update
- Update CLAUDE.md with repository pattern requirements
- Add repository method naming conventions
- Update architecture diagram

---

## File Checklist

### Repositories to Create (12 files)
- [ ] `app/repositories/base_repository.py` — Base class
- [ ] `app/repositories/repository_factory.py` — DI factory
- [ ] `app/repositories/preventive_master_repository.py` — Lookups
- [ ] `app/repositories/config_repository.py` — Config
- [ ] `app/repositories/user_repository.py` — Users + tokens
- [ ] `app/repositories/contact_repository.py` — Contacts
- [ ] `app/repositories/order_repository.py` — Orders
- [ ] `app/repositories/cart_repository.py` — Cart
- [ ] `app/repositories/diet_repository.py` — Diet
- [ ] `app/repositories/care_repository.py` — Care records
- [ ] `app/repositories/reminder_repository.py` — Reminders
- [ ] `app/repositories/nudge_repository.py` — Nudges
- [ ] `app/repositories/document_repository.py` — Documents
- [ ] `app/repositories/audit_repository.py` — Audit trail

### Services to Refactor (12 files)
**Admin** (6):
- [ ] `app/services/admin/nudge_engine.py`
- [ ] `app/services/admin/nudge_scheduler.py`
- [ ] `app/services/admin/reminder_engine.py`
- [ ] `app/services/admin/conflict_expiry.py`
- [ ] `app/services/admin/nudge_config_service.py`
- [ ] `app/services/admin/preventive_seeder.py`

**Shared** (6):
- [ ] `app/services/shared/care_plan_engine.py`
- [ ] `app/services/shared/recommendation_service.py`
- [ ] `app/services/shared/preventive_calculator.py`
- [ ] `app/services/shared/diet_service.py`
- [ ] `app/services/shared/gpt_extraction.py`
- [ ] `app/services/shared/document_upload.py`

### Handlers to Refactor (6 files)
- [ ] `app/handlers/onboarding_handler.py`
- [ ] `app/handlers/order_handler.py`
- [ ] `app/handlers/document_handler.py`
- [ ] `app/handlers/query_handler.py`
- [ ] `app/handlers/reminder_handler.py`
- [ ] `app/handlers/conflict_handler.py`

### Routers to Refactor (4 files)
- [ ] `app/routers/dashboard.py`
- [ ] `app/routers/admin.py`
- [ ] `app/routers/webhook.py`
- [ ] `app/routers/internal.py`

### Domain Services to Refactor (3 files)
- [ ] `app/domain/health/health_service.py` (minimal)
- [ ] `app/domain/reminders/reminder_service.py`
- [ ] `app/domain/orders/order_service.py`

---

## Success Criteria

✅ All 84 files scanning for `db.query()` return zero hits outside `repositories/`
✅ All 12 repositories implemented with full type hints
✅ All services/routers/handlers use dependency-injected repositories
✅ Test coverage maintained (80%+)
✅ Pre-commit hook prevents future violations
✅ Documentation updated with patterns & examples

