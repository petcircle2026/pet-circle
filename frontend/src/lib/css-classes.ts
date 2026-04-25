/* ── Layout Classes ─────────────────────────────────────────────── */
export const LAYOUT = {
  app: "app",
  card: "card",
  vh: "vh",
  banner: "banner",
  profile: "profile",
  avatar: "avatar",
  navCard: "nav-card",
  bell: "bell",
} as const;

/* ── Button Classes ─────────────────────────────────────────────── */
export const BUTTONS = {
  order: "order-btn",
  close: "close-btn",
  back: "back-btn",
  edit: "edit-btn",
  save: "save-btn",
  nav: "nav-arr",
  sm: "btn-sm",
  icon: "btn-icon",
  primary: "btn-or",
  outline: "btn-out",
} as const;

/* ── Status Tag Classes ─────────────────────────────────────────── */
export const STATUS_TAGS = {
  green: "s-tag s-tag-g",
  yellow: "s-tag s-tag-y",
  red: "s-tag s-tag-r",
  recommendation: "s-tag s-tag-rec",
} as const;

/* ── Trait Pill Classes ────────────────────────────────────────── */
export const TRAIT_PILLS = {
  green: "trait-pill trait-g",
  red: "trait-pill trait-r",
  yellow: "trait-pill trait-y",
  neutral: "trait-pill trait-p",
} as const;

/* ── Flexbox Utilities ────────────────────────────────────────── */
export const FLEX = {
  center: "flex-center",
  between: "flex-between",
  start: "flex-start",
  col: "flex-col",
  gapXs: "flex-gap-xs",
  gapSm: "flex-gap-sm",
  gapMd: "flex-gap-md",
  gapLg: "flex-gap-lg",
} as const;

/* ── Care Plan Classes ─────────────────────────────────────────── */
export const CARE_PLAN = {
  section: "care-sec",
  header: "care-hdr",
  item: "care-item",
  name: "care-name",
  meta: "care-meta",
} as const;

/* ── Form Classes ──────────────────────────────────────────────── */
export const FORM = {
  field: "field",
  label: "f-lbl",
  input: "f-input",
} as const;

/* ── Admin Classes (Tailwind) ──────────────────────────────────── */
export const ADMIN = {
  container: "min-h-screen bg-gray-50",
  header: "border-b bg-white px-6 py-4 shadow-sm",
  headerFlex: "mx-auto flex max-w-7xl items-center justify-between",
  title: "text-lg font-bold",
  nav: "border-b bg-white",
  navContainer: "mx-auto flex max-w-7xl gap-1 overflow-x-auto px-6",
  main: "mx-auto max-w-7xl p-6",
  card: "overflow-hidden rounded-lg border bg-white shadow-sm",
  button: "rounded border px-3 py-1 text-sm text-gray-600 hover:bg-gray-100",
  badge: "rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600",
  badgeRed: "rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700",
  table: "w-full table-fixed text-left text-xs sm:text-sm",
  tableHead: "border-t bg-gray-50 text-xs uppercase text-gray-500",
  tableBody: "divide-y",
  tableRow: "hover:bg-gray-50",
  tableCell: "px-2 py-2 sm:px-4",
  loadingText: "py-8 text-center text-gray-500",
  errorText: "py-8 text-center text-red-600",
  emptyText: "py-8 text-center text-gray-400",
} as const;
