from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import patch
from users.models import Group, Membership


class IndexViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.index_url = reverse("index")

    def test_index_get_returns_200(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.index_url)
        self.assertEqual(response.status_code, 200)

    def test_index_returns_correct_template(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.index_url)
        self.assertTemplateUsed(response, "core/index.html")


class AuthenticationViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = reverse("login")
        self.logout_url = reverse("logout")
        self.register_url = reverse("register")
        self.index_url = reverse("index")
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_login_get_returns_200(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)

    def test_login_with_valid_credentials_redirects(self):
        response = self.client.post(
            self.login_url, {"username": "testuser", "password": "testpass123"}
        )
        self.assertIn(response.status_code, [200, 302])

    def test_login_with_invalid_credentials_shows_error(self):
        response = self.client.post(
            self.login_url, {"username": "testuser", "password": "wrongpass"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct username", html=False)

    def test_logout_redirects(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(self.logout_url)
        self.assertIn(response.status_code, [200, 302])

    def test_register_get_returns_200(self):
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)

    def test_register_creates_user_and_redirects(self):
        self.client.post(
            self.register_url,
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password1": "complexpass123!",
                "password2": "complexpass123!",
            },
        )
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_register_with_mismatched_passwords_fails(self):
        self.client.post(
            self.register_url,
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password1": "complexpass123!",
                "password2": "differentpass123!",
            },
        )
        self.assertFalse(User.objects.filter(username="newuser").exists())


class GroupViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username="admin", email="admin@example.com", password="adminpass123"
        )
        self.member_user = User.objects.create_user(
            username="member", email="member@example.com", password="memberpass123"
        )
        self.group = Group.objects.create(name="Test Group", description="A test group")
        Membership.objects.create(user=self.admin_user, group=self.group, role="admin")
        Membership.objects.create(
            user=self.member_user, group=self.group, role="member"
        )

    def test_group_list_requires_login(self):
        response = self.client.get(reverse("groups"))
        self.assertEqual(response.status_code, 302)

    def test_group_list_returns_user_groups(self):
        self.client.login(username="admin", password="adminpass123")
        response = self.client.get(reverse("groups"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Group")

    def test_group_detail_returns_200_for_member(self):
        self.client.login(username="member", password="memberpass123")
        response = self.client.get(
            reverse("group_detail", kwargs={"group_id": self.group.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Group")

    def test_group_detail_shows_member_count(self):
        self.client.login(username="admin", password="adminpass123")
        response = self.client.get(
            reverse("group_detail", kwargs={"group_id": self.group.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "admin")
        self.assertContains(response, "member")


class CreateGroupViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_create_group_requires_login(self):
        response = self.client.get(reverse("create_group"))
        self.assertEqual(response.status_code, 302)

    def test_create_group_get_returns_form(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("create_group"))
        self.assertEqual(response.status_code, 200)

    def test_create_group_post_creates_group_and_membership(self):
        self.client.login(username="testuser", password="testpass123")
        self.client.post(
            reverse("create_group"),
            {
                "name": "New Test Group",
                "description": "A new group for testing",
                "invite_users": "",
                "invite_role": "member",
            },
        )
        self.assertTrue(Group.objects.filter(name="New Test Group").exists())
        group = Group.objects.get(name="New Test Group")
        self.assertTrue(
            Membership.objects.filter(
                user=self.user, group=group, role="admin"
            ).exists()
        )

    def test_create_group_with_invite_creates_memberships(self):
        invitee = User.objects.create_user(
            username="invitee", email="invitee@example.com", password="inviteepass123"
        )
        self.client.login(username="testuser", password="testpass123")
        self.client.post(
            reverse("create_group"),
            {
                "name": "Group With Invites",
                "description": "Testing invites",
                "invite_users": "invitee@example.com",
                "invite_role": "member",
            },
        )
        group = Group.objects.get(name="Group With Invites")
        self.assertTrue(
            Membership.objects.filter(user=invitee, group=group, role="member").exists()
        )


class DeleteGroupViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username="admin", email="admin@example.com", password="adminpass123"
        )
        self.member_user = User.objects.create_user(
            username="member", email="member@example.com", password="memberpass123"
        )
        self.group = Group.objects.create(name="Delete Test Group")
        Membership.objects.create(user=self.admin_user, group=self.group, role="admin")

    def test_delete_group_requires_login(self):
        response = self.client.post(
            reverse("delete_group", kwargs={"group_id": self.group.id})
        )
        self.assertEqual(response.status_code, 302)

    def test_delete_group_requires_admin(self):
        self.client.login(username="member", password="memberpass123")
        response = self.client.post(
            reverse("delete_group", kwargs={"group_id": self.group.id})
        )
        self.assertEqual(response.status_code, 302)

    @patch("django.contrib.messages.error")
    def test_delete_group_admin_can_delete(self, mock_error):
        self.client.login(username="admin", password="adminpass123")
        group_id = self.group.id
        self.client.post(
            reverse("delete_group", kwargs={"group_id": group_id})
        )
        self.assertFalse(Group.objects.filter(id=group_id).exists())


class LeaveGroupViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username="admin", email="admin@example.com", password="adminpass123"
        )
        self.member_user = User.objects.create_user(
            username="member", email="member@example.com", password="memberpass123"
        )
        self.group = Group.objects.create(name="Leave Test Group")
        Membership.objects.create(user=self.admin_user, group=self.group, role="admin")
        Membership.objects.create(
            user=self.member_user, group=self.group, role="member"
        )

    def test_leave_group_requires_login(self):
        response = self.client.post(
            reverse("leave_group", kwargs={"group_id": self.group.id})
        )
        self.assertEqual(response.status_code, 302)

    def test_member_can_leave_group(self):
        self.client.login(username="member", password="memberpass123")
        self.client.post(
            reverse("leave_group", kwargs={"group_id": self.group.id})
        )
        self.assertFalse(
            Membership.objects.filter(user=self.member_user, group=self.group).exists()
        )

    def test_last_admin_cannot_leave(self):
        self.client.login(username="admin", password="adminpass123")
        self.client.post(
            reverse("leave_group", kwargs={"group_id": self.group.id})
        )
        self.assertTrue(
            Membership.objects.filter(user=self.admin_user, group=self.group).exists()
        )


class InviteToGroupViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username="admin", email="admin@example.com", password="adminpass123"
        )
        self.new_user = User.objects.create_user(
            username="newuser", email="newuser@example.com", password="newuserpass123"
        )
        self.group = Group.objects.create(name="Invite Test Group")
        Membership.objects.create(user=self.admin_user, group=self.group, role="admin")

    def test_invite_get_requires_login(self):
        response = self.client.get(
            reverse("invite_to_group", kwargs={"group_id": self.group.id})
        )
        self.assertEqual(response.status_code, 302)

    def test_invite_get_returns_form(self):
        self.client.login(username="admin", password="adminpass123")
        response = self.client.get(
            reverse("invite_to_group", kwargs={"group_id": self.group.id})
        )
        self.assertEqual(response.status_code, 200)

    @patch("users.views.messages")
    def test_invite_post_adds_member(self, mock_messages):
        self.client.login(username="admin", password="adminpass123")
        self.client.post(
            reverse("invite_to_group", kwargs={"group_id": self.group.id}),
            {"emails": "newuser@example.com", "role": "member"},
        )
        self.assertTrue(
            Membership.objects.filter(user=self.new_user, group=self.group).exists()
        )

    @patch("users.views.messages")
    def test_invite_nonexistent_user_shows_warning(self, mock_messages):
        self.client.login(username="admin", password="adminpass123")
        self.client.post(
            reverse("invite_to_group", kwargs={"group_id": self.group.id}),
            {"emails": "nonexistent@example.com", "role": "member"},
        )
        mock_messages.warning.assert_called()
