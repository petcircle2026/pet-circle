# Repository Pattern Adoption Audit

**Status**: ⚠️ Incomplete (84 files with direct DB queries found)
**Scope**: Enforce repository pattern across entire codebase
**Goal**: Zero direct database queries outside of repository layer

---

## Executive Summary

- **Current State**: Mixed — 3 repositories exist (Pet, Preventive, Health) but 84+ files still execute direct queries
- **Violation Count**: 50+ direct `db.query()` patterns found in services, routers, handlers, domain logic
- **Affected Domains**: Admin, Shared Services, WhatsApp Handlers, Routers, Domain Services
- **Effort**: 40-50 hours (3-4 day sprint for 1 engineer)
- **Impact**: Critical — enables data access layer consolidation, testing, schema evolution

---

## Existing Repositories (3/12)

| Repository | Location | Status | Methods | Models |
|---|---|---|---|---|
| **PetRepository** | `app/repositories/pet_repository.py` | ✅ READY | 18 | Pet, Weight |
| **PreventiveRepository** | `app/repositories/preventive_repository.py` | ✅ READY | 20 | PreventiveRecord, CustomPreventive |
| **HealthRepository** | `app/repositories/health_repository.py` | ✅ READY | 25 | Conditions, Medications, Diagnostics |

---

## Required Repositories (12 Total)

### Lookup/Config Repositories (2)
1. **PreventiveMasterRepository** — Read-only reference data
   - Models: PreventiveMaster, ProductMedicines, ProductFood, ProductSupplement
   - Methods: find_by_species, find_all, get_by_id, list_by_category

2. **ConfigRepository** — System configuration & lookups
   - Models: NudgeConfig, NudgeMessageLibrary, WhatsAppTemplateConfig, BreedConsequenceLibrary
   - Methods: get_config_by_key, list_nudge_messages, get_template_by_name

### User/Contact Repositories (2)
3. **UserRepository** — User management
   - Models: User, DashboardToken
   - Methods: find_by_id, find_by_whatsapp_id, find_all_active, soft_delete

4. **ContactRepository** — Pet contact management
   - Models: Contact
   - Methods: find_by_pet_id, create, update, delete

### Order/Cart Repositories (2)
5. **OrderRepository** — Order management
   - Models: Order, OrderRecommendation
   - Methods: find_by_id, find_by_pet_id, find_by_user_id, create, update_status, list_pending

6. **CartRepository** — Shopping cart
   - Models: CartItem
   - Methods: find_by_user_id, add_item, remove_item, update_quantity, clear_cart, get_total

### Health/Diet/Care Repositories (2)
7. **DietRepository** — Nutrition management
   - Models: DietItem, FoodNutritionCache, NutritionTargetCache
   - Methods: find_by_pet_id, find_by_id, create, update, delete, get_nutrition_profile

8. **CareRepository** — Hygiene, checkups, diagnostics
   - Models: HygienePreference, DiagnosticTestResult, WeightHistory
   - Methods: find_by_pet_id, create, update, list_by_type, get_last_by_type

### Reminder/Nudge Repositories (2)
9. **ReminderRepository** — Reminder management
   - Models: Reminder, ReminderTemplate
   - Methods: find_by_pet_id, find_pending, create, update_status, delete_expired

10. **NudgeRepository** — Nudge campaigns
    - Models: Nudge, NudgeDeliveryLog, NudgeEngagement
    - Methods: find_by_pet_id, find_active, create, update_status, get_delivery_stats

### Document/Message Repositories (2)
11. **DocumentRepository** — Uploaded documents
    - Models: Document, MessageLog
    - Methods: find_by_pet_id, create, update_extraction_status, get_by_storage_backend, mark_synced

12. **AuditRepository** — Audit trail & conflicts
    - Models: ConflictFlag, DeferredCarePlanPending, PetAIInsight, AgentOrderSession, DashboardVisit
    - Methods: find_by_pet_id, find_by_user_id, create, log_conflict, get_engagement_metrics

---

## Current Violations by Location

### Admin Services (50+ violations)
- **conflict_expiry.py** — Direct ConflictFlag queries
- **nudge_config_service.py** — Direct NudgeConfig queries
- **nudge_engine.py** — 15+ direct queries (PreventiveRecord, PreventiveMaster, ProductMedicines, etc.)
- **nudge_scheduler.py** — 12+ direct queries (User, Pet, PreventiveRecord, NudgeDeliveryLog)
- **reminder_engine.py** — 8+ direct queries (Reminder, User, Pet, PreventiveRecord)
- **preventive_seeder.py** — Seed operations (acceptable but should use repository)

### Shared Services (20+ violations)
- **care_plan_engine.py** — Direct PreventiveRecord, Condition queries
- **recommendation_service.py** — Direct Product* queries
- **preventive_calculator.py** — Direct PreventiveRecord queries
- **gpt_extraction.py** — Direct Document queries
- **document_upload.py** — Direct Document queries
- **diet_service.py** — Direct DietItem queries
- **precompute_service.py** — Multiple direct queries

### WhatsApp Handlers (15+ violations)
- **agentic_edit.py** — Direct model queries
- **reminder_response.py** — Direct Reminder queries
- **query_engine.py** — Direct Pet queries
- **order_service.py** — Direct Order queries
- **onboarding.py** — Direct User, Pet, PreventiveRecord queries
- **message_router.py** — Direct MessageLog queries
- **conflict_engine.py** — Direct ConflictFlag queries

### Routers (15+ violations)
- **dashboard.py** — 10+ direct queries across models
- **admin.py** — 8+ direct queries for stats and updates
- **webhook.py** — Direct MessageLog, User queries
- **internal.py** — Direct reminder trigger queries

### Domain Services (5+ violations)
- **health_service.py** — Uses repositories ✅ COMPLIANT
- **reminder_service.py** — Some direct queries
- **order_service.py** — Duplicate logic in domain and services layer

---

## Adoption Strategy

### Phase A: Foundation (2-3 days)
1. Create all 12 repositories with full method signatures
2. Include comprehensive docstrings and type hints
3. Add builder-pattern query methods for complex filters
4. Create repository factories/DI for easy injection

### Phase B: Bulk Refactoring (3-4 days)
1. **Batch 1**: Admin services (nudge_engine, nudge_scheduler, reminder_engine)
2. **Batch 2**: Shared services (care_plan, recommendation, diet, documents)
3. **Batch 3**: WhatsApp handlers (onboarding, order, query, conflict)
4. **Batch 4**: Routers (dashboard, admin, webhook, internal)

### Phase C: Verification (1 day)
1. Scan codebase for remaining violations
2. Add pre-commit hook to prevent new direct queries
3. Update documentation

---

## Expected Benefits

✅ **Testability**: All services can be tested with mock repositories
✅ **Data Migration**: Switch storage backends (Supabase → MongoDB) without service changes
✅ **Schema Evolution**: Centralized query management for schema changes
✅ **Performance**: Single point to optimize N+1 queries, add caching
✅ **Consistency**: All database rules enforced in one place

---

## Next Steps

1. [ ] User approval on repository list (12 repos above)
2. [ ] Create repository interfaces/base classes
3. [ ] Implement all 12 repositories
4. [ ] Refactor admin services → repositories
5. [ ] Refactor shared services → repositories
6. [ ] Refactor WhatsApp handlers → repositories
7. [ ] Refactor routers → repositories
8. [ ] Add pre-commit hook validation
9. [ ] Documentation update

