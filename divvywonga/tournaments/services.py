"""Business logic for scoring match predictions."""
from django.db import transaction

from .models import Match, Prediction, TournamentParticipation

POINTS_EXACT = 3
POINTS_OUTCOME = 1


def score_prediction(predicted_home, predicted_away, actual_home, actual_away) -> int:
    """Return points for a prediction: exact score=3, correct outcome=1, else 0."""
    if predicted_home == actual_home and predicted_away == actual_away:
        return POINTS_EXACT
    pred_outcome = _outcome(predicted_home, predicted_away)
    actual_outcome = _outcome(actual_home, actual_away)
    return POINTS_OUTCOME if pred_outcome == actual_outcome else 0


def _outcome(home, away) -> str:
    if home > away:
        return "home"
    if home < away:
        return "away"
    return "draw"


def settle_match(match: Match) -> None:
    """(Re)score all predictions for a finished match. Idempotent.

    For each prediction: recompute points_awarded, adjust the related
    TournamentParticipation.points by the DELTA (new - old) so re-settling
    after a result edit does not double-count. Skip predictions whose
    participation is missing/inactive. Use transaction.atomic().
    """
    if match.status != "finished" or match.home_score is None or match.away_score is None:
        raise ValueError("Match must be finished with both scores set to settle.")

    with transaction.atomic():
        for pred in match.predictions.all():
            new_points = score_prediction(
                pred.predicted_home_score,
                pred.predicted_away_score,
                match.home_score,
                match.away_score,
            )
            delta = new_points - pred.points_awarded
            pred.points_awarded = new_points
            pred.save()

            participation = (
                TournamentParticipation.objects.filter(
                    user=pred.user, tournament=match.tournament, is_active=True
                )
                .first()
            )
            if participation is not None:
                participation.points = max(0, participation.points + delta)
                participation.save()


def can_edit_prediction(prediction: Prediction) -> bool:
    """Return True if the prediction's match is still predictable."""
    return prediction.match.is_predictable()
