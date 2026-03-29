import pytest


@pytest.fixture
def group(db):
    from users.models import Group

    return Group.objects.create(name="Test Group", description="A test group")


@pytest.fixture
def membership(db, admin_user, group):
    from users.models import Membership

    return Membership.objects.create(user=admin_user, group=group, role="admin")


@pytest.fixture
def admin_user(db):
    from django.contrib.auth.models import User

    return User.objects.create_user(
        username="admin", email="admin@example.com", password="adminpass123"
    )
