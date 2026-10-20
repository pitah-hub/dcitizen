# Huduma Requests: Public Service Request System

A mini eCitizen-style portal. Citizens report public service problems (a broken streetlight, a water issue, uncollected garbage), then track each request until it is resolved. County officers manage requests from an admin panel.

**Live demo:** https://fitaa.pythonanywhere.com (the officer login for the live site is sent with the submission, not published here)

## Features

### Required by the brief

| Requirement | How it is done |
|---|---|
| Citizen registration and login | Email and password. National ID (7 or 8 digits) and a Kenyan phone number are validated. |
| Submit a request | Category, county, area, description, optional image (JPG or PNG, up to 5 MB) and an optional map pin. |
| Admin dashboard | Counts, two charts, the oldest pending requests, and a filterable, searchable request list. |
| Status tracking | Pending, then In Progress, then Resolved, with a full timeline. Anyone can also look a request up by its reference number. |
| Basic analytics | Open vs resolved, requests per category, and citizen satisfaction. |

### Beyond the brief

- **Messages:** citizens and officers can exchange messages on a request. The thread closes when the request is resolved.
- **Satisfaction ratings:** the owner of a resolved request can leave 1 to 5 stars and a comment, once. Officers see the average, the low ratings and the latest comments.
- **Map pin:** report the exact spot using an OpenStreetMap map, your device location, or a click. Officers see it on the request page.
- **Printable receipt:** one clean page per request, saved as PDF from the browser's print dialog.
- **Password reset:** by an emailed one-time link that expires after one hour.
- **Suspend posting:** officers can stop a citizen from reporting, messaging or rating. The citizen can still sign in and read, and sees why.
- **Email notifications:** on submission, on every status change, and on officer messages.
- **Seed commands and tests:** a fresh install has demo data in one command, and the automated tests cover the workflow, permissions, forms, emails and seed commands.

## Quick start

You need Python 3.10 or newer and Git.

```
git clone https://github.com/pitah-hub/dcitizen.git
cd dcitizen
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_reference_data
python manage.py seed_demo
python manage.py seed_demo_feedback
python manage.py runserver
```

On Mac or Linux, replace the activate line with `source venv/bin/activate`. Then open http://127.0.0.1:8000/.

Emails (confirmations, status updates, password reset links) are printed in the terminal where `runserver` is running. No mail server is needed.

## Demo accounts

`seed_demo` creates these accounts and prints them. The password below is for local use only.

| Role | Email | Password |
|---|---|---|
| Officer | officer@demo.local | Demo-pass-123 |
| Citizen | amina@demo.local | Demo-pass-123 |
| Citizen | brian@demo.local | Demo-pass-123 |
| Citizen | cynthia@demo.local | Demo-pass-123 |

Running `seed_demo` again is safe: it repairs the accounts and never duplicates data. It also creates 24 sample requests across all three statuses, some with map pins. To use a different password, run `python manage.py seed_demo --password "your-password"`.

You can also create your own account on the Register page. Officers are accounts with staff status, made by `seed_demo` or `python manage.py createsuperuser`.

## How it works

### Status workflow

```
Pending  ->  In Progress  ->  Resolved
```

Moves are forward only, one step at a time. A resolved request cannot be reopened.

### Who can do what

| Action | Visitor | Citizen | Officer |
|---|---|---|---|
| See the landing, About, Contact pages and track by reference | Yes | Yes | Yes |
| Report an issue | No | Yes (unless suspended) | No (goes to the panel) |
| Open a request | No | Own requests only | All requests |
| Change a status | No | No | Yes |
| Message on a request | No | Own open request | Any open request |
| Rate a request | No | Own resolved request, once | No |
| Suspend or reinstate posting | No | No | Yes |

### Main pages

| Page | URL |
|---|---|
| Landing and public tracking | `/`, `/track/?ref=SR-2026-0001` |
| Register, login, password reset | `/register/`, `/login/`, `/password-reset/` |
| Citizen dashboard, my requests, report | `/dashboard/`, `/requests/`, `/requests/new/` |
| Request detail, receipt | `/requests/<id>/`, `/requests/<id>/receipt/` |
| Officer dashboard and requests | `/admin-panel/`, `/admin-panel/requests/` |
| Django's built-in admin (superusers) | `/admin/` |

## Project structure

```
config/        project settings and root URLs
accounts/      custom user (email login), registration, profile, password reset
services/      requests, status workflow, feedback, messages, receipts, analytics, seed commands
adminpanel/    officer dashboard, request management, citizen moderation
templates/     base layout, shared partials, and each app's pages
static/        site.css, modern.css and two small JavaScript files
```

## Design decisions

- **One way to change a status.** `ServiceRequest.change_status()` checks the allowed move, saves it and logs the history in one transaction. Views never set a status directly, so the rules live in one place.
- **Owner-scoped queries, 404 not 403.** Citizens only ever query their own requests. Opening someone else's request returns "not found", so request numbers cannot be probed.
- **Public tracking shows the minimum.** The tracking page shows only the category, county, status and dates. It never shows names, descriptions, areas, images, officer notes or map coordinates.
- **Database-level guarantees.** One rating per request is enforced by a one-to-one relation, and the 1 to 5 range by a check constraint, not only by the views.
- **Messages and status history are separate.** Status changes are the official record. Messages are the conversation.
- **Server-rendered pages.** Django templates and Bootstrap with no build step. The little JavaScript there is (map, animations) is plain, and every page works without it.
- **Reference numbers** look like `SR-2026-0007`, built from the record's id.
- **SQLite and console email.** Both need no setup, so a reviewer can run the project in minutes. The models are portable, and moving to PostgreSQL or real SMTP is a settings change.
- **Map pins are optional and validated on the server:** both coordinates are required together, and the pin must fall inside Kenya.

## Security

- CSRF protection on every form; passwords hashed and checked with Django's validators.
- Staff-only and citizen-only views are enforced in code, not only by hiding buttons.
- Uploads are limited to JPG and PNG, up to 5 MB.
- Password reset links are signed, work once and expire after one hour. An unknown email gets the same response as a known one, so accounts cannot be discovered through the form.
- In production, the secret key, allowed hosts and secure cookies come from environment variables.

## Tests

```
python manage.py test
```

Covers the status workflow, permissions and ownership, forms and validation, emails, analytics, ratings, messages, the receipt, map pins, suspension, password reset and the seed commands.

## Deployment (PythonAnywhere)

Set these in the WSGI file: `DJANGO_PRODUCTION=1`, `DJANGO_SECRET_KEY`, and `DJANGO_ALLOWED_HOSTS` (your site's hostname). Run `python manage.py collectstatic --noinput`, then map `/static/` to the `staticfiles` folder and `/media/` to the `media` folder in the Web tab.

On a public site, create the demo accounts with a private password so the published one does not protect a live officer account:

```
python manage.py seed_demo --password "a-private-password"
```

## Known limitations

- **Tracking by reference is open.** Reference numbers are sequential, so someone could try numbers and see request statuses. Only status information is shown, never personal data.
- **Email is console-only.** On the live site, emails (including password reset links) appear in the server log, so a reset cannot be completed there. Run the project locally to see the full flow.
- **Messaging is basic.** Officers are not notified of citizen messages, messages cannot be edited or deleted, and there is no rate limiting.
- **Concurrent edits.** If two officers update the same request at the same moment, the second can pass its check against stale data and log a duplicate step.
- **No audit log** records who suspended a citizen, or when.
- **Map needs the internet.** Map tiles come from OpenStreetMap, and the location button needs HTTPS (or localhost) and a device that can work out its position.
- **Storage.** SQLite has limited write concurrency, and uploaded images are stored on the server's disk.
## How this was built

AI coding assistance was used during development. I tested and deployed the project.”

## Possible next steps

Real SMTP email, notifications for officers, an audit log, PostgreSQL, assigning requests to specific officers, request throttling, Swahili translations, and a REST API.
