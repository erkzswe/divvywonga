import pytest


@pytest.fixture
def admin_user(db):
    from django.contrib.auth.models import User

    return User.objects.create_user(
        username="admin", email="admin@example.com", password="adminpass123"
    )


@pytest.fixture
def member_user(db):
    from django.contrib.auth.models import User

    return User.objects.create_user(
        username="member", email="member@example.com", password="memberpass123"
    )


@pytest.fixture
def group(db):
    from users.models import Group

    return Group.objects.create(name="Test Group", description="A test group")


@pytest.fixture
def group_with_members(db, admin_user, member_user, group):
    from users.models import Membership

    Membership.objects.create(user=admin_user, group=group, role="admin")
    Membership.objects.create(user=member_user, group=group, role="member")
    return group
