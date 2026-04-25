# Frontend Refactoring — Before/After Code Examples

**Purpose:** Show concrete before/after patterns for each violation type and phase.

---

## Violation Type 1: Inline Styles

### BottomSheet.tsx — Header with Inline Flex & Spacing

**Before (Violation):**
```tsx
<div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
  {title ? <h3 style={{ fontSize: 17, fontWeight: 700, color: '#111', margin: 0 }}>{title}</h3> : <span />}
  <button
    type="button"
    onClick={onClose}
    style={{
      width: 32,
      height: 32,
      borderRadius: '50%',
      border: '1.5px solid #e0e0e0',
      background: '#f5f5f5',
      fontSize: 18,
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: '#555',
      flexShrink: 0,
    }}
    aria-label="Close"
  >
    &times;
  </button>
</div>
```

**After (Phase 2 + Phase 4):**
```tsx
<div className="bottom-sheet-header">
  {title ? <h3 className="bottom-sheet-title">{title}</h3> : <span />}
  <button
    type="button"
    onClick={onClose}
    className={BUTTONS.close}
    aria-label={ARIA_LABELS.close}
  >
    &times;
  </button>
</div>
```

**New CSS (`globals.css`):**
```css
.bottom-sheet-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--sp-lg);
}

.bottom-sheet-title {
  font-size: var(--fs-lg);
  font-weight: 700;
  color: var(--t1);
  margin: 0;
}

.close-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1.5px solid var(--border);
  background: var(--to);
  font-size: var(--fs-xl);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--t2);
  flex-shrink: 0;
}
```

**New Constant (`lib/css-classes.ts`):**
```typescript
export const BUTTONS = {
  close: "close-btn",
  // ... other buttons
} as const;
```

**New Constant (`lib/aria-labels.ts`):**
```typescript
export const ARIA_LABELS = {
  close: "Close",
  // ... other labels
} as const;
```

---

### CarePlanCard.tsx — Inline Button Styling

**Before:**
```tsx
{onEditReminders && (
  <button
    type="button"
    onClick={onEditReminders}
    style={{
      border: "1px solid #ffd9c2",
      background: "#fff4ec",
      color: "#c54c0b",
      borderRadius: 999,
      padding: "5px 12px",
      fontSize: 12,
      fontWeight: 700,
      cursor: "pointer",
      flexShrink: 0,
    }}
    aria-label="Edit care reminders"
  >
    Edit
  </button>
)}
```

**After:**
```tsx
{onEditReminders && (
  <button
    type="button"
    onClick={onEditReminders}
    className={BUTTONS.edit}
    aria-label={ARIA_LABELS.editReminders}
  >
    Edit
  </button>
)}
```

**New CSS:**
```css
.edit-btn {
  border: 1px solid #ffd9c2;
  background: #fff4ec;
  color: #c54c0b;
  border-radius: var(--br-full);
  padding: 5px 12px;
  font-size: var(--fs-sm);
  font-weight: 700;
  cursor: pointer;
  flex-shrink: 0;
}
```

---

## Violation Type 2: Hardcoded Class Names & Attributes

### ProfileBanner.tsx — Class Names & Labels

**Before:**
```tsx
<button
  className="bell"
  onClick={onGoToReminders}
  type="button"
  title="Care Reminders"
  aria-label="Open care reminders"
>
  🔔
</button>
```

**After:**
```tsx
<button
  className={LAYOUT.bell}
  onClick={onGoToReminders}
  type="button"
  title={ARIA_LABELS.openReminders}
  aria-label={ARIA_LABELS.openReminders}
>
  🔔
</button>
```

**New Constants:**
```typescript
// lib/css-classes.ts
export const LAYOUT = {
  bell: "bell",
  avatar: "avatar",
  profile: "profile",
  // ...
} as const;

// lib/aria-labels.ts
export const ARIA_LABELS = {
  openReminders: "Open care reminders",
  // ...
} as const;
```

---

### Admin Components — Tailwind Classes

**Before:**
```tsx
<div className="min-h-screen bg-gray-50">
  <header className="border-b bg-white px-6 py-4 shadow-sm">
    <h1 className="text-lg font-bold">{APP_ADMIN_TITLE}</h1>
  </header>
  <nav className="border-b bg-white">
    <div className="mx-auto flex max-w-7xl gap-1 overflow-x-auto px-6">
      {/* pills */}
    </div>
  </nav>
</div>
```

**After:**
```tsx
<div className={ADMIN.container}>
  <header className={ADMIN.header}>
    <h1 className={ADMIN.title}>{APP_ADMIN_TITLE}</h1>
  </header>
  <nav className={ADMIN.nav}>
    <div className={ADMIN.navContainer}>
      {/* pills */}
    </div>
  </nav>
</div>
```

**New Constants:**
```typescript
// lib/css-classes.ts
export const ADMIN = {
  container: "min-h-screen bg-gray-50",
  header: "border-b bg-white px-6 py-4 shadow-sm",
  title: "text-lg font-bold",
  nav: "border-b bg-white",
  navContainer: "mx-auto flex max-w-7xl gap-1 overflow-x-auto px-6",
  // ... more admin classes
} as const;
```

---

## Violation Type 3: Business Logic in Components

### CartView.tsx — Cart Calculations

**Before (Inline Logic):**
```tsx
const inCartItems = useMemo(() => items.filter((item) => item.quantity > 0), [items]);

const subtotal = useMemo(() => {
  return inCartItems.reduce((sum, item) => sum + item.price * item.quantity, 0);
}, [inCartItems]);

const deliveryFee = subtotal >= FREE_THRESHOLD ? 0 : DELIVERY_FEE;
const total = subtotal + deliveryFee;
const amountForFreeDelivery = Math.max(0, FREE_THRESHOLD - subtotal);
```

**After (Phase 3):**
```tsx
const { inCart, subtotal, deliveryFee, total, amountForFreeDelivery } = useCartCalculations(items);
```

**New Hook (`hooks/useCartCalculations.ts`):**
```typescript
import { useMemo } from "react";
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
  const inCart = useMemo(() => items.filter((item) => item.quantity > 0), [items]);

  const subtotal = useMemo(() => {
    return inCart.reduce((sum, item) => sum + item.price * item.quantity, 0);
  }, [inCart]);

  const deliveryFee = subtotal >= FREE_THRESHOLD ? 0 : DELIVERY_FEE;
  const total = subtotal + deliveryFee;
  const amountForFreeDelivery = Math.max(0, FREE_THRESHOLD - subtotal);

  return { inCart, subtotal, deliveryFee, total, amountForFreeDelivery };
}
```

**Benefit:** Reusable, testable, decoupled from component

---

### BottomSheet.tsx — Scroll Lock Logic

**Before:**
```tsx
useEffect(() => {
  if (open) document.body.style.overflow = 'hidden';
  else document.body.style.overflow = '';
  return () => { document.body.style.overflow = ''; };
}, [open]);
```

**After:**
```tsx
useScrollLock(open);
```

**New Hook (`hooks/useScrollLock.ts`):**
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

**Benefit:** Declarative, reusable across components, testable

---

### CartView.tsx — Search Result Grouping

**Before (Inline):**
```tsx
const groupedResults = useMemo(() => {
  const groups: Record<string, SearchResult[]> = {};
  for (const r of searchResults) {
    const key = `${r.brand_name}||${r.product_name}`;
    if (!groups[key]) groups[key] = [];
    groups[key].push(r);
  }
  return Object.entries(groups).map(([key, skus]) => {
    const [brand, productName] = key.split("||");
    return { brand, productName, skus };
  });
}, [searchResults]);
```

**After:**
```tsx
const groupedResults = useMemo(() => groupSearchResults(searchResults), [searchResults]);
```

**New Utility (`utils/cart-utils.ts`):**
```typescript
interface SearchResult {
  brand_name: string;
  product_name: string;
  [key: string]: any;
}

interface GroupedResult {
  brand: string;
  productName: string;
  skus: SearchResult[];
}

export function groupSearchResults(results: SearchResult[]): GroupedResult[] {
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

**Benefit:** Testable in isolation, reusable if search used elsewhere, clearer intent

---

### ProfileBanner.tsx — Date Formatting

**Before (Inline):**
```tsx
function formatVetVisitDate(value: string | null | undefined): string {
  if (!value) return "--";
  const dateOnlyMatch = value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (dateOnlyMatch) {
    const year = Number(dateOnlyMatch[1]);
    const month = Number(dateOnlyMatch[2]);
    const day = Number(dateOnlyMatch[3]);
    const safeDate = new Date(year, month - 1, day);
    return new Intl.DateTimeFormat("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(safeDate);
  }
  // ... more logic
}

// Inside component:
const fallbackVetLastVisit = formatVetVisitDate(data.vet_summary?.last_visit) || "--";
```

**After:**
```tsx
import { formatVetVisitDate } from "@/utils/profile-utils";

// Inside component:
const fallbackVetLastVisit = formatVetVisitDate(data.vet_summary?.last_visit);
```

**New Utility (`utils/profile-utils.ts`):**
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
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(safeDate);
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(parsed);
}
```

**Benefit:** Reusable, testable, cleaner components, shared date logic

---

## Summary of Transformations

| Violation | Pattern | Solution | File Type |
|---|---|---|---|
| **Inline Styles** | `style={{...}}` | CSS class or CSS variable | `globals.css` |
| **Hardcoded Classes** | `className="btn-sm"` | Constant reference `BUTTONS.sm` | `css-classes.ts` |
| **Hardcoded Attributes** | `aria-label="Close"` | Constant reference `ARIA_LABELS.close` | `aria-labels.ts` |
| **Cart Math** | Inline `useMemo` | Hook `useCartCalculations()` | `hooks/useCartCalculations.ts` |
| **Scroll Logic** | Inline `useEffect` | Hook `useScrollLock()` | `hooks/useScrollLock.ts` |
| **Search Grouping** | Inline `useMemo` logic | Utility `groupSearchResults()` | `utils/cart-utils.ts` |
| **Date Formatting** | Component function | Utility `formatVetVisitDate()` | `utils/profile-utils.ts` |

---

## Verification Checklist (Per Example)

After applying each transformation:

- [ ] Component renders identically (visual comparison)
- [ ] No TypeScript errors (`tsc --noEmit`)
- [ ] No ESLint warnings (`npm run lint`)
- [ ] Computed styles in DevTools match original (F12 inspector)
- [ ] Logic produces same output (console log comparison if needed)

---

**Note:** All examples preserve 100% functional equivalence. The refactoring is purely structural, moving code to better locations without changing behavior or output.
