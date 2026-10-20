from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch

from tournaments.models import (
    Match,
    Prediction,
    Tournament,
    TournamentParticipation,
)
from users.models import Group, Membership


class PredictViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.member_user = User.objects.create_user(
            username="member", email="member@example.com", password="memberpass123"
        )
        self.no_part_user = User.objects.create_user(
            username="nopart", email="nopart@example.com", password="nopartpass123"
        )
        self.group = Group.objects.create(name="Test Group", description="A test group")
        Membership.objects.create(
            user=self.member_user, group=self.group, role="member"
        )
        Membership.objects.create(
            user=self.no_part_user, group=self.group, role="member"
        )
        self.tournament = Tournament.objects.create(
            name="World Cup 2026",
            description="Football world cup",
            group=self.group,
            sport_type="football",
            tournament_type="knockout",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
        )
        TournamentParticipation.objects.create(
            user=self.member_user,
            tournament=self.tournament,
            group=self.group,
            role="member",
        )
        self.match = Match.objects.create(
            tournament=self.tournament,
            home_team="Home FC",
            away_team="Away FC",
            kickoff=timezone.now() + timedelta(hours=1),
        )
        self.existing_prediction = Prediction.objects.create(
            user=self.member_user,
            match=self.match,
            tournament=self.tournament,
            predicted_home_score=1,
            predicted_away_score=0,
        )

    def _predict_url(self, match=None):
        return reverse(
            "tournaments:predict",
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

    def _fresh_match(self, **kwargs):
        defaults = {
            "tournament": self.tournament,
            "home_team": "Other FC",
            "away_team": "Rival FC",
            "kickoff": timezone.now() + timedelta(hours=2),
        }
        defaults.update(kwargs)
        return Match.objects.create(**defaults)

    def test_predict_requires_login(self):
        response = self.client.get(self._predict_url())
        self.assertEqual(response.status_code, 302)

    def test_member_with_participation_can_get_form(self):
        self.client.login(username="member", password="memberpass123")
        response = self.client.get(self._predict_url())
        self.assertEqual(response.status_code, 200)

    @patch("tournaments.views.messages")
    def test_group_member_without_participation_redirected(self, mock_messages):
        self.client.login(username="nopart", password="nopartpass123")
        response = self.client.get(self._predict_url())
        expected = reverse(
            "tournaments:tournament_detail",
            kwargs={"group_id": self.group.id, "tournament_id": self.tournament.id},
        )
        self.assertRedirects(response, expected)
        mock_messages.error.assert_called()

    @patch("tournaments.views.messages")
    def test_non_member_redirected_away(self, mock_messages):
        User.objects.create_user(
            username="other", email="other@example.com", password="otherpass123"
        )
        self.client.login(username="other", password="otherpass123")
        response = self.client.get(self._predict_url())
        expected = reverse("index")
        self.assertRedirects(response, expected)
        mock_messages.error.assert_called()

    def test_post_places_prediction(self):
        self.client.login(username="member", password="memberpass123")
        fresh_match = self._fresh_match()
        response = self.client.post(
            self._predict_url(fresh_match),
            {"predicted_home_score": 2, "predicted_away_score": 1},
        )
        self.assertRedirects(response, self._match_list_url())
        self.assertTrue(
            Prediction.objects.filter(
                user=self.member_user,
                match=fresh_match,
                tournament=self.tournament,
                predicted_home_score=2,
                predicted_away_score=1,
            ).exists()
        )

    def test_post_updates_existing_prediction(self):
        self.client.login(username="member", password="memberpass123")
        response = self.client.post(
            self._predict_url(),
            {"predicted_home_score": 3, "predicted_away_score": 2},
        )
        self.assertRedirects(response, self._match_list_url())
        self.existing_prediction.refresh_from_db()
        self.assertEqual(self.existing_prediction.predicted_home_score, 3)
        self.assertEqual(self.existing_prediction.predicted_away_score, 2)
        self.assertEqual(
            Prediction.objects.filter(
                user=self.member_user, match=self.match
            ).count(),
            1,
        )

    @patch("tournaments.views.messages")
    def test_post_rejected_after_kickoff(self, mock_messages):
        past_match = self._fresh_match(kickoff=timezone.now() - timedelta(hours=1))
        self.client.login(username="member", password="memberpass123")
        response = self.client.post(
            self._predict_url(past_match),
            {"predicted_home_score": 2, "predicted_away_score": 1},
        )
        self.assertRedirects(response, self._match_list_url())
        mock_messages.warning.assert_called()
        self.assertFalse(
            Prediction.objects.filter(
                user=self.member_user, match=past_match
            ).exists()
        )

    @patch("tournaments.views.messages")
    def test_post_rejected_on_finished_match(self, mock_messages):
        finished_match = self._fresh_match(
            kickoff=timezone.now() - timedelta(hours=2),
            status="finished",
            home_score=1,
            away_score=0,
        )
        self.client.login(username="member", password="memberpass123")
        response = self.client.post(
            self._predict_url(finished_match),
            {"predicted_home_score": 2, "predicted_away_score": 1},
        )
        self.assertRedirects(response, self._match_list_url())
        mock_messages.warning.assert_called()
        self.assertFalse(
            Prediction.objects.filter(
                user=self.member_user, match=finished_match
            ).exists()
        )

    @patch("tournaments.views.messages")
    def test_editing_after_kickoff_rejected(self, mock_messages):
        self.match.kickoff = timezone.now() - timedelta(hours=1)
        self.match.save()
        self.client.login(username="member", password="memberpass123")
        response = self.client.post(
            self._predict_url(),
            {"predicted_home_score": 9, "predicted_away_score": 9},
        )
        self.assertRedirects(response, self._match_list_url())
        mock_messages.warning.assert_called()
        self.existing_prediction.refresh_from_db()
        self.assertEqual(self.existing_prediction.predicted_home_score, 1)
        self.assertEqual(self.existing_prediction.predicted_away_score, 0)
        self.assertEqual(
            Prediction.objects.filter(
                user=self.member_user, match=self.match
            ).count(),
            1,
        )
