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
divvywonga/
├── divvywonga/              # Django project settings
│   ├── settings.py          # All configuration
│   ├── urls.py              # Root URL routing
│   ├── wsgi.py              # WSGI application
│   ├── core/                # Core app (homepage, nav)
│   │   ├── views.py         # Index view
│   │   ├── tests.py         # All tests
│   │   ├── templatetags/    # Custom template tags (ascii_art.py)
│   │   ├── templates/core/  # Templates
│   │   │   ├── base.html    # Base template
│   │   │   ├── index.html   # Homepage
│   │   │   ├── nav.html     # Navigation
│   │   │   └── components/  # Reusable partials
│   │   └── static/css/      # Custom CSS
│   └── users/               # Users & groups app
│       ├── models.py         # Group, Membership models
│       ├── views.py          # All group views
│       ├── forms.py          # User forms
│       ├── urls.py           # User URL patterns
│       └── templates/users/  # User templates
└── core/                    # Symlink/source for core app (legacy)
```

## Commands

Run all tests:
```bash
cd divvywonga && source ../.venv/bin/activate && python manage.py test core.tests
```

Run tests with pytest:
```bash
source .venv/bin/activate && python -m pytest
```

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
