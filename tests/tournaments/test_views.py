from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch
from users.models import Group, Membership
from tournaments.models import Tournament, TournamentParticipation


class TournamentViewTests(TestCase):
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
        self.tournament = Tournament.objects.create(
            name="World Cup 2026",
            description="Football world cup",
            group=self.group,
            sport_type="football",
            tournament_type="knockout",
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=30),
        )
        TournamentParticipation.objects.create(
            user=self.admin_user,
            tournament=self.tournament,
            group=self.group,
            role="admin",
        )

    def test_tournament_list_requires_login(self):
        response = self.client.get(
            reverse("tournaments:group_tournaments", kwargs={"group_id": self.group.id})
        )
        self.assertEqual(response.status_code, 302)

    def test_tournament_list_returns_200_for_member(self):
        self.client.login(username="member", password="memberpass123")
        response = self.client.get(
            reverse("tournaments:group_tournaments", kwargs={"group_id": self.group.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "World Cup 2026")

    def test_tournament_list_redirects_non_member(self):
        User.objects.create_user(
            username="other", email="other@example.com", password="otherpass123"
        )
        self.client.login(username="other", password="otherpass123")
        response = self.client.get(
            reverse("tournaments:group_tournaments", kwargs={"group_id": self.group.id})
        )
        self.assertEqual(response.status_code, 302)


class CreateTournamentViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username="admin", email="admin@example.com", password="adminpass123"
        )
        self.group = Group.objects.create(name="Test Group")
        Membership.objects.create(user=self.admin_user, group=self.group, role="admin")

    def test_create_tournament_requires_login(self):
        response = self.client.get(
            reverse("tournaments:create_tournament", kwargs={"group_id": self.group.id})
        )
        self.assertEqual(response.status_code, 302)

    def test_create_tournament_get_returns_form(self):
        self.client.login(username="admin", password="adminpass123")
        response = self.client.get(
            reverse("tournaments:create_tournament", kwargs={"group_id": self.group.id})
        )
        self.assertEqual(response.status_code, 200)

    @patch("tournaments.views.messages")
    def test_create_tournament_post_creates_tournament(self, mock_messages):
        self.client.login(username="admin", password="adminpass123")
        start_date = timezone.now().strftime("%Y-%m-%dT%H:%M")
        end_date = (timezone.now() + timezone.timedelta(days=7)).strftime(
            "%Y-%m-%dT%H:%M"
        )
        self.client.post(
            reverse(
                "tournaments:create_tournament", kwargs={"group_id": self.group.id}
            ),
            {
                "name": "Euro 2028",
                "description": "European Championship",
                "sport_type": "football",
                "tournament_type": "league",
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        self.assertTrue(Tournament.objects.filter(name="Euro 2028").exists())
        tournament = Tournament.objects.get(name="Euro 2028")
        self.assertTrue(
            TournamentParticipation.objects.filter(
                user=self.admin_user, tournament=tournament, role="admin"
            ).exists()
        )

    def test_create_tournament_redirects_non_member(self):
        User.objects.create_user(
            username="other", email="other@example.com", password="otherpass123"
        )
        self.client.login(username="other", password="otherpass123")
        response = self.client.get(
            reverse("tournaments:create_tournament", kwargs={"group_id": self.group.id})
        )
        self.assertEqual(response.status_code, 302)


class TournamentDetailViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username="admin", email="admin@example.com", password="adminpass123"
        )
        self.member_user = User.objects.create_user(
            username="member", email="member@example.com", password="memberpass123"
        )
        self.group = Group.objects.create(name="Test Group")
        Membership.objects.create(user=self.admin_user, group=self.group, role="admin")
        Membership.objects.create(
            user=self.member_user, group=self.group, role="member"
        )
        self.tournament = Tournament.objects.create(
            name="World Cup",
            group=self.group,
            sport_type="football",
            tournament_type="knockout",
            start_date=timezone.now(),
        )
        TournamentParticipation.objects.create(
            user=self.admin_user,
            tournament=self.tournament,
            group=self.group,
            role="admin",
        )
        TournamentParticipation.objects.create(
            user=self.member_user,
            tournament=self.tournament,
            group=self.group,
            role="member",
            points=50,
        )

    def test_tournament_detail_returns_200_for_member(self):
        self.client.login(username="member", password="memberpass123")
        response = self.client.get(
            reverse(
                "tournaments:tournament_detail",
                kwargs={"group_id": self.group.id, "tournament_id": self.tournament.id},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "World Cup")

    def test_tournament_detail_shows_participants(self):
        self.client.login(username="admin", password="adminpass123")
        response = self.client.get(
            reverse(
                "tournaments:tournament_detail",
                kwargs={"group_id": self.group.id, "tournament_id": self.tournament.id},
            )
        )
        self.assertContains(response, "admin")
        self.assertContains(response, "member")
        self.assertContains(response, "50")

    def test_tournament_detail_requires_login(self):
        response = self.client.get(
            reverse(
                "tournaments:tournament_detail",
                kwargs={"group_id": self.group.id, "tournament_id": self.tournament.id},
            )
        )
        self.assertEqual(response.status_code, 302)

    def test_tournament_detail_redirects_non_member(self):
        User.objects.create_user(
            username="nonmember2", email="nonmember2@example.com", password="pass123"
        )
        self.client.login(username="nonmember2", password="pass123")
        response = self.client.get(
            reverse(
                "tournaments:tournament_detail",
                kwargs={"group_id": self.group.id, "tournament_id": self.tournament.id},
            )
        )
        self.assertEqual(response.status_code, 302)


class DeleteTournamentViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username="admin", email="admin@example.com", password="adminpass123"
        )
        self.member_user = User.objects.create_user(
            username="member", email="member@example.com", password="memberpass123"
        )
        self.group = Group.objects.create(name="Test Group")
        Membership.objects.create(user=self.admin_user, group=self.group, role="admin")
        self.tournament = Tournament.objects.create(
            name="To Delete",
            group=self.group,
            sport_type="football",
            tournament_type="league",
            start_date=timezone.now(),
        )
        TournamentParticipation.objects.create(
            user=self.admin_user,
            tournament=self.tournament,
            group=self.group,
            role="admin",
        )

    def test_delete_tournament_requires_login(self):
        response = self.client.post(
            reverse(
                "tournaments:delete_tournament",
                kwargs={"group_id": self.group.id, "tournament_id": self.tournament.id},
            )
        )
        self.assertEqual(response.status_code, 302)

    def test_delete_tournament_requires_admin(self):
        self.client.login(username="member", password="memberpass123")
        response = self.client.post(
            reverse(
                "tournaments:delete_tournament",
                kwargs={"group_id": self.group.id, "tournament_id": self.tournament.id},
            )
        )
        self.assertEqual(response.status_code, 302)

    def test_delete_tournament_admin_can_delete(self):
        self.client.login(username="admin", password="adminpass123")
        tournament_id = self.tournament.id
        self.client.post(
            reverse(
                "tournaments:delete_tournament",
                kwargs={"group_id": self.group.id, "tournament_id": tournament_id},
            )
        )
        self.assertFalse(Tournament.objects.filter(id=tournament_id).exists())

    def test_delete_tournament_group_admin_can_delete(self):
        user2 = User.objects.create_user(
            username="groupadmin",
            email="groupadmin@example.com",
            password="groupadminpass123",
        )
        Membership.objects.create(user=user2, group=self.group, role="admin")
        self.client.login(username="groupadmin", password="groupadminpass123")
        tournament_id = self.tournament.id
        self.client.post(
            reverse(
                "tournaments:delete_tournament",
                kwargs={"group_id": self.group.id, "tournament_id": tournament_id},
            )
        )
        self.assertFalse(Tournament.objects.filter(id=tournament_id).exists())


class LeaveTournamentViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username="admin", email="admin@example.com", password="adminpass123"
        )
        self.member_user = User.objects.create_user(
            username="member", email="member@example.com", password="memberpass123"
        )
        self.group = Group.objects.create(name="Test Group")
        Membership.objects.create(user=self.admin_user, group=self.group, role="admin")
        Membership.objects.create(
            user=self.member_user, group=self.group, role="member"
        )
        self.tournament = Tournament.objects.create(
            name="Test Tournament",
            group=self.group,
            sport_type="football",
            tournament_type="league",
            start_date=timezone.now(),
        )
        TournamentParticipation.objects.create(
            user=self.admin_user,
            tournament=self.tournament,
            group=self.group,
            role="admin",
        )
        TournamentParticipation.objects.create(
            user=self.member_user,
            tournament=self.tournament,
            group=self.group,
            role="member",
        )

    def test_leave_tournament_requires_login(self):
        response = self.client.post(
            reverse(
                "tournaments:leave_tournament",
                kwargs={"group_id": self.group.id, "tournament_id": self.tournament.id},
            )
        )
        self.assertEqual(response.status_code, 302)

    def test_member_can_leave_tournament(self):
        self.client.login(username="member", password="memberpass123")
        self.client.post(
            reverse(
                "tournaments:leave_tournament",
                kwargs={"group_id": self.group.id, "tournament_id": self.tournament.id},
            )
        )
        self.assertFalse(
            TournamentParticipation.objects.filter(
                user=self.member_user, tournament=self.tournament
            ).exists()
        )

    def test_last_admin_cannot_leave(self):
        self.client.login(username="admin", password="adminpass123")
        self.client.post(
            reverse(
                "tournaments:leave_tournament",
                kwargs={"group_id": self.group.id, "tournament_id": self.tournament.id},
            )
        )
        self.assertTrue(
            TournamentParticipation.objects.filter(
                user=self.admin_user, tournament=self.tournament
            ).exists()
        )


class InviteToTournamentViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username="admin", email="admin@example.com", password="adminpass123"
        )
        self.group_member = User.objects.create_user(
            username="groupmember",
            email="groupmember@example.com",
            password="groupmemberpass123",
        )
        self.group = Group.objects.create(name="Test Group")
        Membership.objects.create(user=self.admin_user, group=self.group, role="admin")
        Membership.objects.create(
            user=self.group_member, group=self.group, role="member"
        )
        self.tournament = Tournament.objects.create(
            name="Test Tournament",
            group=self.group,
            sport_type="football",
            tournament_type="league",
            start_date=timezone.now(),
        )
        TournamentParticipation.objects.create(
            user=self.admin_user,
            tournament=self.tournament,
            group=self.group,
            role="admin",
        )

    def test_invite_get_requires_login(self):
        response = self.client.get(
            reverse(
                "tournaments:invite_to_tournament",
                kwargs={"group_id": self.group.id, "tournament_id": self.tournament.id},
            )
        )
        self.assertEqual(response.status_code, 302)

    def test_invite_get_returns_form(self):
        self.client.login(username="admin", password="adminpass123")
        response = self.client.get(
            reverse(
                "tournaments:invite_to_tournament",
                kwargs={"group_id": self.group.id, "tournament_id": self.tournament.id},
            )
        )
        self.assertEqual(response.status_code, 200)

    @patch("tournaments.views.messages")
    def test_invite_post_adds_participant(self, mock_messages):
        self.client.login(username="admin", password="adminpass123")
        self.client.post(
            reverse(
                "tournaments:invite_to_tournament",
                kwargs={"group_id": self.group.id, "tournament_id": self.tournament.id},
            ),
            {"emails": "groupmember@example.com", "role": "member"},
        )
        self.assertTrue(
            TournamentParticipation.objects.filter(
                user=self.group_member, tournament=self.tournament
            ).exists()
        )

    @patch("tournaments.views.messages")
    def test_invite_non_group_member_shows_warning(self, mock_messages):
        User.objects.create_user(
            username="nonmember",
            email="nonmember@example.com",
            password="nonmemberpass123",
        )
        self.client.login(username="admin", password="adminpass123")
        self.client.post(
            reverse(
                "tournaments:invite_to_tournament",
                kwargs={"group_id": self.group.id, "tournament_id": self.tournament.id},
            ),
            {"emails": "nonmember@example.com", "role": "member"},
        )
        mock_messages.warning.assert_called()

    def test_invite_requires_group_admin_or_tournament_admin(self):
        self.client.login(username="groupmember", password="groupmemberpass123")
        response = self.client.get(
            reverse(
                "tournaments:invite_to_tournament",
                kwargs={"group_id": self.group.id, "tournament_id": self.tournament.id},
            )
        )
        self.assertEqual(response.status_code, 302)
