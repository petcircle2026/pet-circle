# PetCircle — Credentials Handover Template

**CONFIDENTIAL** — Share via secure channel only (1Password, Bitwarden, encrypted email, etc.)

This document lists every credential the client needs to operate PetCircle independently. Fill in actual values and share securely before Phase 2 (GitHub transfer).

---

## GitHub

| Item | Value | Notes |
|------|-------|-------|
| **Repository URL** | `https://github.com/BerenikeSolutions/pet-circle` | Transfer to client's account in Phase 2 |
| **Client GitHub Account** | ___________________ | Client to provide |
| **Client GitHub Username** | ___________________ | For transfer authorization |
| **New Repository URL** | ___________________ | Will be `https://github.com/{client-username}/pet-circle` after transfer |

---

## Render Backend

### Account Setup
| Item | Value | Notes |
|------|-------|-------|
| **Render Account Email** | ___________________ | Client creates at render.com |
| **Render API Token** | ___________________ | Optional but recommended for API access |
| **Production Service Name** | `petcircle-api` | Auto-deployed from `main` branch |
| **Dev Service Name** | `petcircle-api-dev` | Auto-deployed from `dev` branch |
| **Production Service URL** | ___________________ | Will be assigned by Render (e.g., `https://petcircle-api.onrender.com`) |
| **Dev Service URL** | ___________________ | Will be assigned by Render (e.g., `https://petcircle-api-dev.onrender.com`) |

### Environment Variables for Render

All these must be entered in **Render Dashboard → Select Service → Environment**

| Variable | Value | Required? | Notes |
|----------|-------|-----------|-------|
| `APP_ENV` | `production` | YES | Set for production service only |
| `APP_ENV` | `development` | YES | Set for dev service only |
| `DATABASE_URL` | ___________________ | YES | PostgreSQL connection string from Supabase |
| `SUPABASE_URL` | ___________________ | YES | e.g., `https://xxx.supabase.co` |
| `SUPABASE_KEY` | ___________________ | YES | Anon key from Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | ___________________ | YES | Service role key from Supabase |
| `SUPABASE_BUCKET_NAME` | `petcircle-documents` | YES | S3 bucket name in Supabase |
| `WHATSAPP_TOKEN` | ___________________ | YES | From Meta Business Platform |
| `WHATSAPP_VERIFY_TOKEN` | ___________________ | YES | Custom token for webhook verification |
| `WHATSAPP_PHONE_NUMBER_ID` | ___________________ | YES | From Meta Business Platform |
| `WHATSAPP_APP_SECRET` | ___________________ | YES | From Meta Business Platform |
| `ADMIN_SECRET_KEY` | ___________________ | YES | Secret for admin endpoints; share with GitHub Actions |
| `ADMIN_DASHBOARD_PASSWORD` | ___________________ | YES | Password for admin login (bcrypt hashed) |
| `ENCRYPTION_KEY` | ___________________ | YES | 32-byte encryption key for sensitive fields |
| `FRONTEND_URL` | ___________________ | YES | Will be Vercel URL (e.g., `https://pet-circle-chi.vercel.app`) |
| `OPENAI_API_KEY` | ___________________ | NO* | Required if `AI_PROVIDER=openai` |
| `ANTHROPIC_API_KEY` | ___________________ | NO* | Required if `AI_PROVIDER=claude` |
| `AI_PROVIDER` | `claude` or `openai` | YES | Determines which AI service to use |
| `GCP_CREDENTIALS_JSON` | ___________________ | YES | Base64-encoded GCP service account JSON |
| `GCP_BUCKET_NAME` | ___________________ | YES | GCP Cloud Storage bucket name |
| `RAZORPAY_KEY_ID` | ___________________ | NO | Required if payments enabled |
| `RAZORPAY_KEY_SECRET` | ___________________ | NO | Required if payments enabled |
| `ORDER_NOTIFICATION_PHONE` | ___________________ | NO | WhatsApp number for order notifications |
| `CLOUDAMQP_URL` | ___________________ | NO | Required if using RabbitMQ |

### WhatsApp Templates (16 total)
All template names must match Meta Business Platform exactly.

| Variable | Template Name | Value | Notes |
|----------|---------------|-------|-------|
| `WHATSAPP_TEMPLATE_CONFLICT` | ___________________ | ___________________ | Conflict detection template |
| `WHATSAPP_TEMPLATE_ORDER_FULFILLMENT_CHECK` | ___________________ | ___________________ | Order status check template |
| `WHATSAPP_TEMPLATE_BIRTHDAY` | ___________________ | ___________________ | Birthday reminder template |
| `WHATSAPP_TEMPLATE_REMINDER_T7` | ___________________ | ___________________ | 7-day advance reminder |
| `WHATSAPP_TEMPLATE_REMINDER_DUE` | ___________________ | ___________________ | Due date reminder |
| `WHATSAPP_TEMPLATE_REMINDER_D3` | ___________________ | ___________________ | 3-day reminder |
| `WHATSAPP_TEMPLATE_REMINDER_OVERDUE` | ___________________ | ___________________ | Overdue reminder |
| `WHATSAPP_TEMPLATE_NUDGE_VALUE_ADD_PERSONAL` | ___________________ | ___________________ | Personalized nudge |
| `WHATSAPP_TEMPLATE_NUDGE_ENGAGEMENT` | ___________________ | ___________________ | Engagement nudge |
| `WHATSAPP_TEMPLATE_NUDGE_BREED` | ___________________ | ___________________ | Breed-specific nudge |
| `WHATSAPP_TEMPLATE_NUDGE_BREED_DATA` | ___________________ | ___________________ | Breed data nudge |
| `WHATSAPP_TEMPLATE_NUDGE_NO_BREED` | ___________________ | ___________________ | Generic nudge (no breed) |
| `WHATSAPP_TEMPLATE_NUDGE_ENGAGEMENT_NO_BREED` | ___________________ | ___________________ | Engagement nudge (no breed) |
| `WHATSAPP_TEMPLATE_NUDGE_BREED_DATA_NO_BREED` | ___________________ | ___________________ | Breed data nudge (no breed) |
| `WHATSAPP_TEMPLATE_REMINDER_FOOD_SCHEDULED` | ___________________ | ___________________ | Food order reminder |
| `WHATSAPP_TEMPLATE_REMINDER_SUPPLEMENT_SCHEDULED` | ___________________ | ___________________ | Supplement reminder |
| `WHATSAPP_TEMPLATE_REMINDER_CHRONIC_SCHEDULED` | ___________________ | ___________________ | Chronic care reminder |

---

## Vercel Frontend

### Account Setup
| Item | Value | Notes |
|------|-------|-------|
| **Vercel Account Email** | ___________________ | Client creates at vercel.com |
| **New Project Name** | ___________________ | e.g., `pet-circle` |
| **Production Domain** | ___________________ | Will be assigned (e.g., `pet-circle-chi.vercel.app`) |

### Environment Variables for Vercel

| Variable | Value | Required? | Notes |
|----------|-------|-----------|-------|
| `NEXT_PUBLIC_API_URL` | ___________________ | YES | Render production URL (e.g., `https://petcircle-api.onrender.com`) |

---

## Supabase Database

### Account Setup
| Item | Value | Notes |
|------|-------|-------|
| **Supabase Email** | ___________________ | Client creates account |
| **Organization Name** | ___________________ | Client's org on Supabase |
| **Project Name** | ___________________ | e.g., `pet-circle-prod` |
| **Database Password** | ___________________ | Strong password; store securely |
| **Region** | ___________________ | Recommended: closest to India (Singapore) |
| **Supabase URL** | ___________________ | Will be assigned (e.g., `https://xxx.supabase.co`) |
| **Supabase Anon Key** | ___________________ | From Supabase dashboard |
| **Supabase Service Role Key** | ___________________ | From Supabase dashboard |
| **Supabase Storage Bucket Name** | `petcircle-documents` | Already defined in schema |

### Database Setup
| Item | Status | Notes |
|------|--------|-------|
| Run 60 migrations from `backend/migrations/` | _____ | Execute in order |
| Import existing pet/user data (if migrating) | _____ | Optional data migration |
| Verify all tables created | _____ | Check dashboard |

---

## External Services

### Meta / WhatsApp Business API
| Item | Value | Notes |
|------|-------|-------|
| **Meta Business Account** | ___________________ | Client's Meta account |
| **WhatsApp Business Phone Number** | ___________________ | Client's verified phone |
| **App ID** | ___________________ | From Meta Business Platform |
| **App Secret** | ___________________ | From Meta Business Platform |
| **Webhook URL (for Meta)** | ___________________ | `https://{render-url}/webhook/whatsapp` |
| **Webhook Verify Token** | ___________________ | Set in Render env var `WHATSAPP_VERIFY_TOKEN` |

### OpenAI (if using `AI_PROVIDER=openai`)
| Item | Value | Notes |
|------|-------|-------|
| **OpenAI Account** | ___________________ | Client's account at platform.openai.com |
| **API Key** | ___________________ | Generate and store securely |
| **Model** | `gpt-4.1` | Specified in extraction prompts |

### Anthropic (if using `AI_PROVIDER=claude`)
| Item | Value | Notes |
|------|-------|-------|
| **Anthropic Account** | ___________________ | Client's account at console.anthropic.com |
| **API Key** | ___________________ | Generate and store securely |
| **Default Model** | `claude-opus-4-6` or `claude-sonnet-4-6` | Check `backend/app/config.py` |

### GCP Cloud Storage
| Item | Value | Notes |
|------|-------|-------|
| **GCP Project ID** | ___________________ | Client's GCP project |
| **GCP Bucket Name** | ___________________ | e.g., `petcircle-documents-prod` |
| **Service Account Email** | ___________________ | e.g., `xxx@{project}.iam.gserviceaccount.com` |
| **Service Account Key (JSON)** | ___________________ | Download from GCP Console; base64-encode for `GCP_CREDENTIALS_JSON` |

### Razorpay (if payments enabled)
| Item | Value | Notes |
|------|-------|-------|
| **Razorpay Account** | ___________________ | Client's account at dashboard.razorpay.com |
| **Key ID** | ___________________ | From Razorpay Dashboard |
| **Key Secret** | ___________________ | From Razorpay Dashboard |

### RabbitMQ / CloudAMQP (if async tasks enabled)
| Item | Value | Notes |
|------|-------|-------|
| **CloudAMQP Account** | ___________________ | Client's account (optional; async uses asyncio if not set) |
| **AMQP URL** | ___________________ | Format: `amqp://user:pass@host/vhost` |

---

## GitHub Actions Secrets

These must be entered in **GitHub → Settings → Secrets and Variables → Actions**

| Secret | Value | Used By |
|--------|-------|---------|
| `PRODUCTION_API_URL` | ___________________ | Reminder cron, GCP sync cron, extraction replay cron |
| `ADMIN_SECRET_KEY` | ___________________ | Same as Render `ADMIN_SECRET_KEY` |
| `RENDER_BACKEND_URL` | ___________________ | Keepalive cron, deploy check |

---

## Summary Checklist

- [ ] All Render env vars filled
- [ ] All WhatsApp template names filled (16 templates)
- [ ] Vercel `NEXT_PUBLIC_API_URL` filled
- [ ] Supabase URLs and keys filled
- [ ] External service credentials gathered
- [ ] GitHub Actions secrets filled
- [ ] Credentials shared securely with client
- [ ] Client has created accounts on: GitHub, Render, Vercel, Supabase, Meta

**Next:** Proceed to Phase 2 (GitHub Transfer)
