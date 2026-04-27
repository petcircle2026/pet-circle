"""
PetCircle Phase 1 - Central Constants

All magic numbers and system-wide limits are defined here.
No other file should hardcode these values.
Import from this module to ensure single source of truth.
"""

import os

# --- Application Branding ---
APP_BRAND_NAME: str = "PetCircle"
APP_BRAND_PAW_ICON: str = "\U0001f43e"
APP_API_TITLE: str = f"{APP_BRAND_NAME} API"
APP_RETURNING_HEADING: str = f"Welcome back to *{APP_BRAND_NAME}* {APP_BRAND_PAW_ICON}"

# --- User & Pet Limits ---
# Maximum number of pets a single user can register.
# Enforced at the service layer during onboarding.
MAX_PETS_PER_USER: int = 5

# --- Post-Onboarding Document Upload Window ---
# Duration in seconds for the guided upload window after onboarding completes.
# User is prompted to upload medical records during this window.
DOC_UPLOAD_WINDOW_SECONDS: int = 300  # 5 minutes

# --- File Upload Limits ---
# Maximum file size in megabytes for document uploads.
MAX_UPLOAD_MB: int = 10

# Maximum file size in bytes, derived from MAX_UPLOAD_MB.
MAX_UPLOAD_BYTES: int = MAX_UPLOAD_MB * 1024 * 1024

# Maximum number of file uploads allowed per pet per day.
# Prevents abuse and controls storage costs.
MAX_UPLOADS_PER_PET_PER_DAY: int = 1000

# Maximum number of pending (unprocessed) documents allowed per pet at a time.
# If a pet already has this many pending documents, new uploads are rejected
# until existing ones finish extraction. Prevents queue flooding.
MAX_PENDING_DOCS_PER_PET: int = 100

# Maximum number of documents a user can send in a single upload burst/session.
# Enforced over the in-memory batch window so each new burst resets the count.
# Internal cap only - do not surface this number in any user-facing message or LLM prompt.
MAX_DOCS_PER_SESSION: int = 300

# Maximum number of concurrent background extraction tasks system-wide.
# Sized to allow multiple pet batches to extract in parallel while
# staying within DB pool limits (pool_size=15, max_overflow=10).
# Each extraction holds a DB session for the GPT call duration (~5-15s).
MAX_CONCURRENT_EXTRACTIONS: int = 8

# Maximum number of concurrent document upload processing tasks system-wide.
# Limits initial DB + media-download work when a user sends many files at once
# (e.g. 15 documents). Without this, 15 tasks simultaneously hold DB connections
# and hit Supabase hard enough to trigger SSL termination on the pooler side.
# Peak load: 15 uploads + 8 extractions = 23 sessions - within pool ceiling of 25.
MAX_CONCURRENT_UPLOAD_PROCESSING: int = 15

# Maximum number of upload tasks allowed to queue (waiting on the semaphore)
# system-wide at any one time. Once this threshold is hit, new upload tasks are
# rejected immediately with a user-friendly retry message rather than being
# queued. This prevents event loop overload from hundreds of waiting coroutines
# during traffic spikes.
# Rationale: MAX_CONCURRENT_UPLOAD_PROCESSING (15) active + 30 queued = 45 max
# in-flight coroutines. Each waiting coroutine is ~2KB on the heap, so 45 costs
# ~90KB - negligible. Above this we're likely under a DoS pattern, not real use.
MAX_QUEUED_UPLOADS: int = 30

# Maximum number of concurrent background message processing tasks system-wide.
# This is the ENTRY-POINT semaphore - it gates every message type (text, button,
# image, document) before any DB session is opened. Inner semaphores
# (MAX_CONCURRENT_UPLOAD_PROCESSING, MAX_CONCURRENT_EXTRACTIONS) then apply
# additional per-stage limits within this outer bound.
# Sized at 30 so all 100 concurrent users can be active: 30 processing + 70 queued
# = 100 total without any rejections. DB pool (40) is not fully consumed by
# handlers alone - they hold sessions briefly and release them (not the full
# handler lifetime), so 30 concurrent handlers fit within 40 pool connections.
MAX_CONCURRENT_MESSAGE_PROCESSING: int = 30

# Maximum number of messages allowed to queue waiting for the entry-point
# semaphore. Above this threshold new tasks are rejected immediately rather
# than queued, preventing event loop overload during traffic spikes.
# 30 active + 70 queued = 100 max coroutines - covers all 100 concurrent users.
MAX_QUEUED_MESSAGES: int = 70

# Allowed MIME types for uploaded documents.
# Only images (JPEG, PNG) and PDF are accepted.
ALLOWED_MIME_TYPES: set[str] = {
    "image/jpeg",
    "image/png",
    "application/pdf",
}

# --- Timezone ---
# All date/time operations use Asia/Kolkata (IST).
# This is a system-wide constant - never use UTC or other zones.
SYSTEM_TIMEZONE: str = "Asia/Kolkata"

# --- Care Plan Status Windows ---
# Due-soon window used by dashboard care-plan status semantics.
CARE_PLAN_DUE_SOON_DAYS: int = 7

# --- Conflict Resolution ---
# Number of days before an unresolved conflict auto-resolves.
# After expiry, the system keeps the existing record (KEEP_EXISTING).
CONFLICT_EXPIRY_DAYS: int = 5

# --- Reminder Button Payload IDs ---
# These are the exact payload strings sent by WhatsApp interactive buttons.
# Never hardcode these strings elsewhere - always reference these constants.
REMINDER_DONE: str = "REMINDER_DONE"            # "Done - Log It" (Due stage)
REMINDER_ALREADY_DONE: str = "REMINDER_ALREADY_DONE"  # "Already Done" (T-7 stage)
REMINDER_SNOOZE_7: str = "REMINDER_SNOOZE_7"    # "Remind Me Later" (T-7 / Due stage)
REMINDER_ORDER_NOW: str = "REMINDER_ORDER_NOW"  # "Order Now" (Due stage) -> agentic_order
REMINDER_STILL_PENDING: str = "REMINDER_STILL_PENDING"  # "Still Pending" (D+3 / Overdue)
REMINDER_SCHEDULE: str = "REMINDER_SCHEDULE"    # "Schedule For ()" -> awaiting_reschedule_date
REMINDER_RESCHEDULE: str = "REMINDER_RESCHEDULE"
REMINDER_CANCEL: str = "REMINDER_CANCEL"

# Set of all valid reminder payload IDs for routing in message_router.
REMINDER_PAYLOADS: frozenset[str] = frozenset({
    REMINDER_DONE, REMINDER_ALREADY_DONE, REMINDER_SNOOZE_7,
    REMINDER_ORDER_NOW, REMINDER_STILL_PENDING,
    REMINDER_SCHEDULE, REMINDER_RESCHEDULE, REMINDER_CANCEL,
})

# Number of days to push next_due_date forward when user snoozes a reminder.
# Per-category constants allow future independent tuning.
# All currently set to 7 days - change individual values to configure.
SNOOZE_DAYS_VACCINE: int = 7
SNOOZE_DAYS_DEWORMING: int = 7
SNOOZE_DAYS_FLEA: int = 7
SNOOZE_DAYS_FOOD: int = 7
SNOOZE_DAYS_SUPPLEMENT: int = 7
SNOOZE_DAYS_MEDICINE: int = 7
SNOOZE_DAYS_VET_FOLLOWUP: int = 7
SNOOZE_DAYS_HYGIENE: int = 7

# --- Reminder Stage Constants ---
# 4-stage lifecycle per preventive record cycle.
STAGE_T7: str = "t7"               # 7 days before due date
STAGE_DUE: str = "due"             # on due date
STAGE_D3: str = "d3"               # 3 days after due date
STAGE_OVERDUE: str = "overdue_insight"  # D+7+, monthly repeat

# Ordered stages for precedence: if multiple are eligible on same day,
# prefer higher-priority stage (lower index = higher priority).
STAGE_PRIORITY_ORDER: list[str] = [STAGE_DUE, STAGE_D3, STAGE_OVERDUE, STAGE_T7]

# Number of ignored reminders before dropping to monthly-only fallback.
REMINDER_IGNORE_THRESHOLD: int = 3

# Days between monthly overdue_insight repeats once monthly_fallback is True.
REMINDER_MONTHLY_INTERVAL_DAYS: int = 30

# Minimum days between any two sent reminders for the same pet.
REMINDER_MIN_GAP_DAYS: int = 3

# --- Reminder Send Times (IST) ---
# Used by reminder_templates.py as default send times per stage.
# Can be overridden at runtime via the reminder_config DB table (migration 024).
REMINDER_SEND_TIME_T7: tuple[int, int] = (9, 0)       # 09:00 IST
REMINDER_SEND_TIME_DUE: tuple[int, int] = (10, 0)     # 10:00 IST
REMINDER_SEND_TIME_D3: tuple[int, int] = (9, 0)       # 09:00 IST
REMINDER_SEND_TIME_OVERDUE: tuple[int, int] = (9, 0)  # 09:00 IST
REMINDER_SEND_TIME_HYGIENE: tuple[int, int] = (10, 0) # 10:00 IST

# --- Reminder Guard Rails ---
# These mirror the DB-configurable reminder_config table values.
# reminder_config_loader uses these as fallbacks when the DB row is absent.
REMINDER_MAX_PER_PET_PER_DAY: int = 1
REMINDER_MIN_DAYS_SAME_ITEM: int = 3

# --- Conflict Button Payload IDs ---
CONFLICT_USE_NEW: str = "CONFLICT_USE_NEW"
CONFLICT_KEEP_EXISTING: str = "CONFLICT_KEEP_EXISTING"

# --- Rate Limiting ---
# Maximum WhatsApp messages per phone number within the rolling window.
MAX_MESSAGES_PER_MINUTE: int = 20

# Rolling window duration in seconds for rate limiting.
RATE_LIMIT_WINDOW_SECONDS: int = 60

# =============================================================================
# AI MODEL SWITCH - change only AI_PROVIDER to swap provider/tier everywhere.
# Valid values: "claude" | "openai"
# =============================================================================
AI_PROVIDER: str = os.getenv("AI_PROVIDER", "claude")

# --- Claude model IDs (Anthropic) ---
# Override via CLAUDE_EXTRACTION_MODEL / CLAUDE_QUERY_MODEL env vars to swap
# model versions (e.g. on deprecation) without a code deploy.
_CLAUDE_EXTRACTION_MODEL: str = os.getenv("CLAUDE_EXTRACTION_MODEL", "claude-opus-4-6")
_CLAUDE_QUERY_MODEL: str = os.getenv("CLAUDE_QUERY_MODEL", "claude-sonnet-4-6")

# --- OpenAI model IDs ---
# Override via OPENAI_EXTRACTION_MODEL / OPENAI_QUERY_MODEL env vars.
_OPENAI_EXTRACTION_MODEL: str = os.getenv("OPENAI_EXTRACTION_MODEL", "gpt-4.1")
_OPENAI_QUERY_MODEL: str = os.getenv("OPENAI_QUERY_MODEL", "gpt-4.1")

# --- Active models - resolved from AI_PROVIDER (do not edit below this line) ---
AI_EXTRACTION_MODEL: str = (
    _CLAUDE_EXTRACTION_MODEL if AI_PROVIDER == "claude" else _OPENAI_EXTRACTION_MODEL
)
AI_QUERY_MODEL: str = (
    _CLAUDE_QUERY_MODEL if AI_PROVIDER == "claude" else _OPENAI_QUERY_MODEL
)

# Aliases for existing imports - these resolve to the models above based on AI_PROVIDER
OPENAI_EXTRACTION_MODEL: str = AI_EXTRACTION_MODEL
OPENAI_QUERY_MODEL: str = AI_QUERY_MODEL

# Temperature for extraction - deterministic output required.
OPENAI_EXTRACTION_TEMPERATURE: float = 0.0

# Max tokens for extraction response.
# Blood/CBC reports with 30+ diagnostic parameters need ~3000-4000 tokens.
# With conditions/contacts/fecal/xray extraction, output can reach ~5000 tokens.
OPENAI_EXTRACTION_MAX_TOKENS: int = 6144

# Query-specific settings - separated from extraction to allow independent tuning.
OPENAI_QUERY_TEMPERATURE: float = 0.0
OPENAI_QUERY_MAX_TOKENS: int = 1500

# --- Retry Configuration ---
# Retry backoff intervals in seconds (transient errors).
OPENAI_RETRY_BACKOFFS: list[float] = [1.0, 2.0]
# Rate-limit (429) specific backoffs - longer to allow TPM window recovery.
OPENAI_RATE_LIMIT_BACKOFFS: list[float] = [10.0, 20.0]
# Max concurrent AI API calls across the whole process.
CLAUDE_API_CONCURRENCY: int = 20

# --- Circuit Breaker Configuration ---
# Number of consecutive failures before the LLM circuit opens.
CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
# Seconds the circuit stays open before allowing a single probe attempt.
CIRCUIT_BREAKER_RECOVERY_SECONDS: float = 30.0

# --- Razorpay Retry Configuration ---
# Backoff intervals for Razorpay payment API retries (transient errors only).
RAZORPAY_RETRY_BACKOFFS: list[float] = [1.0, 2.0]

# --- Extraction Hardening ---
# Maximum number of automatic replay attempts for a failed extraction.
# After this many attempts the document stays 'failed' permanently.
EXTRACTION_MAX_AUTO_RETRIES: int = 3

# Confidence threshold below which a second-pass extraction is triggered.
# The model rates its own confidence 0.0-1.0; values below this floor mean
# the document was ambiguous and deserves a focused re-extraction.
EXTRACTION_LOW_CONFIDENCE_THRESHOLD: float = 0.65

# --- Weight Lookup (AI-powered ideal weight range) ---
OPENAI_WEIGHT_LOOKUP_MODEL: str = AI_QUERY_MODEL  # resolves from AI_PROVIDER
OPENAI_WEIGHT_LOOKUP_TEMPERATURE: float = 0.0
OPENAI_WEIGHT_LOOKUP_MAX_TOKENS: int = 200
WEIGHT_CACHE_STALENESS_DAYS: int = 365

# --- Nutrition AI Lookup (breed-specific targets) ---
OPENAI_NUTRITION_LOOKUP_MAX_TOKENS: int = 500
NUTRITION_CACHE_STALENESS_DAYS: int = 365

# --- Food Nutrition Estimation (unknown foods) ---
OPENAI_FOOD_ESTIMATION_MAX_TOKENS: int = 2000
FOOD_CACHE_STALENESS_DAYS: int = 365

# --- Personalized Nutrition Recommendations ---
OPENAI_NUTRITION_REC_MAX_TOKENS: int = 400
OPENAI_NUTRITION_REC_TEMPERATURE: float = 0.3

# WhatsApp retries - single retry only.
WHATSAPP_MAX_RETRIES: int = 1

# --- WhatsApp Cloud API ---
# Graph API version used for all WhatsApp Cloud API calls.
# Update here only when Meta deprecates the current version.
WHATSAPP_API_VERSION: str = os.getenv("WHATSAPP_API_VERSION", "v21.0")

# --- Dashboard Token ---
# Length in bytes for generating secure random dashboard tokens.
# 128-bit = 16 bytes, rendered as 32-char hex string.
DASHBOARD_TOKEN_BYTES: int = 16

# Number of days before a dashboard token expires.
# After expiry, the user can regenerate by typing "dashboard" in WhatsApp.
DASHBOARD_TOKEN_EXPIRY_DAYS: int = 30

# --- Supabase Storage ---
# Path template for uploaded files: {user_id}/{pet_id}/{filename}
# Enforced in the upload service - never construct paths manually elsewhere.
STORAGE_PATH_TEMPLATE: str = "{user_id}/{pet_id}/{filename}"

# --- Greeting Detection ---
# Shared set of greetings used by both onboarding and message router
# to detect casual greetings and avoid routing them to GPT.
GREETINGS: frozenset[str] = frozenset({
    "hi", "hello", "hey", "hii", "hiii", "yo", "sup",
    "hola", "namaste", "good morning", "good evening",
    "good afternoon", "gm", "start", "restart",
})

# --- Common Acknowledgment / Farewell Messages ---
# Messages that should get canned responses, not GPT calls.
ACKNOWLEDGMENTS: frozenset[str] = frozenset({
    "thanks", "thank you", "thankyou", "thx", "ty",
    "ok", "okay", "got it", "cool", "great", "nice",
    "awesome", "perfect", "sure", "alright",
})

FAREWELLS: frozenset[str] = frozenset({
    "bye", "goodbye", "good bye", "see you", "cya", "later",
})


HELP_COMMANDS: frozenset[str] = frozenset({
    "help", "menu", "commands", "what can you do",
})

# --- Order Flow ---
# Commands that trigger the product ordering flow.
ORDER_COMMANDS: frozenset[str] = frozenset({
    "order", "shop", "buy",
})

# Button payload IDs for order category selection.
ORDER_CAT_MEDICINES: str = "ORDER_CAT_MEDICINES"
ORDER_CAT_FOOD: str = "ORDER_CAT_FOOD"
ORDER_CAT_SUPPLEMENTS: str = "ORDER_CAT_SUPPLEMENTS"

# Button payload IDs for order confirmation.
ORDER_CONFIRM: str = "ORDER_CONFIRM"
ORDER_CANCEL: str = "ORDER_CANCEL"

# Sets for routing in message_router.
ORDER_CATEGORY_PAYLOADS: frozenset[str] = frozenset({
    ORDER_CAT_MEDICINES, ORDER_CAT_FOOD, ORDER_CAT_SUPPLEMENTS,
})

ORDER_CONFIRM_PAYLOADS: frozenset[str] = frozenset({
    ORDER_CONFIRM, ORDER_CANCEL,
})

# Fixed button payload IDs embedded in the order_fulfillment_check_v1 template.
# Template Quick Reply buttons have fixed payloads - no order_id in payload.
# The handler resolves the order by looking up the most recent pending order.
ORDER_FULFILL_YES: str = "ORDER_FULFILL_YES"
ORDER_FULFILL_NO: str = "ORDER_FULFILL_NO"

# Kept for backwards-compatibility with any legacy interactive messages already sent.
ORDER_FULFILL_YES_PREFIX: str = "ORDER_FULFILL_YES:"
ORDER_FULFILL_NO_PREFIX: str = "ORDER_FULFILL_NO:"

# Map button payload -> database category value.
ORDER_CATEGORY_MAP: dict[str, str] = {
    ORDER_CAT_MEDICINES: "medicines",
    ORDER_CAT_FOOD: "food_nutrition",
    ORDER_CAT_SUPPLEMENTS: "supplements",
}

# Map database category -> display label for WhatsApp messages.
ORDER_CATEGORY_LABELS: dict[str, str] = {
    "medicines": "Medicines",
    "food_nutrition": "Food & Nutrition",
    "supplements": "Supplements",
}

# --- Pet Weight ---
# Maximum allowed pet weight in kg. Anything above is rejected.
MAX_PET_WEIGHT_KG: float = 100.0

# --- Date Formats ---
# Accepted input date formats for parsing user-provided dates.
ACCEPTED_DATE_FORMATS: list[str] = [
    "%d/%m/%Y",      # DD/MM/YYYY
    "%d-%m-%Y",      # DD-MM-YYYY
    "%d.%m.%Y",      # DD.MM.YYYY
    "%d %B %Y",      # 12 March 2024
    "%d %b %Y",      # 12 Mar 2024
    "%d %B %y",      # 12 March 24
    "%d %b %y",      # 12 Mar 24
    "%d-%b-%Y",      # 29-Jan-2025
    "%d-%b-%y",      # 29-Jan-25
    "%B %d, %Y",     # March 12, 2024
    "%b %d, %Y",     # Mar 12, 2024
    "%Y-%m-%d",      # ISO format
    "%d/%m/%y",      # DD/MM/YY
    "%d-%m-%y",      # DD-MM-YY
]

# Formats for month+year only (day defaults to 1).
MONTH_YEAR_FORMATS: list[str] = [
    "%B %Y",         # March 2024
    "%b %Y",         # Mar 2024
    "%m/%Y",         # 03/2024
    "%m-%Y",         # 03-2024
]

# Canonical storage format for all dates in the database.
DB_DATE_FORMAT: str = "%Y-%m-%d"

# --- Nudge Engine ---
# Categories for health nudges (must match DB CHECK constraint).
NUDGE_CATEGORIES: list[str] = [
    "vaccine", "deworming", "flea", "condition", "nutrition", "grooming", "checkup",
]

# Priority sort order - lower number = higher priority.
NUDGE_PRIORITY_ORDER: dict[str, int] = {"urgent": 0, "high": 1, "medium": 2}

# Source sort order - record-based nudges rank above AI-generated ones.
NUDGE_SOURCE_ORDER: dict[str, int] = {"record": 0, "ai": 1}

# Trigger types for nudge generation.
NUDGE_TRIGGER_CRON: str = "cron"
NUDGE_TRIGGER_UPLOAD: str = "upload"
NUDGE_TRIGGER_INACTIVITY: str = "inactivity"

# WhatsApp button payload IDs for nudge interactions.
NUDGE_ACTION: str = "NUDGE_ACTION"
NUDGE_DISMISS: str = "NUDGE_DISMISS"
NUDGE_VIEW_DASHBOARD: str = "NUDGE_VIEW_DASHBOARD"

# Set for routing in message_router.
NUDGE_PAYLOADS: frozenset[str] = frozenset({
    NUDGE_ACTION, NUDGE_DISMISS, NUDGE_VIEW_DASHBOARD,
})

# Nudge cache freshness - skip regeneration if nudges are younger than this.
NUDGE_CACHE_HOURS: int = 6

# --- Nudge Scheduler - Level System ---
# User levels for the nudge scheduler (recalculated on every trigger event).
NUDGE_LEVEL_0: int = 0  # no breed set OR breed set but no preventive_record rows
NUDGE_LEVEL_1: int = 1  # breed set, no preventive_record rows
NUDGE_LEVEL_2: int = 2  # breed set + at least 1 preventive_record row

# O+N schedule days for Level 0 and Level 1 users.
# Index 0 = first nudge (O+1), index 4 = last scheduled slot (O+30).
NUDGE_SCHEDULE_DAYS: list[int] = [1, 5, 10, 20, 30]

# Minimum hours between any two nudge sends for the same user (engagement gap rule).
NUDGE_MIN_GAP_HOURS: int = 48

# Maximum number of nudges that can be sent to a user in a rolling 7-day window.
# Reminder messages are excluded because this cap applies to nudge_delivery_log only.
NUDGE_MAX_PER_WEEK: int = 2

# Inactivity threshold for forcing a nudge outside the O+N schedule.
# If no inbound/outbound activity exists in message_logs for this long,
# scheduler can send the next undelivered slot (subject to other guards).
NUDGE_INACTIVITY_TRIGGER_HOURS: int = 72

# Days between nudges for post-O+30 users (Level 0 / 1) and Level 2 post-slot-5.
NUDGE_POST_SCHEDULE_INTERVAL_DAYS: int = 30

# Level 2 data priority for Breed + Data nudge sequencing (slots 1-3).
# The scheduler picks the top category from this list that has NO records yet.
NUDGE_L2_DATA_PRIORITY: list[str] = [
    "vaccine", "flea_tick", "deworming", "nutrition",
    "supplement", "condition", "medication", "diagnostics", "grooming",
]

# --- Document Categories ---
# Categories assigned by GPT extraction to classify uploaded documents.
# Used for grouping in the dashboard, PDF appendix, and filtering.
# The 5 primary report types (Blood Report -> PCR) map to the PDF appendix sections.
DOCUMENT_CATEGORIES: list[str] = [
    "Blood Report",
    "Urine Report",
    "Imaging",
    "Prescription",
    "PCR & Parasite Panel",
    "Vaccination",
    "Other",
]

# --- Database Connection Pool ---
# Co-located with concurrency constants to make the relationship explicit:
#   pool_size = MAX_CONCURRENT_MESSAGE_PROCESSING (one connection per handler)
#   max_overflow covers uploads + extractions running concurrently with handlers
DB_POOL_SIZE: int = MAX_CONCURRENT_MESSAGE_PROCESSING          # 30
DB_POOL_MAX_OVERFLOW: int = MAX_CONCURRENT_MESSAGE_PROCESSING  # 30 -> hard cap 60 total
DB_POOL_RECYCLE_SECONDS: int = 120   # refresh before Supabase/Supavisor idle-timeout
DB_POOL_TIMEOUT_SECONDS: int = 30    # connection checkout timeout
DB_POOL_WAIT_WARN_SECONDS: float = 10.0  # warn when checkout waits longer than this

# Supabase TCP keepalive settings (PgBouncer compatibility).
DB_KEEPALIVES_IDLE: int = 30       # seconds idle before first probe
DB_KEEPALIVES_INTERVAL: int = 10   # seconds between probes
DB_KEEPALIVES_COUNT: int = 5       # probes before declaring connection dead

# --- Vaccine Age Eligibility ---
# Minimum age (in days) a pet must be to receive each puppy/kitten vaccine dose.
# Dogs/cats >= PUPPY_AGE_CUTOFF_DAYS are adults and never shown puppy vaccines.
# Keys must match preventive_master.item_name values (lowercase comparison).
PUPPY_VACCINE_MIN_AGE_DAYS: dict[str, int] = {
    "dhppi 1st dose":         42,   # 6 weeks
    "dhppi 2nd dose":         63,   # 9 weeks
    "dhppi 3rd dose":         84,   # 12 weeks
    "puppy booster":          90,   # ~3 months
    "pentavalent 1st dose":   42,
    "pentavalent 2nd dose":   63,
    "pentavalent 3rd dose":   84,
    "feline core 1st dose":   42,
    "feline core 2nd dose":   63,
    "feline core 3rd dose":   84,
}

# Pets at or above this age (days) are adults; puppy-specific vaccines are hidden.
PUPPY_AGE_CUTOFF_DAYS: int = 365  # 1 year

# --- Hygiene Item Labels ---
# Maps item_id to display label for reminder messages.
# item_id values must match hygiene_preference.item_id in the database.
HYGIENE_ITEM_LABELS: dict[str, str] = {
    "bath-nail":    "Bath, Brush & Nail Trim",
    "ear-clean":    "Ear Cleaning",
    "teeth-brush":  "Dental / Teeth Brushing",
    "coat-brush":   "Coat Brushing",
}
