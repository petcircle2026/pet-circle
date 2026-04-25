# Frontend Architecture Refactoring — Executive Summary

**Date:** 2026-04-25  
**Project:** PetCircle  
**Scope:** React Frontend (`frontend/src/`)  
**Goal:** Align implementation with architectural constraints without affecting output  

---

## What Was Audited

- **42 component files** (`.tsx`, `.ts`)
- **~4000+ lines** of component code
- **6 utility/library files** for constants and helpers
- **CSS architecture** (`globals.css`)

---

## Three Violations Found

### 1. **Inline Styles (453 instances)**
   - **Impact:** Zero on output; pure implementation detail
   - **Scope:** BottomSheet, CarePlanCard, DietAnalysisCard, DashboardClient, ProfileBanner, Admin components
   - **Fix:** Move to CSS variables and utility classes in `globals.css`
   - **Effort:** ~4 hours

### 2. **Hardcoded Class Names & Attributes (~200+ instances)**
   - **Impact:** Zero on output; pure implementation detail
   - **Scope:** All component files, especially admin components
   - **Fix:** Create constant files (`css-classes.ts`, `aria-labels.ts`, `data-attributes.ts`)
   - **Effort:** ~3 hours

### 3. **Business Logic in Components (6 files)**
   - **Impact:** Zero on output; same computation, same correctness
   - **Scope:** Cart calculations, dashboard fetching, scroll management, data grouping, date formatting
   - **Fix:** Extract to custom hooks and utility functions
   - **Effort:** ~5 hours

---

## Key Finding

**All violations are internal implementation details.** The frontend renders identically before and after refactoring. No UI/UX changes needed; no API changes required; no user-facing modifications.

---

## Refactoring Plan at a Glance

| Phase | Focus | Time | Files | Breaking? |
|-------|-------|------|-------|---|
| 1 | CSS Variables & Utility Classes | 1–2h | `globals.css` | ✓ No |
| 2 | Extract Constants (classes, labels) | 2–3h | New files + 6 components | ✓ No |
| 3 | Extract Business Logic (hooks/utils) | 4–5h | New files + 8 components | ✓ No |
| 4 | Replace Inline Styles | 3–4h | 6 main components | ✓ No |
| **Total** | | **10–14h** | | **✓ Non-Breaking** |

---

## New Files to Create

### Phase 1
- (CSS updates only to existing `globals.css`)

### Phase 2
- `frontend/src/lib/css-classes.ts` — Layout, button, status, admin class constants
- `frontend/src/lib/aria-labels.ts` — Accessibility labels
- `frontend/src/lib/data-attributes.ts` — Data attributes for testing/styling

### Phase 3
- `frontend/src/hooks/useCartCalculations.ts` — Cart math (delivery fee, totals)
- `frontend/src/hooks/useScrollLock.ts` — Body overflow management
- `frontend/src/hooks/useDashboardData.ts` — API fetch, caching, stale-while-revalidate
- `frontend/src/utils/cart-utils.ts` — Search result grouping
- `frontend/src/utils/profile-utils.ts` — Vet date formatting

---

## Post-Refactoring Compliance

### ✓ Frontend Constraints Met
- No inline `style={{}}` in components
- All class names referenced from constants
- Business logic extracted to hooks/utilities

### ✓ CSS Centralization Met
- All styles in `globals.css` (variables + classes)
- No hardcoded color/size values
- CSS variables for all theme values

### ✓ Attribute Management Met
- All class names from `css-classes.ts` constants
- All labels from `aria-labels.ts` constants
- All data attributes from `data-attributes.ts` constants

---

## Quality Assurance Strategy

### Before Each Phase
- [ ] `npm run dev` works
- [ ] Dashboard renders in all tabs
- [ ] Visual inspection: colors, spacing match

### After Each Phase
- [ ] `tsc --noEmit` passes (type check)
- [ ] `npm run lint` passes (ESLint)
- [ ] `npm run build` succeeds (production build)
- [ ] DevTools computed styles unchanged

### After All Phases
- [ ] E2E tests pass (cart flow, document upload)
- [ ] Lighthouse score maintained or improved
- [ ] Pixel-perfect visual match (before/after comparison)
- [ ] Keyboard navigation works
- [ ] Screen reader announcements correct

---

## Risk Assessment

| Risk | Probability | Severity | Mitigation |
|---|---|---|---|
| Styling breaks on mobile | Low | High | Visual QA on iOS/Android |
| Type errors after extraction | Low | Low | `tsc --noEmit` before commit |
| Missed hardcoded values | Medium | Low | Grep for remaining violations |
| Component output differs | Very Low | Critical | Pixel-perfect visual comparison |

---

## Git Strategy

```bash
# Phase 1
git add frontend/src/app/globals.css
git commit -m "chore: Add CSS variables and utility classes for Phase 1 refactor"

# Phase 2
git add frontend/src/lib/css-classes.ts frontend/src/lib/aria-labels.ts frontend/src/lib/data-attributes.ts
git add frontend/src/components/**/*.tsx  # Components that use constants
git commit -m "refactor: Extract hardcoded class names and aria-labels to constants (Phase 2)"

# Phase 3
git add frontend/src/hooks/ frontend/src/utils/
git add frontend/src/components/**/*.tsx  # Components using hooks/utils
git commit -m "refactor: Extract business logic to hooks and utilities (Phase 3)"

# Phase 4
git add frontend/src/app/globals.css
git add frontend/src/components/**/*.tsx  # Components with replaced inline styles
git commit -m "refactor: Replace inline styles with CSS variables and utility classes (Phase 4)"
```

---

## Documentation Artifacts

Three documents created to guide implementation:

1. **`FRONTEND_AUDIT.md`** — Detailed violation analysis, current strengths, refactoring plan with code examples
2. **`FRONTEND_REFACTOR_CHECKLIST.md`** — Step-by-step task checklist for each phase with code snippets
3. **`REFACTOR_SUMMARY.md`** (this file) — High-level overview and executive summary

---

## Next Steps

**To proceed:**

1. ✓ Review `FRONTEND_AUDIT.md` for violation details and Phase 1–4 breakdown
2. ✓ Review `FRONTEND_REFACTOR_CHECKLIST.md` for detailed implementation steps
3. Execute phases in order (1 → 2 → 3 → 4)
4. After each phase: commit, run QA, proceed to next
5. After Phase 4: final validation and documentation update

---

## Constraints Achieved

After refactoring, the frontend will fully comply with:

```
✓ Frontend must be purely presentational (no logic)
✓ No JavaScript/scripting logic in components
✓ All styling in global CSS (no inline styles)
✓ All class names from constants (no hardcoded attributes)
✓ Business logic in utilities/hooks (not components)
```

---

## Output Guarantee

**Visual/Functional Output:** 100% identical to current state  
**Styling:** Pixel-perfect match (verified via DevTools before/after)  
**Behavior:** Same cart math, same API calls, same data flow  
**User Experience:** Completely unchanged  

---

**Status:** Ready for Phase 1  
**Estimated Completion:** 10–14 hours of development  
**Risk Level:** Low (non-breaking, internal refactor)  
**Approval:** Awaiting review and go-ahead for Phase 1
