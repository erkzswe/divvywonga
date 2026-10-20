from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from tournaments.models import (
    Match,
    Prediction,
    Tournament,
    TournamentParticipation,
)
from tournaments.services import (
    POINTS_EXACT,
    POINTS_OUTCOME,
    score_prediction,
    settle_match,
)
from users.models import Group, Membership


class ScorePredictionTests(TestCase):
    def test_exact_score_returns_exact_points(self):
        self.assertEqual(score_prediction(2, 1, 2, 1), POINTS_EXACT)
        self.assertEqual(score_prediction(2, 1, 2, 1), 3)

    def test_correct_home_win_outcome_returns_outcome_points(self):
        self.assertEqual(score_prediction(2, 0, 3, 1), POINTS_OUTCOME)
        self.assertEqual(score_prediction(2, 0, 3, 1), 1)

    def test_correct_draw_outcome_returns_outcome_points(self):
        self.assertEqual(score_prediction(1, 1, 2, 2), POINTS_OUTCOME)

    def test_correct_away_win_outcome_returns_outcome_points(self):
        self.assertEqual(score_prediction(0, 1, 1, 3), POINTS_OUTCOME)

    def test_wrong_outcome_returns_zero(self):
        self.assertEqual(score_prediction(2, 1, 1, 2), 0)
        self.assertEqual(score_prediction(0, 0, 2, 1), 0)
        self.assertEqual(score_prediction(1, 2, 2, 1), 0)

    def test_exact_zero_zero_draw_returns_exact_points(self):
        self.assertEqual(score_prediction(0, 0, 0, 0), POINTS_EXACT)


class SettleMatchTests(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name="Test Group", description="A test group")
        self.tournament = Tournament.objects.create(
            name="World Cup 2026",
            description="Football world cup",
            group=self.group,
            sport_type="football",
            tournament_type="knockout",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
        )
        self.user_a = User.objects.create_user(
            username="usera", email="usera@example.com", password="pass123"
        )
        self.user_b = User.objects.create_user(
            username="userb", email="userb@example.com", password="pass123"
        )
        self.user_c = User.objects.create_user(
            username="userc", email="userc@example.com", password="pass123"
        )
        for user in (self.user_a, self.user_b, self.user_c):
            Membership.objects.create(user=user, group=self.group, role="member")
            TournamentParticipation.objects.create(
                user=user,
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

    def _finish_match(self, home_score, away_score):
        self.match.status = "finished"
        self.match.home_score = home_score
        self.match.away_score = away_score
        self.match.save()

    def _make_prediction(self, user, home, away, tournament=None):
        return Prediction.objects.create(
            user=user,
            match=self.match,
            tournament=tournament or self.tournament,
            predicted_home_score=home,
            predicted_away_score=away,
        )

    def _participation(self, user):
        return TournamentParticipation.objects.get(
            user=user, tournament=self.tournament
        )

    def test_settle_raises_when_match_not_finished(self):
        with self.assertRaises(ValueError):
            settle_match(self.match)

    def test_settle_raises_when_finished_but_scores_missing(self):
        self.match.status = "finished"
        self.match.save()
        with self.assertRaises(ValueError):
            settle_match(self.match)

    def test_settle_awards_points_across_predictions(self):
        self._finish_match(2, 1)
        pred_exact = self._make_prediction(self.user_a, 2, 1)
        pred_outcome = self._make_prediction(self.user_b, 1, 0)
        pred_wrong = self._make_prediction(self.user_c, 0, 0)

        settle_match(self.match)

        pred_exact.refresh_from_db()
        pred_outcome.refresh_from_db()
        pred_wrong.refresh_from_db()
        self.assertEqual(pred_exact.points_awarded, 3)
        self.assertEqual(pred_outcome.points_awarded, 1)
        self.assertEqual(pred_wrong.points_awarded, 0)
        self.assertEqual(self._participation(self.user_a).points, 3)
        self.assertEqual(self._participation(self.user_b).points, 1)
        self.assertEqual(self._participation(self.user_c).points, 0)

    def test_settle_is_idempotent(self):
        self._finish_match(2, 1)
        self._make_prediction(self.user_a, 2, 1)

        settle_match(self.match)
        settle_match(self.match)

        self.assertEqual(self._participation(self.user_a).points, 3)
        pred = Prediction.objects.get(user=self.user_a, match=self.match)
        self.assertEqual(pred.points_awarded, 3)

    def test_settle_uses_delta_on_result_change(self):
        self._finish_match(2, 1)
        pred = self._make_prediction(self.user_a, 2, 1)

        settle_match(self.match)
        self.assertEqual(self._participation(self.user_a).points, 3)

        self.match.home_score = 0
        self.match.away_score = 0
        self.match.save()
        settle_match(self.match)

        pred.refresh_from_db()
        self.assertEqual(pred.points_awarded, 0)
        self.assertEqual(self._participation(self.user_a).points, 0)

    def test_settle_skips_missing_participation_gracefully(self):
        self._finish_match(2, 1)
        orphan_user = User.objects.create_user(
            username="orphan", email="orphan@example.com", password="pass123"
        )
        Membership.objects.create(user=orphan_user, group=self.group, role="member")
        pred = self._make_prediction(orphan_user, 2, 1)

        settle_match(self.match)

        pred.refresh_from_db()
        self.assertEqual(pred.points_awarded, 3)
        self.assertFalse(
            TournamentParticipation.objects.filter(
                user=orphan_user, tournament=self.tournament
            ).exists()
        )
