from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from tournaments.models import Match, Prediction, Tournament, TournamentParticipation
from users.models import Group, Membership


class MatchListViewTests(TestCase):
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
        TournamentParticipation.objects.create(
            user=self.member_user,
            tournament=self.tournament,
            group=self.group,
            role="member",
        )
        self.match = Match.objects.create(
            tournament=self.tournament,
            home_team="Brazil",
            away_team="Argentina",
            kickoff=timezone.now() + timezone.timedelta(days=1),
        )

    def test_match_list_requires_login(self):
        response = self.client.get(
            reverse(
                "tournaments:match_list",
                kwargs={"group_id": self.group.id, "tournament_id": self.tournament.id},
            )
        )
        self.assertEqual(response.status_code, 302)

    def test_member_can_view_match_list(self):
        self.client.force_login(self.member_user)
        response = self.client.get(
            reverse(
                "tournaments:match_list",
                kwargs={"group_id": self.group.id, "tournament_id": self.tournament.id},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Brazil")
        self.assertContains(response, "Argentina")

    @patch("tournaments.views.messages")
    def test_match_list_redirects_non_member(self, mock_messages):
        other_user = User.objects.create_user(
            username="other", email="other@example.com", password="otherpass123"
        )
        self.client.force_login(other_user)
        response = self.client.get(
            reverse(
                "tournaments:match_list",
                kwargs={"group_id": self.group.id, "tournament_id": self.tournament.id},
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("index"))
        mock_messages.error.assert_called()

    def test_superuser_can_view_match_list_without_membership(self):
        superuser = User.objects.create_superuser(
            username="super", email="super@example.com", password="superpass123"
        )
        self.client.force_login(superuser)
        response = self.client.get(
            reverse(
                "tournaments:match_list",
                kwargs={"group_id": self.group.id, "tournament_id": self.tournament.id},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Brazil")

    def test_finished_match_shows_scores(self):
        Match.objects.create(
            tournament=self.tournament,
            home_team="Germany",
            away_team="Italy",
            kickoff=timezone.now() - timezone.timedelta(days=1),
            home_score=3,
            away_score=1,
            status="finished",
        )
        self.client.force_login(self.member_user)
        response = self.client.get(
            reverse(
                "tournaments:match_list",
                kwargs={"group_id": self.group.id, "tournament_id": self.tournament.id},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Germany")
        self.assertContains(response, "Italy")
        self.assertContains(response, "3&ndash;1")


class CreateMatchViewTests(TestCase):
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
            name="World Cup 2026",
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

    def _create_match_url(self):
        return reverse(
            "tournaments:create_match",
            kwargs={"group_id": self.group.id, "tournament_id": self.tournament.id},
        )

    def _match_list_url(self):
        return reverse(
            "tournaments:match_list",
            kwargs={"group_id": self.group.id, "tournament_id": self.tournament.id},
        )

    def _valid_match_data(self):
        kickoff = (timezone.now() + timezone.timedelta(days=1)).strftime(
            "%Y-%m-%dT%H:%M"
        )
        return {"home_team": "Team A", "away_team": "Team B", "kickoff": kickoff}

    def test_create_match_requires_login(self):
        response = self.client.get(self._create_match_url())
        self.assertEqual(response.status_code, 302)

    def test_get_returns_form_for_group_admin(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(self._create_match_url())
        self.assertEqual(response.status_code, 200)

    @patch("tournaments.views.messages")
    def test_post_as_group_admin_creates_match(self, mock_messages):
        self.client.force_login(self.admin_user)
        response = self.client.post(self._create_match_url(), self._valid_match_data())
        self.assertTrue(
            Match.objects.filter(
                home_team="Team A",
                away_team="Team B",
                tournament=self.tournament,
            ).exists()
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self._match_list_url())
        mock_messages.success.assert_called()

    @patch("tournaments.views.messages")
    def test_post_as_tournament_admin_creates_match(self, mock_messages):
        tour_admin = User.objects.create_user(
            username="touradmin",
            email="touradmin@example.com",
            password="touradminpass123",
        )
        Membership.objects.create(
            user=tour_admin, group=self.group, role="member"
        )
        TournamentParticipation.objects.create(
            user=tour_admin,
            tournament=self.tournament,
            group=self.group,
            role="admin",
        )
        self.client.force_login(tour_admin)
        response = self.client.post(self._create_match_url(), self._valid_match_data())
        self.assertTrue(
            Match.objects.filter(
                home_team="Team A",
                away_team="Team B",
                tournament=self.tournament,
            ).exists()
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self._match_list_url())

    @patch("tournaments.views.messages")
    def test_post_as_plain_member_denied(self, mock_messages):
        self.client.force_login(self.member_user)
        response = self.client.post(self._create_match_url(), self._valid_match_data())
        self.assertFalse(Match.objects.exists())
        self.assertEqual(response.status_code, 302)
        mock_messages.error.assert_called()

    def test_post_with_identical_team_names_rejected(self):
        self.client.force_login(self.admin_user)
        data = self._valid_match_data()
        data["home_team"] = "Same Team"
        data["away_team"] = "same team"
        response = self.client.post(self._create_match_url(), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Match.objects.exists())


class SetMatchResultViewTests(TestCase):
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
            name="World Cup 2026",
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
        self.member_participation = TournamentParticipation.objects.create(
            user=self.member_user,
            tournament=self.tournament,
            group=self.group,
            role="member",
        )
        self.match = Match.objects.create(
            tournament=self.tournament,
            home_team="Brazil",
            away_team="Argentina",
            kickoff=timezone.now() + timezone.timedelta(days=1),
        )

    def _result_url(self, match=None):
        return reverse(
            "tournaments:set_match_result",
            kwargs={
                "group_id": self.group.id,
                "tournament_id": self.tournament.id,
                "match_id": (match or self.match).id,
            },
        )

    def _match_list_url(self):
        return reverse(
            "tournaments:match_list",
            kwargs={"group_id": self.group.id, "tournament_id": self.tournament.id},
        )

    def _post_result(self, home_score, away_score, status="finished", user=None):
        self.client.force_login(user or self.admin_user)
        return self.client.post(
            self._result_url(),
            {
                "home_score": home_score,
                "away_score": away_score,
                "status": status,
            },
        )

    def _create_prediction(self, home, away, user=None):
        return Prediction.objects.create(
            user=user or self.member_user,
            match=self.match,
            tournament=self.tournament,
            predicted_home_score=home,
            predicted_away_score=away,
        )

    def test_set_result_requires_login(self):
        response = self.client.post(
            self._result_url(), {"home_score": 2, "away_score": 1, "status": "finished"}
        )
        self.assertEqual(response.status_code, 302)

    @patch("tournaments.views.messages")
    def test_group_admin_sets_result(self, mock_messages):
        response = self._post_result(2, 1)
        self.match.refresh_from_db()
        self.assertEqual(self.match.home_score, 2)
        self.assertEqual(self.match.away_score, 1)
        self.assertEqual(self.match.status, "finished")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self._match_list_url())
        mock_messages.success.assert_called()

    @patch("tournaments.views.messages")
    def test_finishing_match_settles_exact_prediction(self, mock_messages):
        prediction = self._create_prediction(2, 1)
        self._post_result(2, 1)
        prediction.refresh_from_db()
        self.member_participation.refresh_from_db()
        self.assertEqual(prediction.points_awarded, 3)
        self.assertEqual(self.member_participation.points, 3)

    @patch("tournaments.views.messages")
    def test_outcome_only_prediction_gets_one_point(self, mock_messages):
        prediction = self._create_prediction(3, 1)
        self._post_result(2, 1)
        prediction.refresh_from_db()
        self.member_participation.refresh_from_db()
        self.assertEqual(prediction.points_awarded, 1)
        self.assertEqual(self.member_participation.points, 1)

    @patch("tournaments.views.messages")
    def test_wrong_outcome_gets_zero_points(self, mock_messages):
        prediction = self._create_prediction(0, 0)
        self._post_result(2, 1)
        prediction.refresh_from_db()
        self.member_participation.refresh_from_db()
        self.assertEqual(prediction.points_awarded, 0)
        self.assertEqual(self.member_participation.points, 0)

    @patch("tournaments.views.messages")
    def test_resettling_same_result_does_not_double_count(self, mock_messages):
        prediction = self._create_prediction(2, 1)
        self._post_result(2, 1)
        self._post_result(2, 1)
        prediction.refresh_from_db()
        self.member_participation.refresh_from_db()
        self.assertEqual(prediction.points_awarded, 3)
        self.assertEqual(self.member_participation.points, 3)

    @patch("tournaments.views.messages")
    def test_changing_result_adjusts_points_by_delta(self, mock_messages):
        prediction = self._create_prediction(2, 1)
        self._post_result(2, 1)
        self._post_result(0, 3)
        prediction.refresh_from_db()
        self.member_participation.refresh_from_db()
        self.assertEqual(prediction.points_awarded, 0)
        self.assertEqual(self.member_participation.points, 0)

    @patch("tournaments.views.messages")
    def test_plain_member_cannot_set_result(self, mock_messages):
        response = self._post_result(2, 1, user=self.member_user)
        self.match.refresh_from_db()
        self.assertEqual(self.match.status, "scheduled")
        self.assertIsNone(self.match.home_score)
        self.assertIsNone(self.match.away_score)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self._match_list_url())
        mock_messages.error.assert_called()

    @patch("tournaments.views.messages")
    def test_invalid_result_finished_without_scores(self, mock_messages):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            self._result_url(), {"status": "finished"}
        )
        self.match.refresh_from_db()
        self.assertEqual(self.match.status, "scheduled")
        self.assertIsNone(self.match.home_score)
        self.assertIsNone(self.match.away_score)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self._match_list_url())
        mock_messages.error.assert_called()
