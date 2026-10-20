# DivvyWonga - AI Coding Agent Instructions

You are an expert Django developer working on DivvyWonga, a group expenses management application.

## Tech Stack

- **Framework:** Django 5.2.4
- **Python:** 3.13
- **Database:** SQLite3 (configurable via `DATABASE_PATH` env var)
- **Frontend:** Bootstrap 5 (Bootswatch "morph" theme), Bootstrap Icons
- **Forms:** Django Crispy Forms with Bootstrap 5 template pack
- **Rich Text:** django-tinymce
- **Testing:** pytest, pytest-django, pytest-cov
- **Linting:** ruff

## Project Structure

```
divvywonga/                      # Django project root (manage.py lives here)
├── core/                        # Core app (homepage, nav) + Django settings
│   ├── settings.py              # All configuration (module: core.settings)
│   ├── views.py                 # Index view
│   ├── templatetags/            # Custom template tags (ascii_art.py)
│   ├── templates/core/          # Templates
│   │   ├── base.html            # Base template
│   │   ├── index.html           # Homepage
│   │   ├── nav.html             # Navigation
│   │   └── components/          # Reusable partials
│   └── static/css/              # Custom CSS
├── divvywonga/                  # Project package
│   ├── urls.py                  # Root URL routing (includes tournaments.urls)
│   ├── wsgi.py                  # WSGI application
│   └── asgi.py                  # ASGI application
├── users/                       # Users & groups app
│   ├── models.py                # Group, Membership models
│   ├── views.py                 # All group views
│   ├── forms.py                 # User forms
│   ├── urls.py                  # User URL patterns
│   └── templates/users/         # User templates
├── tournaments/                 # Tournaments app (app_name = "tournaments")
│   ├── models.py                # Tournament, TournamentParticipation, Match, Prediction models
│   ├── views.py                 # Tournament views
│   ├── forms.py                 # Tournament create/invite forms
│   ├── urls.py                  # Namespaced URL patterns (tournaments:*)
│   ├── services.py              # Betting/scoring logic (score_prediction, settle_match)
│   └── templates/tournaments/   # Tournament templates
└── manage.py
tests/                           # External test suite (pytest, not in-app tests)
├── conftest.py
├── core/                        # tests/core/
├── users/                       # tests/users/
├── tournaments/                 # tests/tournaments/
└── integration/                 # tests/integration/
pytest.ini                       # testpaths=tests, pythonpath=divvywonga,
                                 # DJANGO_SETTINGS_MODULE=core.settings
```

- Settings module is `divvywonga/core/settings.py` (imported as `core.settings`).
- Tests live in the top-level `tests/` directory (pytest). The old in-app
  `tests.py` / `tests/` dirs are no longer used.

## Commands

Run all tests (canonical, from repo root):
```bash
source .venv/bin/activate && python -m pytest
```

Run a subset of tests:
```bash
source .venv/bin/activate && python -m pytest tests/tournaments -q
```
Note: `python manage.py test ...` is not used — pytest is the only test runner.

Run linter:
```bash
source .venv/bin/activate && ruff check
```

Run Django system check:
```bash
cd divvywonga && source ../.venv/bin/activate && python manage.py check
```

## Code Conventions

### Python
- Use Django class-based views (`View`, `TemplateView`, `CreateView`, etc.)
- Always use `LoginRequiredMixin` for views requiring authentication
- Use `select_related()` for foreign key queries to avoid N+1 problems
- Import order: stdlib → Django → third-party → local

### Templates
- Use `{% load static %}` in templates that need static files
- Custom template tags go in `core/templatetags/`
- Template partials go in `core/templates/core/components/`
- Bootstrap 5 classes for styling

### Models (users/models.py)
- **Group:** name, description, is_active, created_at, updated_at
- **Membership:** user (FK), group (FK), points (0-10000), joined_at, is_active, role (admin/moderator/member)
- Access user groups via `request.user.membership_set.select_related("group")`

### Models (tournaments/models.py)
- **Tournament:** name, description, group (FK, related_name="tournaments"), sport_type, tournament_type, start_date, end_date, is_active, created_at, updated_at; unique together name+group
- **TournamentParticipation:** user (FK), tournament (FK), group (FK), points (0-10000), joined_at, is_active, role (admin/moderator/member/predictor); unique together user+tournament
- **Match:** tournament (FK, related_name="matches"), home_team, away_team, kickoff, home_score/away_score (nullable), status (scheduled/finished/cancelled); `clean()` enforces scores iff finished; `is_predictable()` returns True if scheduled and kickoff not passed; `get_outcome()` returns home/draw/away or None.
- **Prediction:** user (FK), match (FK, related_name="predictions"), tournament (FK, denormalized), predicted_home_score, predicted_away_score, points_awarded, created_at/updated_at; unique together (user, match).
- Access tournaments via `group.tournaments` and participants via `tournament.tournamentparticipation_set`

### Tournaments
- Permission pattern: views check group-role OR tournament-role (e.g. group admin/moderator OR tournament admin/moderator), with superuser bypass (`request.user.is_superuser`)
- Creating a tournament also creates the creator's `TournamentParticipation` with `role="admin"` in the same transaction
- Tournament invites require the invitee to already be an active member of the group; non-members are skipped with a warning
- **Betting:** scoring lives in `tournaments/services.py` (score_prediction: exact=3, outcome=1; settle_match: idempotent delta-based, called when a match result is set to finished); predictions lock at kickoff (`Match.is_predictable()`); PredictView requires active TournamentParticipation.

### URL Naming
| URL | Name |
|-----|------|
| `/` | index |
| `/login/` | login |
| `/logout/` | logout |
| `/register/` | register |
| `/groups/` | groups |
| `/groups/create/` | create_group |
| `/groups/<id>/` | group_detail |
| `/groups/<id>/delete/` | delete_group |
| `/groups/<id>/leave/` | leave_group |
| `/groups/<id>/invite/` | invite_to_group |
| `/groups/<id>/tournaments/` | tournaments:group_tournaments |
| `/groups/<id>/tournaments/create/` | tournaments:create_tournament |
| `/groups/<id>/tournaments/<id>/` | tournaments:tournament_detail |
| `/groups/<id>/tournaments/<id>/delete/` | tournaments:delete_tournament |
| `/groups/<id>/tournaments/<id>/leave/` | tournaments:leave_tournament |
| `/groups/<id>/tournaments/<id>/invite/` | tournaments:invite_to_tournament |
| `/groups/<id>/tournaments/<id>/matches/` | tournaments:match_list |
| `/groups/<id>/tournaments/<id>/matches/create/` | tournaments:create_match |
| `/groups/<id>/tournaments/<id>/matches/<mid>/result/` | tournaments:set_match_result |
| `/groups/<id>/tournaments/<id>/matches/<mid>/predict/` | tournaments:predict |

## Three-Tier Boundaries

### Always Do
- Run `python manage.py check` after modifying settings or URLs
- Run tests after any model, view, or template changes
- Use `select_related()` on foreign key queries
- Use `LoginRequiredMixin` for authenticated views
- Use `{% load static %}` in templates that reference static files
- Run `ruff check` before committing

### Ask First
- Modifying `settings.py` configuration
- Adding new dependencies to `pyproject.toml`
- Changing URL patterns
- Modifying authentication flow
- Database schema changes (model modifications)

### Never Do
- Commit secrets, API keys, or credentials to the repository
- Modify the `node_modules/` or `.venv/` directories
- Delete test files or modify test assertions
- Hardcode database paths outside of environment variables
- Modify the `db.sqlite3` file directly

## Code Examples

### Correct: View with user groups query
```python
class Index(LoginRequiredMixin, View):
    def get(self, request):
        user_groups = (
            request.user.membership_set
            .select_related("group")
            .filter(is_active=True)
            .order_by("-joined_at")
        )
        return render(request, "core/index.html", {"user_groups": user_groups})
```

### Wrong: Missing select_related (N+1 query)
```python
def get(self, request):
    user_groups = request.user.membership_set.filter(is_active=True)
    return render(request, "core/index.html", {"user_groups": user_groups})
```

### Correct: Template with static files
```django
{% extends 'core/base.html' %}
{% load static %}
{% load ascii_art %}

{% block content %}
<link rel="stylesheet" href="{% static 'css/homepage.css' %}">
{% endblock %}
```

### Wrong: Missing load static
```django
{% extends 'core/base.html' %}
<link rel="stylesheet" href="{% static 'css/homepage.css' %}">
```

## Testing Guidelines

- All view tests must login the user first when using `LoginRequiredMixin`
- Use `assertContains(response, ...)` for template content
- Test both authenticated and anonymous access patterns
- Group-related tests need both admin and member users

## Git Workflow

- Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`
- Example: `feat: add user profile page`
- Always run tests before pushing
- Never commit to main directly

## Maintenance

Update this file when:
- New dependencies are added
- URL patterns change
- Directory structure changes
- New conventions are established
