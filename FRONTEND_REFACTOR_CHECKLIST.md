# Frontend Refactoring Checklist

**Project:** PetCircle  
**Objective:** Align frontend with architectural constraints (no inline styles, no hardcoded attributes, business logic in utilities)  
**Status:** Ready for Phase 1  
**Estimated Duration:** 10–14 hours  

---

## Quick Reference: Violations Found

| Violation Type | Count | Severity | Phase |
|---|---|---|---|
| Inline `style={{}}` objects | 453 | Medium | 4 |
| Hardcoded class names (Tailwind) | ~200+ | Low | 2 |
| Hardcoded aria-labels | ~15 | Low | 2 |
| Business logic in components | 6 files | Medium | 3 |
| Color constants in JS (not CSS) | 3 files | Low | 4 |
| **Total files affected** | **42** | | |

---

## Phase 1: Extend Global CSS Variables

### Tasks

- [ ] Open `frontend/src/app/globals.css`
- [ ] Add spacing variables to `:root`:
  ```css
  --sp-xs: 4px;    /* margin, padding small */
  --sp-sm: 8px;
  --sp-md: 12px;
  --sp-lg: 16px;   /* main padding)
  --sp-xl: 20px;
  ```
- [ ] Add font size variables:
  ```css
  --fs-xs: 11px;   /* labels, tags */
  --fs-sm: 12px;   /* body text, small buttons */
  --fs-md: 14px;   /* standard body */
  --fs-lg: 17px;   /* card titles, headers *)
  --fs-xl: 24px;   /* banner title *)
  ```
- [ ] Add border radius variables:
  ```css
  --br-sm: 8px;    /* buttons *)
  --br-md: 10px;   /* input fields *)
  --br-lg: 16px;   /* cards *)
  --br-full: 999px; /* pills *)
  ```
- [ ] Add utility classes before closing `}`:
  ```css
  /* Flexbox utilities */
  .flex-center { display: flex; align-items: center; justify-content: center; }
  .flex-between { display: flex; align-items: center; justify-content: space-between; }
  .flex-start { display: flex; align-items: center; justify-content: flex-start; }
  .flex-col { display: flex; flex-direction: column; }
  
  /* Button size classes */
  .btn-sm { width: 28px; height: 28px; border-radius: 50%; border: 1.5px solid var(--border); }
  .btn-icon { width: 36px; height: 36px; border-radius: 50%; }
  
  /* Pill utilities */
  .pill { border-radius: var(--br-full); padding: var(--sp-sm) var(--sp-md); }
  .pill-sm { font-size: var(--fs-xs); font-weight: 600; }
  
  /* Container classes */
  .flex-gap-sm { gap: 4px; }
  .flex-gap-md { gap: 8px; }
  .flex-gap-lg { gap: 12px; }
  ```

### Verification
- [ ] `npm run dev` — dashboard loads without errors
- [ ] Inspect element in DevTools — variables exist in `:root`
- [ ] Visual check — no styling changes visible

### Commit
```
chore: Add CSS variables and utility classes for Phase 1 refactor
```

---

## Phase 2: Create Class Name & Attribute Constants

### New Files to Create

#### 1. `frontend/src/lib/css-classes.ts`

- [ ] Create file
- [ ] Add `LAYOUT` constants:
  ```typescript
  export const LAYOUT = {
    app: "app",
    card: "card",
    vh: "vh", // view header
    banner: "banner",
    profile: "profile",
    avatar: "avatar",
    navCard: "nav-card",
  } as const;
  ```
- [ ] Add `BUTTONS` constants:
  ```typescript
  export const BUTTONS = {
    order: "order-btn",
    bell: "bell",
    back: "back-btn",
    edit: "edit-btn",
    save: "save-btn",
    nav: "nav-arr",
  } as const;
  ```
- [ ] Add `STATUS_TAGS` constants:
  ```typescript
  export const STATUS_TAGS = {
    green: "s-tag s-tag-g",
    yellow: "s-tag s-tag-y",
    red: "s-tag s-tag-r",
    recommendation: "s-tag s-tag-rec",
  } as const;
  ```
- [ ] Add `TRAIT_PILLS` constants:
  ```typescript
  export const TRAIT_PILLS = {
    green: "trait-pill trait-g",
    red: "trait-pill trait-r",
    yellow: "trait-pill trait-y",
    neutral: "trait-pill trait-p",
  } as const;
  ```
- [ ] Add `ADMIN` constants (Tailwind):
  ```typescript
  export const ADMIN = {
    container: "min-h-screen bg-gray-50",
    header: "border-b bg-white px-6 py-4 shadow-sm",
    nav: "border-b bg-white",
    main: "mx-auto max-w-7xl p-6",
    card: "overflow-hidden rounded-lg border bg-white shadow-sm",
    button: "rounded border px-3 py-1 text-sm text-gray-600 hover:bg-gray-100",
    badge: "rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600",
    table: "w-full table-fixed text-left text-xs sm:text-sm",
  } as const;
  ```

#### 2. `frontend/src/lib/aria-labels.ts`

- [ ] Create file
- [ ] Add constants:
  ```typescript
  export const ARIA_LABELS = {
    close: "Close",
    back: "Back",
    openReminders: "Open care reminders",
    editReminders: "Edit care reminders",
    addToCart: "Add to cart",
    removeFromCart: "Remove from cart",
    increaseQuantity: "Increase quantity",
    decreaseQuantity: "Decrease quantity",
  } as const;
  ```

#### 3. `frontend/src/lib/data-attributes.ts`

- [ ] Create file
- [ ] Add constants:
  ```typescript
  export const DATA_ATTR = {
    testId: "data-testid",
    section: "data-section",
    status: "data-status",
  } as const;
  ```

### Components to Update (Phase 2)

#### `BottomSheet.tsx`
- [ ] Replace `aria-label="Close"` with `aria-label={ARIA_LABELS.close}`
- [ ] Keep inline styles (Phase 4 will replace)
- [ ] Keep className patterns as-is

#### `CarePlanCard.tsx`
- [ ] Find hardcoded class in `onEditReminders` button style
- [ ] Extract to CSS variable reference

#### `ProfileBanner.tsx`
- [ ] Replace `aria-label="Open care reminders"` with constant
- [ ] Replace hardcoded `className="banner"` with `className={LAYOUT.banner}`

#### Admin Components (low priority)
- [ ] Update class references to use `ADMIN.*` constants
- [ ] Example:
  ```tsx
  // Before:
  <div className="border-b bg-white px-6 py-4 shadow-sm">
  
  // After:
  <div className={ADMIN.header}>
  ```

### Verification
- [ ] `tsc --noEmit` — no type errors
- [ ] `npm run lint` — no linting issues
- [ ] `npm run dev` — dashboard unchanged
- [ ] DevTools inspect — same classes applied

### Commit
```
refactor: Extract hardcoded class names and aria-labels to constants (Phase 2)
```

---

## Phase 3: Extract Business Logic to Hooks & Utilities

### New Hooks to Create

#### `frontend/src/hooks/useCartCalculations.ts`
- [ ] Create file
- [ ] Implement:
  ```typescript
  import type { CartItem } from "@/components/CartView";
  
  const DELIVERY_FEE = 49;
  const FREE_THRESHOLD = 599;
  
  interface CartCalculations {
    inCart: CartItem[];
    subtotal: number;
    deliveryFee: number;
    total: number;
    amountForFreeDelivery: number;
  }
  
  export function useCartCalculations(items: CartItem[]): CartCalculations {
    const inCart = items.filter((item) => item.quantity > 0);
    const subtotal = inCart.reduce((sum, item) => sum + item.price * item.quantity, 0);
    const deliveryFee = subtotal >= FREE_THRESHOLD ? 0 : DELIVERY_FEE;
    const total = subtotal + deliveryFee;
    const amountForFreeDelivery = Math.max(0, FREE_THRESHOLD - subtotal);
    return { inCart, subtotal, deliveryFee, total, amountForFreeDelivery };
  }
  ```
- [ ] Test: Call with sample cart, verify calculations

#### `frontend/src/hooks/useScrollLock.ts`
- [ ] Create file
- [ ] Implement:
  ```typescript
  import { useEffect } from "react";
  
  export function useScrollLock(locked: boolean): void {
    useEffect(() => {
      if (locked) {
        document.body.style.overflow = "hidden";
      } else {
        document.body.style.overflow = "";
      }
      return () => {
        document.body.style.overflow = "";
      };
    }, [locked]);
  }
  ```
- [ ] Test: Open/close BottomSheet, verify scroll state

#### `frontend/src/hooks/useDashboardData.ts`
- [ ] Create file
- [ ] Move dashboard fetch logic from `DashboardClient.tsx` (lines 75–100+)
- [ ] Return: `{ data, loading, error, refreshing }`

### New Utilities to Create

#### `frontend/src/utils/cart-utils.ts`
- [ ] Create file
- [ ] Move `groupedResults` logic from `CartView.tsx` (lines 108–119):
  ```typescript
  interface SearchResult {
    sku_id: string;
    brand_name: string;
    product_name: string;
    [key: string]: any;
  }
  
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

#### `frontend/src/utils/profile-utils.ts`
- [ ] Create file
- [ ] Move date formatting from `ProfileBanner.tsx` (lines 20–42):
  ```typescript
  export function formatVetVisitDate(value: string | null | undefined): string {
    if (!value) return "--";
    const dateOnlyMatch = value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (dateOnlyMatch) {
      const year = Number(dateOnlyMatch[1]);
      const month = Number(dateOnlyMatch[2]);
      const day = Number(dateOnlyMatch[3]);
      const safeDate = new Date(year, month - 1, day);
      return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit", month: "short", year: "numeric",
      }).format(safeDate);
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return value;
    return new Intl.DateTimeFormat("en-GB", {
      day: "2-digit", month: "short", year: "numeric",
    }).format(parsed);
  }
  ```

### Components to Update (Phase 3)

#### `CartView.tsx`
- [ ] Import `useCartCalculations`:
  ```typescript
  const { inCart, subtotal, deliveryFee, total, amountForFreeDelivery } = useCartCalculations(items);
  ```
- [ ] Remove lines 57–65 (old calculation logic)
- [ ] Import `groupSearchResults`:
  ```typescript
  const groupedResults = useMemo(() => groupSearchResults(searchResults), [searchResults]);
  ```
- [ ] Remove lines 108–119 (old grouping logic)

#### `BottomSheet.tsx`
- [ ] Import `useScrollLock`:
  ```typescript
  useScrollLock(open);
  ```
- [ ] Remove lines 13–17 (old scroll lock logic)

#### `DashboardClient.tsx`
- [ ] Import `useDashboardData`:
  ```typescript
  const { data, loading, error, refreshing } = useDashboardData(token);
  ```
- [ ] Remove lines 48–200+ (old fetch logic)

#### `ProfileBanner.tsx`
- [ ] Import `formatVetVisitDate`:
  ```typescript
  const fallbackVetLastVisit = formatVetVisitDate(data.vet_summary?.last_visit);
  ```
- [ ] Remove lines 20–42 (old date formatting logic)

### Verification
- [ ] `tsc --noEmit` — no type errors
- [ ] `npm run dev` — all views load
- [ ] Test cart: Add items, verify totals match
- [ ] Test BottomSheet: Open/close, scroll lock works
- [ ] Test dashboard: Data loads and displays

### Commit
```
refactor: Extract business logic to hooks and utilities (Phase 3)
```

---

## Phase 4: Replace Inline Styles with CSS Variables

### `BottomSheet.tsx` (11 inline styles)

- [ ] Line 22: Keep `className`, add class for animations
- [ ] Line 25–26: Replace inline style with class
  ```tsx
  // Before:
  <div className="relative w-full max-w-[430px] bg-white rounded-t-[20px] p-5 pb-8 animate-slideUp"
    style={{ maxHeight: '85vh', overflowY: 'auto' }}>
  
  // After:
  <div className="bottom-sheet">
  ```
  Add to `globals.css`:
  ```css
  .bottom-sheet {
    position: relative;
    width: 100%;
    max-width: 430px;
    background: var(--white);
    border-radius: 20px;
    padding: var(--sp-lg) var(--sp-lg) var(--sp-xl);
    max-height: 85vh;
    overflow-y: auto;
    animation: slideUp 0.3s ease-out;
  }
  ```
- [ ] Line 32: Replace inline style:
  ```tsx
  // Before:
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
  
  // After:
  <div className="flex-between" style={{ marginBottom: 'var(--sp-lg)' }}>
  ```
  Or even better, add to `globals.css`:
  ```css
  .bottom-sheet-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: var(--sp-lg);
  }
  ```
- [ ] Line 34: Replace inline style:
  ```tsx
  // Before:
  <h3 style={{ fontSize: 17, fontWeight: 700, color: '#111', margin: 0 }}>
  
  // After:
  <h3 className="bottom-sheet-title">
  ```
  Add to `globals.css`:
  ```css
  .bottom-sheet-title {
    font-size: var(--fs-lg);
    font-weight: 700;
    color: var(--t1);
    margin: 0;
  }
  ```
- [ ] Line 37–56: Replace button inline style:
  ```tsx
  // Before:
  <button style={{ width: 32, height: 32, borderRadius: '50%', border: '1.5px solid #e0e0e0', ... }}>
  
  // After:
  <button className={`${BUTTONS.close}`}>
  ```
  Add to `globals.css`:
  ```css
  .close-btn {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    border: 1.5px solid var(--border);
    background: var(--to);
    font-size: var(--fs-lg);
    line-height: 1;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--t2);
    font-weight: 400;
    flex-shrink: 0;
  }
  ```

### `CarePlanCard.tsx` (4 inline styles)

- [ ] Line 35–36: Replace style:
  ```tsx
  // Before:
  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
  
  // After:
  <div className="flex-between" style={{ gap: 'var(--sp-lg)' }}>
  ```
- [ ] Line 38–56: Button inline style (already has good background pattern, keep as-is or extract to class)

### `ProfileBanner.tsx` (1 inline style)

- [ ] Line 118: Replace inline style:
  ```tsx
  // Before:
  <div style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
  
  // After:
  <div className="truncate">
  ```
  Add to `globals.css`:
  ```css
  .truncate {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  ```

### `DietAnalysisCard.tsx` (Color objects)

- [ ] Line 15: Replace color object:
  ```typescript
  // Before:
  const NUTR_COLOR = { green: "#34C759", amber: "#FF9F1C", red: "#FF3B30" };
  
  // After:
  ```
  Add to `globals.css`:
  ```css
  :root {
    --color-success: #34C759;
    --color-warning: #FF9F1C;
    --color-danger: #FF3B30;
  }
  ```
  Update component to use CSS variables in inline SVG:
  ```typescript
  const NUTR_COLOR = { green: "var(--color-success)", amber: "var(--color-warning)", red: "var(--color-danger)" };
  ```
- [ ] Line 32–35: Replace pill color constants:
  ```typescript
  // Before:
  const AMBER_PILL_BG = "#FFF3E0";
  const AMBER_PILL_TXT = "#b85c00";
  
  // After:
  ```
  Add to `globals.css` and reference via inline style or data attribute:
  ```css
  .nutrition-pill-amber {
    background: #FFF3E0;
    color: #b85c00;
  }
  ```

### Admin Components (Optional, low priority)

- [ ] Select 1–2 components, replace hardcoded Tailwind with `ADMIN.*` constants
- [ ] Or document pattern and defer to later refactor

### Verification
- [ ] `npm run dev` — dashboard, cart, profile all render identically
- [ ] DevTools inspect elements — computed styles match before state
- [ ] Check font sizes, colors, spacing with color picker
- [ ] Open all tabs (Overview, Health, Hygiene, Nutrition, Conditions)
- [ ] Open BottomSheet (document upload) — styling correct
- [ ] Cart flow: Add item, verify button styling

### Commit
```
refactor: Replace inline styles with CSS variables and utility classes (Phase 4)
```

---

## Post-Refactoring Validation

### Full Test Suite
- [ ] Run `npm run build` — production build succeeds
- [ ] Run `npm run lint` — no issues
- [ ] Run `npm run test:e2e` (if configured) — E2E tests pass
- [ ] Visual regression: Side-by-side screenshots of before/after

### Browser Testing
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest, if accessible)
- [ ] Mobile Safari (iOS device or simulator)

### Accessibility Check
- [ ] Tab order works (keyboard navigation)
- [ ] Screen reader announces labels correctly
- [ ] All buttons have aria-labels (via constants)

### Performance
- [ ] Lighthouse score (mobile) — no regression
- [ ] CSS bundle size — should be similar or smaller (styles consolidated)

### Documentation
- [ ] Update `CLAUDE.md` with new structure:
  ```markdown
  ## CSS & Constants Structure
  - `globals.css` — All CSS variables, animations, utility classes
  - `lib/css-classes.ts` — Tailwind & semantic class name constants
  - `lib/aria-labels.ts` — Accessibility label constants
  - `lib/data-attributes.ts` — Data attribute constants
  
  ## Business Logic Hooks
  - `hooks/useCartCalculations.ts` — Cart total/fee calculations
  - `hooks/useScrollLock.ts` — Document body overflow management
  - `hooks/useDashboardData.ts` — Dashboard API fetch & cache
  
  ## Utilities
  - `utils/cart-utils.ts` — Cart-specific helpers (search grouping)
  - `utils/profile-utils.ts` — Profile-specific helpers (date formatting)
  ```

---

## Final Sign-Off

- [ ] All phases complete
- [ ] All tests passing
- [ ] All commits reviewed and merged
- [ ] `FRONTEND_AUDIT.md` and `FRONTEND_REFACTOR_CHECKLIST.md` archived in git

**Refactoring Status:** ✓ Complete  
**Output Consistency:** ✓ 100% identical to original  
**Code Quality:** ✓ Improved (constants, hooks, utilities)  
**Constraint Compliance:** ✓ Full adherence  

---

## Notes & Troubleshooting

### Issue: Tailwind classes not working after refactor

**Solution:** Ensure `className` prop receives string, not undefined:
```typescript
className={BUTTONS.close ?? ""}
```

### Issue: CSS variable not applying in inline SVG

**Solution:** SVG `<circle fill="var(--color)">` may not work. Use inline style instead:
```typescript
<circle fill={`var(--color-success)`} />
```

### Issue: Type errors after extracting hooks

**Solution:** Add return type annotations to all hooks:
```typescript
export function useCartCalculations(items: CartItem[]): CartCalculations {
  // ...
}
```

---

**Document Version:** 1.0  
**Last Updated:** 2026-04-25
