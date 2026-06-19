# SmartCV Builder

A Django-based CV/resume builder with AI-powered writing assistance, Stripe
payments, 10 professional templates, and WeasyPrint PDF export.

## What's built

### Core CV builder
- Register / login / logout / password reset (console email in dev, real
  SMTP via env vars in production)
- Profile with free / premium plan — enforces a 2-CV limit on free tier
- Full data model: Resume, PersonalInfo, Experience, Education, Skill,
  Certification, Project, Language, Award, Publication, Reference,
  HobbyInterest, CustomSection, Template, DownloadHistory
- Builder hub per CV with completion ring; every section editable inline
- Experience and Education use dynamic inline formsets (JS add/remove)
- Skills, Certifications, Projects, Languages, Awards, Publications,
  References, Hobbies, Custom Sections through a generic registry-driven
  CRUD flow (one view + two templates handle all nine)

### 10 CV templates (all visually distinct, all generating real PDFs)
| # | Slug | Accent | Premium |
|---|------|--------|---------|
| 1 | modern-corporate | #1d4ed8 | Free |
| 2 | minimalist | #111827 | Free |
| 3 | ats-friendly-resume | #0f766e | Free |
| 4 | creative-portfolio | #7c3aed | Free |
| 5 | executive-classic | #1e3a5f | Free |
| 6 | tech-dark | #22d3ee | **Premium** |
| 7 | two-column-elegant | #be185d | Free |
| 8 | academic-research | #14532d | Free |
| 9 | bold-infographic | #f59e0b | **Premium** |
| 10 | compact-one-page | #0369a1 | Free |

Adding a new template: seed a `Template` row, add an HTML file under
`templates/resumes/templates_layouts/`, add one entry to `_template_html_name()`
in `resumes/views.py`.

### PDF export
WeasyPrint renders the same HTML used for in-browser preview. Free-plan
downloads carry a diagonal watermark; premium doesn't. Every download is
logged to `DownloadHistory`.

### AI features (OpenAI or GitHub)
Four AJAX endpoints on the builder hub, all fail gracefully when the API key
is not set:
- **Rewrite Summary** — generates a 2-4 sentence professional summary
- **Analyze CV** — scores the CV 0-100 with strengths, improvements, ATS tips
- **Career Suggestions** — 4-6 personalised next-step recommendations
- **Improve Bullet** — rewrites a single job description bullet point

Set `AI_PROVIDER` to `openai`, `github`, or `zai` (default: `openai`):
- **OpenAI**: Set `OPENAI_API_KEY` and optionally `OPENAI_MODEL` (default: `gpt-4o-mini`)
- **GitHub**: Set `GITHUB_API_KEY` and optionally `GITHUB_AI_MODEL` (default: `gpt-4o`);
  `GITHUB_AI_ENDPOINT` defaults to Azure OpenAI endpoint.
- **ZAI**: z.ai provider — set `ZAI_API_KEY`, `ZAI_AI_MODEL` (default: `glm-5.2`),
  and `ZAI_AI_ENDPOINT` (default: `https://api.z.ai/api/paas/v4/chat/completions`).

### Stripe payments (requires `STRIPE_SECRET_KEY` etc.)
- User clicks "Upgrade to Premium" → Stripe-hosted Checkout Session
- Webhook (`/payments/webhook/`) handles `checkout.session.completed` →
  flips `profile.plan = "premium"` and stores `stripe_customer_id`
- Webhook also handles `customer.subscription.deleted` / `.updated` →
  downgrades user if subscription lapses
- Subscription management page (`/payments/subscription/`) lets premium
  users open the Stripe Customer Portal for self-service billing management

## Setup

```bash
pip install -r requirements.txt
python3 manage.py migrate          # creates tables + seeds all 10 templates
python3 manage.py createsuperuser
python3 manage.py runserver
```

### WeasyPrint system libraries (Debian/Ubuntu)
```bash
apt-get install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b \
                libgdk-pixbuf2.0-0 libcairo2
```

### Required environment variables

| Variable | Default | Notes |
|---|---|---|
| `DJANGO_SECRET_KEY` | insecure dev default | Change in production |
| `DJANGO_DEBUG` | `True` | Set `False` in production |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated |
| `AI_PROVIDER` | `openai` | Choose `openai` or `github` |
| `OPENAI_API_KEY` | *(empty — AI features disabled)* | `sk-…` from platform.openai.com (if using OpenAI) |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `GITHUB_API_KEY` | *(empty)* | GitHub token for models API (if using GitHub) |
| `GITHUB_AI_MODEL` | `gpt-4o` | GitHub AI model name |
| `GITHUB_AI_ENDPOINT` | `https://models.inference.ai.azure.com` | Azure OpenAI endpoint for GitHub Models |
| `ZAI_API_KEY` | *(empty)* | z.ai provider API key (if using ZAI) |
| `ZAI_AI_MODEL` | `glm-5.2` | ZAI model name |
| `ZAI_AI_ENDPOINT` | `https://api.z.ai/api/paas/v4/chat/completions` | ZAI provider endpoint |
| `STRIPE_SECRET_KEY` | *(empty — payments disabled)* | `sk_test_…` or `sk_live_…` |
| `STRIPE_PUBLISHABLE_KEY` | *(empty)* | `pk_test_…` or `pk_live_…` |
| `STRIPE_WEBHOOK_SECRET` | *(empty)* | `whsec_…` from Stripe dashboard |
| `STRIPE_PREMIUM_PRICE_ID` | *(empty)* | `price_…` — your Premium product price |
| `DJANGO_DB_ENGINE` | *(SQLite)* | Set `postgres` + vars below for Postgres |
| `POSTGRES_DB/USER/PASSWORD/HOST/PORT` | — | Only used when `DJANGO_DB_ENGINE=postgres` |
| `DJANGO_EMAIL_BACKEND` | console | Set `django.core.mail.backends.smtp.EmailBackend` + `EMAIL_*` for real email |

### Stripe webhook in development
```bash
stripe listen --forward-to localhost:8000/payments/webhook/
```

### Running tests
```bash
python3 manage.py test
# → 27 tests: accounts (4), resumes (9), AI service (9), all-template renders (5)
```

## Project layout
```
smartcv/        Django settings, root URLs
accounts/       Profile model (plan/role/stripe_customer_id), auth views
resumes/        CV models, forms, views, URLs, admin, 10 template HTML files
ai/             OpenAI service layer + 4 AJAX views
payments/       Stripe checkout, webhook, subscription management
templates/
  base.html                      App chrome (sidebar, topbar)
  accounts/                      Login, register, profile, password-reset
  resumes/                       Dashboard, builder hub, all CRUD pages
  resumes/templates_layouts/     10 standalone CV layout HTML files
  payments/                      Success, cancel, subscription pages
static/css/app.css               Dashboard/builder UI styles
media/                           Uploaded profile pictures
```

## Still on the roadmap
- **Social login** (Google/LinkedIn) via `django-allauth`
- **Resume import** from PDF/DOCX/LinkedIn
- **Cover letter generator** (natural slot: a new AI endpoint + builder section)
- **Celery + Redis** for async AI calls (currently synchronous, fine at low volume)
- **DRF + JWT REST API** layer over the existing models
- **Drag-and-drop section reordering** (order field exists on every model,
  just needs a frontend drag-and-drop + a PATCH endpoint)
- **Deep CV duplication** (currently copies top-level + personal info only)
- **Paystack / Flutterwave** as payment alternative for African markets
  (the webhook handler pattern in `payments/views.py` is the same shape)
