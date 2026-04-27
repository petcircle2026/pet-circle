# Phase 4: Testing Implementation Plan

**Start Date:** 2026-04-27  
**Goal:** Complete all deferred testing from the Comprehensive Logic Audit Report

---

## Testing Scope

### 1. Unit Tests (Backend)

#### 1.1 `test_preventive_logic.py` — Vaccine Eligibility
- **File:** `tests/unit/test_preventive_logic.py`
- **Function Under Test:** `is_vaccine_eligible_for_age(vaccine_item_name, pet_age_days, species)`
- **Test Cases:**
  - Puppy vaccines show only for puppies (age < 365 days)
  - Adult vaccines hide puppy vaccines (age >= 365 days)
  - Vaccines with minimum age are filtered correctly
  - Species-specific filtering (dogs vs cats)
  - Edge case: exactly 365 days
  - Edge case: 364 days (still puppy)
  - None age_days input handled gracefully
  - Unknown vaccine name returns False
- **Coverage Target:** 100% of `preventive_logic.py`

#### 1.2 `test_date_utils.py` — UTC Date Arithmetic
- **File:** `tests/unit/test_date_utils.py`
- **Functions Under Test:**
  - `today_utc()`
  - `now_utc()`
  - `parse_iso_date(iso_string)`
  - `to_iso_date(d)`
  - `days_between(start, end)`
  - `add_days(d, days)`
  - `subtract_days(d, days)`
- **Test Cases:**
  - Basic date arithmetic (add/subtract days)
  - Parse ISO 8601 dates
  - Round-trip conversion (date → ISO → date)
  - Negative day differences (backwards dates)
  - Edge case: Feb 29 (leap year)
  - Edge case: Year boundary (Dec 31 → Jan 1)
  - UTC consistency (no timezone conversions)
- **Coverage Target:** 100% of `date_utils.py`

#### 1.3 `test_cart_logic.py` — Cart Summary
- **File:** `tests/unit/test_cart_logic.py`
- **Functions Under Test:**
  - `calculate_delivery_fee(subtotal_paise)`
  - `calculate_cart_summary(items)`
- **Test Cases:**
  - Free delivery threshold exactly (599.00 INR)
  - Just under free delivery (598.99 INR)
  - Just over free delivery (599.01 INR)
  - Empty cart
  - Single item
  - Multiple items with different quantities
  - Paise rounding edge cases (e.g., 599.005 INR)
  - Zero subtotal (free items only)
- **Coverage Target:** 100% of `cart_logic.py`

### 2. Integration Tests (Backend)

#### 2.1 `test_dashboard_preventives.py` — Preventive API
- **File:** `tests/integration/test_dashboard_preventives.py`
- **Endpoint:** `GET /dashboard/{token}/preventives/{pet_id}`
- **Test Cases:**
  - API returns `eligible` flag for each preventive
  - Eligible flag correctly computed for age
  - Puppy vaccines filtered by age
  - Adult vaccines shown after 365 days
  - Status field matches `get_preventive_status()` logic
  - Overdue preventives shown correctly
  - 200+ days old preventives still show status
- **Database Setup:** Pet with DOB that results in various ages

#### 2.2 `test_cart_service_integration.py` — Cart Service
- **File:** `tests/integration/test_cart_service_integration.py`
- **Functions Under Test:**
  - `get_cart(user_id)`
  - `add_to_cart(user_id, sku, quantity)`
  - `remove_from_cart(user_id, sku)`
  - `place_order(user_id, items)`
- **Test Cases:**
  - Cart returned with delivery fee calculated correctly
  - Adding items updates total correctly
  - Removing items updates total correctly
  - Delivery fee changes when crossing 599 INR threshold
  - `place_order` resolves prices from DB (not client)
  - SKU price lookup returns correct discounted price
  - Cart total matches backend calculation (no client tampering)
- **Database Setup:** Products with prices, user cart

#### 2.3 `test_onboarding_validation.py` — Validation Rules
- **File:** `tests/integration/test_onboarding_validation.py`
- **Test Cases:**
  - Pet DOB parsing (multiple date formats)
  - Weight validation (0 < w ≤ 999.99)
  - Species validation (dog, cat, bird, etc.)
  - Breed validation
  - Conflict detection (DOB conflicts, duplicate pets)
  - Error messages match `VALIDATION_SPECIFICATION.md`
- **Database Setup:** Existing pets with conflicts

### 3. End-to-End Tests (Frontend)

#### 3.1 Cart Flow E2E
- **File:** `frontend/e2e/cart.spec.ts`
- **Scenario:** Add item → see delivery fee → checkout → payment → success
- **Assertions:**
  - Cart total includes delivery fee
  - Crossing 599 INR threshold removes delivery fee
  - Payment integrates with Razorpay
  - Order confirmation displays correctly
  - Order stored in database

#### 3.2 Vaccine Eligibility E2E
- **File:** `frontend/e2e/vaccine-eligibility.spec.ts`
- **Scenario:** Create puppy → view health tab → see only puppy vaccines
- **Assertions:**
  - Puppy vaccines shown for puppies (< 365 days)
  - Adult vaccines shown for adults (>= 365 days)
  - Age-based filtering works without JavaScript (backend logic)
  - Filter button responsive

#### 3.3 Validation Messages E2E
- **File:** `frontend/e2e/validation.spec.ts`
- **Scenario:** Try invalid input → see error → fix → submit → success
- **Assertions:**
  - Frontend validation shows immediately (UX)
  - Backend validation enforced (security)
  - Error messages match spec
  - Success message after valid submit

### 4. Regression Tests

#### 4.1 Full Dashboard Load
- **File:** `tests/e2e/dashboard-load.spec.ts`
- **Scenario:** Load dashboard for pet with:
  - Multiple preventive records
  - Various statuses (overdue, upcoming, up_to_date)
  - Weight history (5+ entries)
  - Cart items (5+ items)
  - Active conditions (2+)
- **Assertions:**
  - All tabs load without errors
  - Data displays correctly
  - No console errors
  - Network requests complete < 3s
  - Dashboard token validates correctly

#### 4.2 Order Placement Flow
- **File:** `tests/e2e/order-flow.spec.ts`
- **Scenario:** Add items → checkout → payment → confirmation
- **Assertions:**
  - Cart subtotal computed correctly
  - Delivery fee applied correctly
  - Total shows correctly
  - Order saved to database
  - Order confirmation email sent
  - Admin notification sent to ORDER_NOTIFICATION_PHONE

---

## Implementation Order

1. ✅ **Day 1:** Unit tests for `date_utils.py` and `preventive_logic.py`
2. ✅ **Day 2:** Unit tests for `cart_logic.py`
3. ✅ **Day 3:** Integration tests for preventives and cart
4. ✅ **Day 4:** Integration tests for validation
5. ✅ **Day 5–6:** E2E tests (cart, vaccines, validation)
6. ✅ **Day 7:** Regression tests (dashboard, orders)

---

## Coverage Goals

| Module | Current | Target | Status |
|--------|---------|--------|--------|
| `preventive_logic.py` | 60% | 100% | IN PROGRESS |
| `date_utils.py` | 0% (new) | 100% | PENDING |
| `cart_logic.py` | 70% | 100% | PENDING |
| `cart_service.py` | 50% | 85% | PENDING |
| `preventive_service.py` | 60% | 85% | PENDING |
| `dashboard_service.py` | 40% | 70% | PENDING |
| Frontend components | 30% | 60% (E2E only) | PENDING |

---

## Test Execution Commands

```bash
# All unit tests
make test-unit

# Specific test file
cd backend && APP_ENV=test pytest tests/unit/test_date_utils.py -v

# Integration tests
cd backend && APP_ENV=test pytest tests/integration/ -v

# Coverage report
cd backend && APP_ENV=test pytest --cov=app tests/ --cov-report=html

# E2E tests
cd frontend && npm run test:e2e

# Full test suite (unit + integration + E2E)
make test
```

---

## Definition of Done

- [ ] All unit tests pass (100% coverage for new code)
- [ ] All integration tests pass
- [ ] All E2E tests pass
- [ ] Coverage report generated: `backend/htmlcov/index.html`
- [ ] No flaky tests (each test passes 5 consecutive runs)
- [ ] Test documentation updated in CLAUDE.md
- [ ] All critical/high-priority issues from audit covered by tests

---

## Notes

- Tests run in `APP_ENV=test` with SQLite in-memory database
- No external dependencies (mocked: WhatsApp API, GCP Storage, OpenAI)
- Fixtures defined in `conftest.py` — reuse existing fixtures for consistency
- E2E tests use Playwright with headless Chrome
