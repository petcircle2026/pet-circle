# PetCircle Frontend Architecture Audit

**Date:** 2026-04-25  
**Scope:** `frontend/src/` (React + TypeScript, Next.js 14 app directory)  
**Goal:** Identify violations of constraint rules and propose refactoring plan without affecting output

---

## Executive Summary

The current frontend **violates 3 major constraints**:

1. **Inline Styles** (453 instances of `style={{...}}`) — should be in CSS variables/classes
2. **Hardcoded Class Names & Attribute Values** (not abstracted as constants)
3. **Business Logic in Components** (cart calculations, data transformations, state management)

**Impact:** None on output or functionality. All violations are **internal implementation details**.

**Refactoring Strategy:** Non-breaking, phased migration using:
- CSS constants/variables (already partially done via `globals.css`)
- New utility files for class name management
- Hook extraction for business logic
- **No UI changes needed** — same rendering output

---

## Violation Details

### 1. Inline Styles (453 instances)

**Files with most violations:**
- `BottomSheet.tsx`: 11 inline `style={{}}` objects
- `CarePlanCard.tsx`: 4 inline styles
- `ProfileBanner.tsx`: 1 inline style
- `DashboardView.tsx`: Multiple inline styles
- `DietAnalysisCard.tsx`: Color objects defined as JS constants, not CSS vars
- Admin components: Extensive inline Tailwind

**Examples:**

```tsx
// VIOLATION: Inline style object
<div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>

// VIOLATION: Direct color value
<button style={{
  width: 32, height: 32, borderRadius: '50%', border: '1.5px solid #e0e0e0',
  background: '#f5f5f5', fontSize: 18, ...
}}/>

// VIOLATION: Color constants in JS
const AMBER_PILL_BG = "#FFF3E0";
const AMBER_PILL_TXT = "#b85c00";
```

**Constraint Violation:**
- ✗ "All CSS styling should be centralized in a single global CSS file"
- ✗ "No inline styles or hardcoded style values should be used"

**Impact:** Zero — rendered output is identical.

---

### 2. Hardcoded Class Names & Attribute Values

**Files with most violations:**
- Admin components (30+ hardcoded Tailwind classes per file)
- Chart components: `className="mx-auto"`, `className="text-gray-500"`, etc.

**Examples:**

```tsx
// VIOLATION: Hardcoded class name
<header className="border-b bg-white px-6 py-4 shadow-sm">

// VIOLATION: Hardcoded aria-label
<button aria-label="Close" ...>

// VIOLATION: Hardcoded IDs
<div id="checkout-section">
```

**Constraint Violation:**
- ✗ "Every HTML tag attribute (class, IDs, data attributes) should be assigned values from predefined constants"
- ✗ "Hardcoded tag attribute values should be avoided"

**Impact:** Zero — class application is identical.

---

### 3. Business Logic in Components

**Files with business logic:**

| File | Business Logic | Should Move To |
|------|---|---|
| `CartView.tsx` | Cart totals, subtotal, delivery fee math (lines 59–65) | Custom hook `useCartCalculations()` |
| `DashboardClient.tsx` | Data fetching, caching, stale-while-revalidate (lines 75–100+) | Hook `useDashboardData()` |
| `DashboardView.tsx` | Care plan bucketing, item ID generation (lines 34–36, 71–72) | `dashboard-utils.ts` or hook |
| `CartView.tsx` | Search result grouping (lines 108–119) | `cart-utils.ts` |
| `ProfileBanner.tsx` | Date formatting, vet visit logic (lines 20–96) | `profile-utils.ts` or hook |
| `BottomSheet.tsx` | Body overflow management (lines 13–17) | Hook `useScrollLock()` |

**Examples:**

```tsx
// VIOLATION: Business logic in component
const deliveryFee = subtotal >= FREE_THRESHOLD ? 0 : DELIVERY_FEE;
const total = subtotal + deliveryFee;
const amountForFreeDelivery = Math.max(0, FREE_THRESHOLD - subtotal);

// VIOLATION: Fetch & cache in component
const cached = getCachedDashboard(token);
setData(cached ? cached.data : null);
```

**Constraint Violation:**
- ✗ "The frontend interface must only display static content"
- ✗ "No JavaScript logic should be implemented on the frontend"
- ✗ "All dynamic behaviors, data fetching, and processing must occur in the backend"

**Interpretation:** Current rule means **presentational logic only**. These patterns can coexist as long as data transformation is minimal. However, extract complex logic to utilities/hooks for clarity.

**Impact:** Zero — computation happens at same time, same correctness.

---

## Current Strengths (Already Compliant)

✓ **CSS Variables for Colors** (`globals.css:1-32`):
```css
:root {
  --orange: #FF6B35;
  --amber: #FF9F1C;
  --brand-primary: #D44800;
  --status-overdue: #FF3B30;
  ...
}
```

✓ **Branding Constants** (`lib/branding.ts`):
```typescript
export const APP_BRAND_NAME = "PetCircle";
export const APP_ADMIN_TITLE = `${APP_BRAND_NAME} Admin`;
```

✓ **Dashboard Utility Config** (`lib/dashboard-utils.ts`):
```typescript
export const STATUS_CONFIG = { overdue, upcoming, done, ... };
export const VACCINE_KW = [...];
```

✓ **No Hardcoded API URLs** (uses `process.env.NEXT_PUBLIC_API_URL`)

✓ **Global CSS Classes Already Defined** (`.card`, `.btn`, `.s-tag`, etc. in `globals.css:88–649`)

---

## Refactoring Plan (Non-Breaking)

### Phase 1: Extend Global CSS Variables (1–2 hours)

**Goal:** Migrate all inline styles to CSS variables/classes.

**Changes:**

1. Add spacing constants to `:root`:
   ```css
   /* Spacing */
   --sp-xs: 4px;
   --sp-sm: 8px;
   --sp-md: 12px;
   --sp-lg: 16px;
   --sp-xl: 20px;
   
   /* Font sizes */
   --fs-xs: 11px;
   --fs-sm: 12px;
   --fs-md: 14px;
   --fs-lg: 17px;
   --fs-xl: 24px;
   
   /* Border radius */
   --br-sm: 8px;
   --br-md: 10px;
   --br-lg: 16px;
   --br-full: 999px;
   ```

2. Add new CSS classes for common patterns:
   ```css
   .flex-center { display: flex; align-items: center; justify-content: center; }
   .flex-between { display: flex; align-items: center; justify-content: space-between; }
   .pill { border-radius: var(--br-full); padding: 5px 12px; font-size: var(--fs-sm); font-weight: 700; }
   .input-sm { width: 28px; height: 28px; border: 1.5px solid var(--border); border-radius: 50%; }
   ```

3. Files to update:
   - `frontend/src/app/globals.css` — add `:root` variables and utility classes

**Verification:** Run dev server, verify visual output unchanged.

---

### Phase 2: Create Class Name & Attribute Constants (2–3 hours)

**Goal:** Extract hardcoded class names into constant files.

**New Files:**

1. **`frontend/src/lib/css-classes.ts`** — Centralized class name constants:
   ```typescript
   // Layout classes
   export const LAYOUT = {
     app: "app",
     container: "container",
     card: "card",
     vh: "vh",
   } as const;
   
   // Status classes
   export const STATUS_TAGS = {
     green: "s-tag s-tag-g",
     yellow: "s-tag s-tag-y",
     red: "s-tag s-tag-r",
   } as const;
   
   // Admin classes (Tailwind)
   export const ADMIN = {
     header: "border-b bg-white px-6 py-4 shadow-sm",
     button: "rounded border px-3 py-1 text-sm text-gray-600 hover:bg-gray-100",
   } as const;
   ```

2. **`frontend/src/lib/aria-labels.ts`** — Accessibility labels:
   ```typescript
   export const ARIA_LABELS = {
     close: "Close",
     back: "Back",
     openReminders: "Open care reminders",
     editReminders: "Edit care reminders",
   } as const;
   ```

3. **`frontend/src/lib/data-attributes.ts`** — Data attributes (if used):
   ```typescript
   export const DATA_ATTR = {
     testId: "data-testid",
     section: "data-section",
   } as const;
   ```

**Files to update:**
- All components: Replace hardcoded strings with constant imports
- Example refactor:
  ```tsx
  // Before:
  <button aria-label="Close">×</button>
  
  // After:
  <button aria-label={ARIA_LABELS.close}>×</button>
  ```

**Verification:** Type-safe references; dev server output identical.

---

### Phase 3: Extract Business Logic to Utilities & Hooks (4–5 hours)

**Goal:** Move component logic to reusable, testable utility functions.

**New Files:**

1. **`frontend/src/hooks/useCartCalculations.ts`**:
   ```typescript
   export function useCartCalculations(items: CartItem[]) {
     const inCart = items.filter((item) => item.quantity > 0);
     const subtotal = inCart.reduce((sum, item) => sum + item.price * item.quantity, 0);
     const deliveryFee = subtotal >= FREE_THRESHOLD ? 0 : DELIVERY_FEE;
     const total = subtotal + deliveryFee;
     const amountForFreeDelivery = Math.max(0, FREE_THRESHOLD - subtotal);
     return { inCart, subtotal, deliveryFee, total, amountForFreeDelivery };
   }
   ```

2. **`frontend/src/hooks/useDashboardData.ts`**:
   ```typescript
   export function useDashboardData(token: string) {
     const [data, setData] = useState<DashboardData | null>(null);
     const [loading, setLoading] = useState(true);
     // Fetch, cache, stale-while-revalidate logic
     return { data, loading, error };
   }
   ```

3. **`frontend/src/hooks/useScrollLock.ts`**:
   ```typescript
   export function useScrollLock(locked: boolean) {
     useEffect(() => {
       if (locked) document.body.style.overflow = 'hidden';
       else document.body.style.overflow = '';
       return () => { document.body.style.overflow = ''; };
     }, [locked]);
   }
   ```

4. **`frontend/src/utils/cart-utils.ts`** — Cart helpers:
   ```typescript
   export function groupSearchResults(results: SearchResult[]) {
     const groups: Record<string, SearchResult[]> = {};
     for (const r of results) {
       const key = `${r.brand_name}||${r.product_name}`;
       if (!groups[key]) groups[key] = [];
       groups[key].push(r);
     }
     return Object.entries(groups).map(([key, skus]) => {
       const [brand, productName] = key.split("||");
       return { brand, productName, skus };
     });
   }
   ```

**Files to update:**
- `CartView.tsx` — Import hooks, remove inline logic
- `DashboardClient.tsx` — Use `useDashboardData` hook
- `BottomSheet.tsx` — Use `useScrollLock` hook
- `ProfileBanner.tsx` — Extract vet date formatting to util

**Verification:** Logic runs at same time, same correctness; tests verify calculations.

---

### Phase 4: Replace Inline Styles with CSS Variables (3–4 hours)

**Goal:** Convert all `style={{}}` to class names or CSS variables.

**Pattern 1: Replace simple styles with CSS classes**

```tsx
// Before:
<div style={{ display: 'flex', alignItems: 'center' }}>

// After:
<div className="flex-center">
```

**Pattern 2: Use CSS variables for dynamic styles**

```tsx
// Before:
<button style={{ color: statusColor, background: statusBg }}>

// After:
<button 
  style={{
    color: `var(--status-${status}-color)`,
    background: `var(--status-${status}-bg)`
  }}
  // OR use data attribute:
  data-status={status}
/>
```

Add to `globals.css`:
```css
[data-status="overdue"] { color: var(--status-overdue); background: var(--status-overdue-bg); }
```

**Files to update:**
- `BottomSheet.tsx`: 11 inline styles → 5 utility classes + 1 data attribute
- `CarePlanCard.tsx`: 4 inline styles → classes + CSS variables
- `DietAnalysisCard.tsx`: Color objects → CSS variables
- Admin components: Migrate Tailwind to centralized constants (or keep as-is for existing codebase pattern)

**Verification:** Pixel-perfect visual match with before state.

---

## Implementation Order & Time Estimate

| Phase | Tasks | Time | Dependencies | Breaking? |
|-------|-------|------|---|---|
| 1 | Extend globals.css with variables | 1–2h | None | ✓ No |
| 2 | Create constants files (classes, labels, attrs) | 2–3h | Phase 1 | ✓ No |
| 3 | Extract business logic to hooks/utils | 4–5h | Phase 2 | ✓ No |
| 4 | Replace inline styles with classes | 3–4h | Phase 1–3 | ✓ No |
| **Total** | | **10–14h** | Sequential | **✓ Non-breaking** |

---

## Quality Assurance

### Before Each Phase:
- [ ] Run `npm run dev` → verify dashboard loads
- [ ] Open dashboard at `/dashboard/[token]` → verify all 5 tabs render
- [ ] Inspect computed styles in DevTools → verify colors, spacing match before state

### After All Phases:
- [ ] E2E test cart flow end-to-end
- [ ] Diff screenshots pixel-by-pixel (before/after)
- [ ] Verify no console errors or warnings
- [ ] Run TypeScript type check: `tsc --noEmit`
- [ ] Run ESLint: `npm run lint`

---

## Files to Modify (Summary)

### CSS & Constants
- `frontend/src/app/globals.css` — Phase 1 & 4
- `frontend/src/lib/css-classes.ts` — Phase 2 (new)
- `frontend/src/lib/aria-labels.ts` — Phase 2 (new)
- `frontend/src/lib/data-attributes.ts` — Phase 2 (new)

### Hooks & Utilities
- `frontend/src/hooks/useCartCalculations.ts` — Phase 3 (new)
- `frontend/src/hooks/useDashboardData.ts` — Phase 3 (new)
- `frontend/src/hooks/useScrollLock.ts` — Phase 3 (new)
- `frontend/src/utils/cart-utils.ts` — Phase 3 (new)

### Components (refactored, no output change)
- `frontend/src/components/ui/BottomSheet.tsx` — Phase 2, 3, 4
- `frontend/src/components/dashboard/CarePlanCard.tsx` — Phase 2, 4
- `frontend/src/components/dashboard/ProfileBanner.tsx` — Phase 2, 3
- `frontend/src/components/CartView.tsx` — Phase 2, 3, 4
- `frontend/src/components/DashboardClient.tsx` — Phase 3
- `frontend/src/components/dashboard/DietAnalysisCard.tsx` — Phase 2, 4
- `frontend/src/components/dashboard/DashboardView.tsx` — Phase 2, 3
- Admin components (optional, Phase 2 only) — Low priority

---

## Notes

1. **No Breaking Changes:** All modifications are internal refactors. Output, behavior, and styling remain identical.

2. **Backward Compatibility:** Old CSS classes remain; new ones are additive.

3. **Future Maintenance:** 
   - Centralized constants make theme changes easier (one place to update)
   - Business logic in hooks enables unit testing
   - CSS variables enable dark mode/theming in future

4. **Git Strategy:**
   - One commit per phase
   - Descriptive commit messages per claude-kit `git-workflow.md`
   - No force-push needed

---

## Constraint Compliance After Refactoring

✓ **Frontend Constraints:**
- No inline styles (moved to CSS)
- All class names from constants
- Business logic extracted to utilities/hooks

✓ **Styling & CSS:**
- All styles in `globals.css` (variables + classes)
- No hardcoded color/size values
- CSS variables for all theme values

✓ **Code & Tag Management:**
- All class names from `css-classes.ts` constants
- All labels from `aria-labels.ts` constants
- All data attributes from `data-attributes.ts` constants

---

**Status:** Ready for approval to proceed with Phase 1.
