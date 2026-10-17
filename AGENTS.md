# Public Service Request System (mini eCitizen-style)

Job-interview take-home project. Citizens register, report public service problems
(broken streetlight, water issue, garbage collection), and track them. Staff manage
requests through an admin panel. Graded on: code quality and structure (25%),
functionality (35%), UI/UX (20%), documentation (10%), bonus features (10%).

Your job is the WEB LAYER: urls, views, templates, static files, seed commands,
view-level tests and README. The models, forms, permissions, analytics and email
helpers are already written and tested. Build on them, do not rewrite them.

Work in PHASES (bottom of this file). Finish one phase, run the checks, report, and
STOP. Do not start the next phase until I say "continue".

---

## 1. Hard rules (read before writing any code)

1. DO NOT EDIT these files. If you think one needs a change, stop and explain why instead:
   - accounts/models.py, accounts/admin.py, accounts/forms.py
   - services/models.py, services/admin.py, services/forms.py
   - services/permissions.py, services/analytics.py, services/notifications.py
   - services/test_core.py
2. Status changes ONLY through `service_request.change_status(new_status, by=user, note="")`.
   Never assign `.status` directly, never use `.update(status=...)`. It raises
   `django.core.exceptions.ValidationError` on an illegal move: catch it and show the message.
3. Citizen views NEVER use `ServiceRequest.objects.all()`. Use
   `ServiceRequest.objects.for_user(request.user)`, or `get_owned_request(user, pk)` for detail pages.
4. Decorators: citizen pages use `@citizen_required`, admin-panel pages use `@staff_required`
   (both in services/permissions.py). Public pages have no decorator.
5. Function-based views. Keep them thin: validation lives in forms, rules live in models,
   counting lives in analytics.py. A view that grows past ~40 lines needs a helper.
6. Emails: call `send_submission_email(obj)` after a citizen's request is saved and
   `send_status_email(obj, update)` after `change_status()` (use the StatusUpdate it returns).
7. Stack is fixed: Django 5.2, SQLite, server-rendered templates, Bootstrap 5.3.3 (CDN),
   Bootstrap Icons 1.11.3 (CDN), Chart.js 4.4.1 (CDN, pinned version). NO Node, TypeScript,
   React, Django REST Framework, or extra pip packages. Ask before adding any dependency.
8. Build only what this file specifies. No extra features, pages, or models. Bonus work happens later and only if I ask.
9. After every successful POST: `messages.success(...)` then redirect (Post/Redirect/Get).
   Every form has `{% csrf_token %}`. Forms with an image use `enctype="multipart/form-data"`.
10. Never use `|safe` or `mark_safe` on user-supplied content. Never use raw SQL.
11. Code style: PEP 8, a one-line docstring on every view, comments explain WHY not WHAT,
    no dead code, no unused imports, no print statements, no commented-out code.
12. Tests go in `test_*.py` files. Delete the empty `tests.py` that `startapp` generates.
13. Do not run destructive commands (deleting db.sqlite3, migrations, or folders) without asking.
14. If anything in this file is ambiguous or conflicts with the code, ASK. Do not guess.

---

## 2. Project state

Existing: Django project `config`, apps `accounts` and `services`, files listed in rule 1,
`requirements.txt`. `settings.py` should already contain the block from `settings_additions.py`
(AUTH_USER_MODEL, LOGIN_URL, MEDIA, EMAIL_BACKEND, TIME_ZONE). Verify, and add whatever is missing.

To create: app `adminpanel` (staff views), `templates/`, `static/`, seed commands, view tests, README.

Model API you will use (all in services/models.py):
- `Status` (TextChoices): PENDING, IN_PROGRESS, RESOLVED. `obj.get_status_display()` gives the label.
- `ServiceRequest`: fields reference, user, category, county, area, description, image, status,
  created_at, updated_at. Related names: `user.service_requests`, `obj.history` (StatusUpdate list).
- `ServiceRequest.objects.for_user(user)`, `.open_cases()`, `.resolved()`
- `StatusUpdate`: request, old_status, new_status, changed_by, note, created_at.
- `User`: email login, `full_name`, `national_id`, `phone`, `is_staff` (staff = admin officer).

---

## 3. URL contract (names must match EXACTLY, other code already depends on them)

| URL | Name | Who | Notes |
|---|---|---|---|
| `/` | `landing` | public | what the system is, how to use it |
| `/about/` | `about` | public | static |
| `/contact/` | `contact` | public | static, placeholder contact details (replaces "support") |
| `/track/` | `track` | public | `?ref=SR-2026-0001`, privacy-safe result |
| `/register/` | `register` | anonymous | |
| `/login/` | `login` | anonymous | Django LoginView, `redirect_authenticated_user=True` |
| `/logout/` | `logout` | any | Django LogoutView, POST only, button in navbar |
| `/profile/` | `profile` | citizen | edit name/email/phone, link to password change |
| `/password-change/` | `password_change` | citizen | Django PasswordChangeView, success -> profile |
| `/dashboard/` | `dashboard` | citizen | staff are redirected to `panel:dashboard` by the decorator |
| `/requests/` | `request_list` | citizen | own requests only |
| `/requests/new/` | `request_create` | citizen | |
| `/requests/<int:pk>/` | `request_detail` | citizen | own request only, 404 otherwise |
| `/admin-panel/` | `panel:dashboard` | staff | analytics |
| `/admin-panel/requests/` | `panel:request_list` | staff | filters, search, pagination |
| `/admin-panel/requests/<int:pk>/` | `panel:request_detail` | staff | manage + change status |

`adminpanel/urls.py` sets `app_name = "panel"`. Django's built-in admin stays at `/admin/`.

---

## 4. Templates and UI

Layout: project-level `templates/` (add to `TEMPLATES["DIRS"]`), static files in `static/` (add `STATICFILES_DIRS`).

```
templates/
  base.html
  partials/_messages.html  _status_badge.html  _timeline.html  _pagination.html  _form_field.html
  public/landing.html  about.html  contact.html  track.html
  accounts/register.html  login.html  profile.html  password_change.html
  services/dashboard.html  request_list.html  request_create.html  request_detail.html
  adminpanel/dashboard.html  request_list.html  request_detail.html
static/css/site.css
```

Look and feel: government-portal style, similar in spirit to eCitizen. Clean white cards on a
light grey background, ONE primary accent colour (deep green), icon service cards on the
citizen dashboard, readable typography, generous spacing. Mobile responsive (test at 375px).

- `base.html`: navbar adapts to state. Anonymous: Login, Register. Citizen: Dashboard, My Requests,
  Report an Issue, Profile, Logout. Staff: Admin Panel, Logout. Footer. `{% block title %}` and `{% block content %}`.
  Messages partial shown under the navbar.
- Status badge (one partial, used everywhere): Pending = warning (yellow), In Progress = info (blue), Resolved = success (green).
- Timeline partial takes `history`, `show_notes`, `show_actor`. Citizen detail: notes on, actor off.
  Admin detail: notes on, actor on. Public track: notes off, actor off.
- Forms render field by field with errors under each field, plus non-field errors at the top.
- Empty states: "You have not reported anything yet" with a button, "No requests match your filters", etc.
- Tables scroll horizontally on small screens (`table-responsive`).
- Wide pages use the full container; forms sit in a centred narrow column.

---

## 5. The spec (pseudocode this project implements)

```
=== PUBLIC (no login) ===

GET /                               LANDING PAGE
  navbar: logo | About | Contact | [Login] [Register]
  hero: "Report a public service issue. Track it until it is fixed."
        [Get Started -> register]  [Track a Request -> track]
  how it works: 1 Register  2 Report an issue  3 Track until resolved
  service categories grid (active Category rows from DB, with icons)
  quick track box: enter reference no -> GET /track/?ref=...
  footer: contact details

GET /track/?ref=...                 PUBLIC TRACKING
  normalise ref (strip, upper); find by reference
  IF no ref given: show the search box only
  IF not found: show "No request found for that reference"
  ELSE show ONLY: reference, category, county, status badge, status timeline
       (no notes, no actor names)
       HIDE: description, area, image, citizen name/email/phone

=== AUTH ===

GET/POST /register/        RegistrationForm
  valid: save (citizen, is_staff False), log them in, success message, redirect dashboard
  invalid: re-render with field errors
GET/POST /login/           LoginView (email + password)
  after login everyone goes to `dashboard` (LOGIN_REDIRECT_URL);
  @citizen_required forwards staff to panel:dashboard
POST /logout/ -> landing

=== CITIZEN (login required) ===

GET /dashboard/            HOME
  greeting with short name
  summary strip from citizen_stats(user): total | pending | in progress | resolved
  service cards: [Report an Issue] [My Requests] [Track a Request] [Profile] [Contact]
  recent requests: last 5 of for_user(user) with status badges

GET/POST /requests/new/    REPORT AN ISSUE  (ReportForm, multipart)
  ON VALID POST:
     obj = form.save(commit=False); obj.user = request.user; obj.save()
     send_submission_email(obj)
     success message showing the reference number
     redirect request_detail(obj.pk)

GET /requests/             MY REQUESTS
  for_user(user), newest first, ?status= filter, paginate 10
  row: reference, category, county, date, status badge -> detail

GET /requests/<pk>/        REQUEST DETAIL
  obj = get_owned_request(request.user, pk)
  show all fields, image if present, status badge, timeline (notes on)

GET/POST /profile/         ProfileForm; national ID shown read-only; link to password change

=== ADMIN PANEL (staff only) ===

GET /admin-panel/          DASHBOARD + ANALYTICS
  stats = dashboard_stats()
  number cards: total, pending, in progress, resolved, open
  chart 1: open vs resolved (doughnut)
  chart 2: requests per category (bar), from stats["by_category"]
  pass chart data with {{ data|json_script:"id" }}, never inline JS strings
  table: 10 oldest PENDING requests (they need attention first)

GET /admin-panel/requests/ ALL REQUESTS
  GET filters: status, category, county, q (matches reference OR citizen full_name, icontains)
  select_related category, county, user; paginate 10; filters survive pagination links

GET/POST /admin-panel/requests/<pk>/   MANAGE REQUEST
  show details, image, citizen contact (name, email, phone), timeline (notes + actor on)
  form = StatusChangeForm(request.POST or None, service_request=obj)
  IF NOT form.can_change: show "This request is resolved" and no form
  ON VALID POST:
     try: update = obj.change_status(form.cleaned_data["new_status"], by=request.user,
                                     note=form.cleaned_data["note"])
     except ValidationError as e: form.add_error(None, e)
     else: send_status_email(obj, update); success message; redirect to this page
```

---

## 6. Phases

After each phase run `python manage.py check` and `python manage.py test`, then reply with:
(a) files created or changed, (b) how I verify it manually in the browser (exact clicks),
(c) anything you were unsure about, (d) a suggested git commit message. I commit myself. Then STOP.

**Phase 0: wiring and foundation**
- Create app `adminpanel`; add to INSTALLED_APPS; delete generated `tests.py` files.
- settings: TEMPLATES DIRS, STATICFILES_DIRS; confirm settings_additions values are present.
- `config/urls.py`: admin/, accounts, services, adminpanel (namespace `panel`), media serving when DEBUG.
- `templates/base.html` and all partials, `static/css/site.css` (accent colour, card styling).
- Management command `seed_reference_data` (services/management/commands/, with `__init__.py` files):
  all 47 Kenyan counties (verify the count is exactly 47) and categories: Streetlight (bi-lightbulb),
  Water (bi-droplet), Garbage Collection (bi-trash), Roads (bi-cone-striped), Drainage (bi-water),
  Other (bi-three-dots). Idempotent via get_or_create. Prints how many were created.

**Phase 1: public pages and auth**
- landing, about, contact, track. Register, login, logout, profile, password change.
- Placeholder routes/views for `dashboard` and `panel:dashboard` may be minimal stubs so redirects resolve.

**Phase 2: citizen flow**
- dashboard, request_create, request_list, request_detail, exactly per the spec.

**Phase 3: admin panel**
- panel dashboard with charts, request list with filters, request detail with status change.

**Phase 4: tests, demo data, README**
- `services/test_views.py` and `accounts/test_views.py` using Django's test Client. Cover:
  register then dashboard; login redirects (citizen -> dashboard, staff -> panel); anonymous redirected to login;
  citizen gets 404 on another citizen's request; citizen gets 403 on /admin-panel/;
  report submission creates the request, the history entry and one email;
  image upload (use SimpleUploadedFile and a temporary MEDIA_ROOT);
  staff status change works and emails; POSTing RESOLVED on a Pending request is rejected;
  public track page does NOT contain the description, citizen name or email;
  admin list filters and search.
- Management command `seed_demo`: 1 staff officer, 3 citizens, about 25 requests spread across all
  statuses and categories, created through the normal model API (create, then `change_status`).
  Idempotent: do nothing if the demo users already exist. Print the demo credentials.
- `README.md` (see section 7).
- Final cleanup: unused imports, dead code, consistent naming, `python manage.py check --deploy` notes only.

---

## 7. README requirements

Overview and screenshots placeholder; feature list mapped to the assignment requirements;
tech stack with a one-line reason for each choice; setup from a fresh clone (Windows and Mac/Linux:
venv, install, migrate, seed_reference_data, seed_demo, createsuperuser optional, runserver);
demo accounts table; URL map; project structure; the status workflow diagram; design decisions
(single `change_status` entry point, owner-scoped queries, 404 for foreign requests, public tracking
hides personal data, console email backend, SQLite now and Postgres via settings later, why server-rendered);
how to run tests; known limitations and future work. Every command must work from a fresh clone.

---

## 8. Final acceptance checklist

- [ ] Fresh clone, follow README only, app runs
- [ ] Register, log in, report with and without an image, see it Pending with a timeline
- [ ] Submission email prints in the terminal with the reference number
- [ ] Staff log in, land on the panel, filter and search, move Pending -> In Progress -> Resolved
- [ ] Status email prints each time; Resolved requests show no status form
- [ ] Open vs resolved and per-category charts match the data
- [ ] Citizen A cannot open citizen B's request (404) or any /admin-panel/ URL (403)
- [ ] Public track shows no personal data
- [ ] Looks right at 375px wide
- [ ] `python manage.py test` passes; `python manage.py check` is clean
