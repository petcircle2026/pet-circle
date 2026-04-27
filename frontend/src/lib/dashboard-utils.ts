import type { PreventiveRecord, ReminderItem } from './api';

// ─── Status Config ───────────────────────────────────────────────
export const STATUS_CONFIG: Record<string, { color: string; bg: string; label: string }> = {
  overdue:  { color: '#FF3B30', bg: '#FFF0F0', label: 'Overdue' },
  upcoming: { color: '#FF9500', bg: '#FFF6ED', label: 'Due Soon' },
  done:     { color: '#34C759', bg: '#F0FFF4', label: 'Up to Date' },
  up_to_date: { color: '#34C759', bg: '#F0FFF4', label: 'Up to Date' },
  missing:  { color: '#8E8E93', bg: '#F2F2F7', label: 'No Record' },
  incomplete: { color: '#8E8E93', bg: '#F2F2F7', label: 'No Record' },
  managed:  { color: '#007AFF', bg: '#F0F6FF', label: 'Managed' },
  urgent:   { color: '#FF3B30', bg: '#FFF0F0', label: 'Refill Now' },
  ok:       { color: '#34C759', bg: '#F0FFF4', label: 'Adequate' },
  cancelled: { color: '#8E8E93', bg: '#F2F2F7', label: 'Cancelled' },
};

// ─── Keyword Arrays ──────────────────────────────────────────────
export const VACCINE_KW = [
  "vaccine",
  "rabies",
  "dhpp",
  "core vaccine",
  "feline core",
  "bordetella",
  "kennel cough",
  "nobivac",
  "coronavirus",
  "ccov",
  "leptospirosis",
  "canine influenza",
  "felv",
  "fiv",
  "puppy booster",
];
export const DEWORMING_KW = ["deworming", "deworm"];
export const FLEA_TICK_KW = ["tick", "flea"];
export const CHECKUP_KW = ["checkup", "annual", "wellness", "blood test", "preventive blood"];

// ─── Date Helpers ────────────────────────────────────────────────
export function formatDMY(date: Date): string {
  const d = String(date.getDate()).padStart(2, '0');
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const y = date.getFullYear();
  return `${d}/${m}/${y}`;
}

const MONTH_NAMES: Record<string, number> = {
  january: 1, february: 2, march: 3, april: 4, may: 5, june: 6,
  july: 7, august: 8, september: 9, october: 10, november: 11, december: 12,
  jan: 1, feb: 2, mar: 3, apr: 4, jun: 6, jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12,
};

export function parseDMY(str: string): Date | null {
  const s = str.trim();
  if (!s) return null;

  // DD/MM/YYYY or DD-MM-YYYY
  const slashDash = s.match(/^(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})$/);
  if (slashDash) {
    const [, dd, mm, yy] = slashDash.map(Number);
    if (dd >= 1 && dd <= 31 && mm >= 1 && mm <= 12) return new Date(yy, mm - 1, dd);
  }

  // "12 March 2024" or "12 Mar 2024"
  const named = s.match(/^(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})$/);
  if (named) {
    const d = Number(named[1]);
    const m = MONTH_NAMES[named[2].toLowerCase()];
    const y = Number(named[3]);
    if (d >= 1 && d <= 31 && m) return new Date(y, m - 1, d);
  }

  // ISO: YYYY-MM-DD
  const iso = s.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (iso) {
    const [, yy, mm, dd] = iso.map(Number);
    if (dd >= 1 && dd <= 31 && mm >= 1 && mm <= 12) return new Date(yy, mm - 1, dd);
  }

  return null;
}

export function isDateInputValid(str: string): boolean {
  return parseDMY(str) !== null;
}

export function formatApiDate(isoDate: string | null): string {
  if (!isoDate) return '—';
  const d = new Date(isoDate);
  if (isNaN(d.getTime())) return '—';
  return formatDMY(d);
}

export function diffDaysFromToday(dateStr: string | null): number | null {
  if (!dateStr) return null;
  const target = new Date(dateStr);
  if (isNaN(target.getTime())) {
    const parsed = parseDMY(dateStr);
    if (!parsed) return null;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    parsed.setHours(0, 0, 0, 0);
    return Math.round((parsed.getTime() - today.getTime()) / 86400000);
  }
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  target.setHours(0, 0, 0, 0);
  return Math.round((target.getTime() - today.getTime()) / 86400000);
}

export function ageInDaysFromDob(dob: string | null): number | null {
  if (!dob) return null;
  const birthDate = new Date(dob);
  if (Number.isNaN(birthDate.getTime())) return null;
  const now = new Date();
  const diffTime = now.getTime() - birthDate.getTime();
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
  return Math.max(diffDays, 0);
}

export function freqLabel(freq: number, unit: string): string {
  if (freq === 1 && unit === 'day') return 'Daily';
  if (freq === 1 && unit === 'week') return 'Weekly';
  if (freq === 1 && unit === 'month') return 'Monthly';
  if (freq === 1 && unit === 'year') return 'Yearly';
  return `Every ${freq} ${unit}s`;
}

export function ageFromDob(dob: string | null): string {
  if (!dob) return '—';
  const birth = new Date(dob);
  if (isNaN(birth.getTime())) return '—';
  const now = new Date();
  let years = now.getFullYear() - birth.getFullYear();
  let months = now.getMonth() - birth.getMonth();
  if (months < 0) { years--; months += 12; }
  if (years > 0) return `${years} yr${years > 1 ? 's' : ''}`;
  return `${months} month${months !== 1 ? 's' : ''}`;
}

// ─── Location Helpers ────────────────────────────────────────────

// ─── Pet Age Helpers ─────────────────────────────────────────────

/**
 * Filter preventives by eligibility.
 * IMPORTANT: The backend (preventive_logic.is_vaccine_eligible_for_age) computes the
 * 'eligible' flag based on pet age and vaccine type. Frontend only filters on display.
 *
 * This is DISPLAY LOGIC, not business logic. Do NOT recompute eligibility here.
 */
export function filterPreventivesByEligibility(records: PreventiveRecord[]): PreventiveRecord[] {
  return records.filter(r => r.eligible !== false);
}

