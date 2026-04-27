# Input Validation Specification

**Status:** Phase 3 (Deferred from audit)  
**Last Updated:** 2026-04-27

## Principle

> **Backend is the source of truth for all validation.**  
> Frontend validation is UX optimization only — it provides immediate feedback but does NOT enforce business rules.

## Validation Rules by Domain

### Pet Profile

| Field | Type | Min | Max | Backend Check | Frontend Check |
|-------|------|-----|-----|----------------|----------------|
| `name` | string | 1 char | 100 chars | Required, non-empty | Required, trim, max 100 |
| `species` | enum | — | — | IN ('dog', 'cat') | SELECT dropdown |
| `breed` | string | 1 char | 100 chars | Optional, max 100 | Optional, max 100 |
| `gender` | enum | — | — | IN ('male', 'female') | SELECT dropdown |
| `dob` | date | — | — | Valid ISO date, <= today | Valid date picker, <= today |
| `weight` | number | 0.1 | 999.99 | Range validation | Range input, 0.1–999.99 |
| `neutered` | boolean | — | — | — | Checkbox |

**Backend Source:** `backend/app/routers/dashboard.py` → `update_pet_profile` endpoint  
**Frontend:** `frontend/src/components/tabs/OverviewTab.tsx` → pet profile edit form

---

### Weight History

| Field | Type | Min | Max | Backend Check | Frontend Check |
|-------|------|-----|-----|----------------|----------------|
| `weight` | number | 0.1 | 999.99 | Range validation | Range input, 0.1–999.99 |
| `recorded_at` | date | — | — | Valid ISO date, <= today | Valid date picker, <= today |
| `note` | string | 0 chars | 500 chars | Optional, max 500 | Optional, max 500 |

**Backend Source:** `backend/app/routers/dashboard.py` → `add_weight_entry` endpoint  
**Frontend:** `frontend/src/components/tabs/HealthTab.tsx` → weight entry form

---

### Checkup Records

| Field | Type | Min | Max | Backend Check | Frontend Check |
|-------|------|-----|-----|----------------|----------------|
| `visited_at` | date | — | — | Valid ISO date, <= today | Valid date picker, <= today |
| `vet_name` | string | 0 chars | 100 chars | Optional, max 100 | Optional, max 100 |
| `clinic_name` | string | 0 chars | 100 chars | Optional, max 100 | Optional, max 100 |
| `notes` | string | 0 chars | 1000 chars | Optional, max 1000 | Optional, max 1000 |

**Backend Source:** `backend/app/routers/dashboard.py` → `add_checkup_record` endpoint  
**Frontend:** `frontend/src/components/tabs/HealthTab.tsx` → checkup form

---

### Cart & Orders

| Field | Type | Min | Max | Backend Check | Frontend Check |
|-------|------|-----|-----|----------------|----------------|
| `quantity` | integer | 1 | 10 | Range (1–10) | Range input, 1–10 |
| `price` | integer | 1 | 10000000 (100k INR) | Positive, max 100k | Display only (no client edit) |

**Backend Source:** `backend/app/domain/orders/cart_logic.py` → `is_valid_quantity()`, `is_valid_price()`  
**Frontend:** `frontend/src/components/CartView.tsx` → quantity controls

---

## Validation Implementation Pattern

### Backend (Source of Truth)

```python
# In backend/app/domain/{domain}/{entity}_logic.py
def validate_weight(weight: float) -> tuple[bool, str]:
    """
    Validate weight value.
    
    Returns:
        (is_valid, error_message)
    """
    if not isinstance(weight, (int, float)):
        return False, "Weight must be a number"
    if weight <= 0 or weight > 999.99:
        return False, "Weight must be between 0.1 and 999.99 kg"
    return True, ""


# In backend/app/routers/dashboard.py
@router.post("/dashboard/{token}/add-weight")
async def add_weight(token: str, request: AddWeightRequest, db: Session):
    is_valid, error = validate_weight(request.weight)
    if not is_valid:
        return {"success": False, "error": error}
    # ... proceed with add
```

### Frontend (UX Optimization)

```typescript
// In frontend/src/components/{component}.tsx
// IMPORTANT: This is DISPLAY logic only, not enforcement
const [weight, setWeight] = useState("");

const isWeightValid = () => {
  const w = parseFloat(weight);
  return !isNaN(w) && w > 0 && w <= 999.99;
};

return (
  <input
    type="number"
    min="0.1"
    max="999.99"
    step="0.1"
    value={weight}
    onChange={(e) => setWeight(e.target.value)}
    disabled={!isWeightValid()}
  />
);
```

---

## Validation Categories

### 1. Format Validation (Frontend + Backend)
- Date formats (ISO 8601)
- Email addresses
- Phone numbers (if applicable)

### 2. Range Validation (Frontend + Backend)
- Numeric bounds (weight, price, quantity)
- String length (name, notes)
- Date ranges (DOB <= today)

### 3. Business Rule Validation (Backend Only)
- Minimum order value checks (cart_logic)
- Duplicate prevention (unique constraints)
- Status transitions (state machine logic)
- Permission checks (access control)

### 4. Consistency Validation (Backend Only)
- Foreign key integrity (pet exists, category valid)
- Enum values (species IN ('dog', 'cat'))
- Calculated field consistency (total = subtotal + fee)

---

## Testing Strategy

### Unit Tests (Backend)
```bash
# Test all validators in isolation
cd backend && pytest tests/unit/test_pet_logic.py::test_validate_weight -v
```

### Integration Tests (Backend + DB)
```bash
# Test validators in context of API endpoints
cd backend && pytest tests/integration/test_dashboard_endpoints.py -v
```

### E2E Tests (Full Flow)
```bash
# Test that frontend validates like backend, and backend still rejects invalid input
cd frontend && npm run test:e2e
```

---

## Migration Checklist

- [ ] Document all current validation rules in this spec
- [ ] Add type hints and docstrings to all validators
- [ ] Link frontend validation comments to backend source
- [ ] Create unit tests for all backend validators
- [ ] Create integration tests for all API endpoints
- [ ] Verify frontend validation mirrors backend (not enforces)
- [ ] Document expected error messages for each validation failure
- [ ] Review for edge cases (null, empty string, very large numbers, etc.)

---

## Common Mistakes to Avoid

❌ **WRONG:** Frontend rejects, backend allows → confusion
```typescript
// Frontend accepts only "YYYY-MM-DD"
if (!date.match(/^\d{4}-\d{2}-\d{2}$/)) {
  return error;
}
```
Backend might accept "2024-01-01" or "01/01/2024". **Mismatch.**

✅ **RIGHT:** Backend is authoritative
```typescript
// Frontend provides input picker/mask
// Backend validates all possible formats
// If backend rejects, show backend error message
```

---

## Deferred Work

- [ ] Create shared validation schema (JSON Schema / OpenAPI) for both backend and frontend
- [ ] Add database-level constraints (CHECK, UNIQUE, NOT NULL) as second validation layer
- [ ] Implement rate limiting on data modification endpoints (POST/PUT/DELETE)
