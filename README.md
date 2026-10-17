# Huduma Requests

> Screenshot placeholder: add a landing-page and staff-dashboard screenshot here before submission.

Huduma Requests is a mini eCitizen-style public-service reporting portal. Citizens can register, report issues, upload supporting images, and follow each status update. Staff officers can search requests, manage the workflow, and view operational analytics.

## Features

- Citizen registration and email-based login
- Public landing, about, contact, and privacy-safe request tracking
- Service reports with category, county, landmark, description, and optional image
- Owner-scoped citizen dashboard, request list, detail page, and status timeline
- Staff-only request management, search, filtering, and status notifications
- Dashboard cards plus open-vs-resolved and category charts
- Kenyan county and service-category reference data
- Console email notifications for submissions and status updates

## Tech stack

| Technology | Why it is used |
| --- | --- |
| Django 5.2 | Secure server-rendered application framework with built-in admin and auth. |
| SQLite | Zero-configuration local database for the take-home project. |
| Bootstrap 5.3.3 | Responsive, accessible layout without a front-end build tool. |
| Bootstrap Icons 1.11.3 | Consistent lightweight interface icons. |
| Chart.js 4.4.1 | Clear client-side operational charts from safe JSON data. |
| Pillow | Django image-field support and upload validation. |

## Setup

### Windows PowerShell

```powershell
git clone <your-repository-url> huduma-requests
cd huduma-requests
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_reference_data
python manage.py seed_demo
python manage.py runserver
```

### macOS / Linux

```bash
git clone <your-repository-url> huduma-requests
cd huduma-requests
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_reference_data
python manage.py seed_demo
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. The console running Django prints notification emails instead of sending SMTP mail.

To use your own administrator account instead of the demo officer:

```bash
python manage.py createsuperuser
```

## Demo accounts

After `python manage.py seed_demo`:

| Role | Email | Password |
| --- | --- | --- |
| Staff officer | `officer@demo.local` | `Demo-pass-123` |
| Citizen | `amina@demo.local` | `Demo-pass-123` |
| Citizen | `brian@demo.local` | `Demo-pass-123` |
| Citizen | `cynthia@demo.local` | `Demo-pass-123` |

The command is idempotent: if demo users already exist, it does not create duplicate records.

## URL map

| URL | Purpose |
| --- | --- |
| `/` | Landing page |
| `/track/?ref=SR-2026-0001` | Public, privacy-safe tracking |
| `/register/`, `/login/`, `/logout/` | Account access |
| `/profile/`, `/password-change/` | Citizen account management |
| `/dashboard/` | Citizen dashboard |
| `/requests/`, `/requests/new/`, `/requests/<id>/` | Citizen request workflow |
| `/admin-panel/` | Staff analytics dashboard |
| `/admin-panel/requests/` | Staff request list, filters, and search |
| `/admin-panel/requests/<id>/` | Staff request management |
| `/admin/` | Django administrative site |

## Project structure

```text
config/       Django settings and root URLs
accounts/     Custom email-login user model and account pages
services/     Request models, forms, permissions, notifications, commands, citizen views
adminpanel/   Staff dashboard and request-management views
templates/    Project-level Bootstrap templates
static/       Project CSS
```

## Status workflow

```text
Pending  -->  In Progress  -->  Resolved
```

The `ServiceRequest.change_status()` model method is the only workflow entry point. It validates the transition and records a `StatusUpdate` in the same database transaction.

## Design decisions

- **Single status entry point:** Prevents accidental status changes that have no audit history.
- **Owner-scoped queries:** Citizen lists use `for_user()` and a foreign request detail URL returns 403.
- **Privacy-safe public tracking:** It shows reference, category, county, status, and timeline only—never contact details, location, description, or uploaded image.
- **Console email backend:** Makes submission and status emails visible in development without SMTP credentials.
- **SQLite now, PostgreSQL later:** SQLite keeps setup simple; database configuration can change through Django settings for deployment.
- **Server-rendered views:** Appropriate for the fixed, form-led workflow and keeps the project dependency-free.

## Tests

```bash
python manage.py check
python manage.py test
```

The view tests cover registration, role redirects, owner isolation, admin permissions, report submission and image upload, emails, workflow rejection, tracking privacy, and staff filters/search.

## Known limitations and future work

- Contact information is placeholder data.
- Staff assignment, GIS coordinates, and real email/SMS delivery are not yet included.
- Production deployment should use environment variables, HTTPS, a real SMTP provider, persistent media storage, PostgreSQL, and restrictive `ALLOWED_HOSTS`.
