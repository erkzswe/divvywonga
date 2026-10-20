import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError, models, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from users.models import Group, Membership

from .forms import (
    MatchCreateForm,
    MatchResultForm,
    PredictionForm,
    TournamentCreateForm,
    TournamentInviteForm,
)
from .models import Match, Prediction, Tournament, TournamentParticipation
from .services import settle_match

logger = logging.getLogger(__name__)


class TournamentListView(LoginRequiredMixin, View):
    """View for listing tournaments within a group."""

    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)

        membership = Membership.objects.filter(user=request.user, group=group).first()

        if not membership and not request.user.is_superuser:
            messages.error(request, "You are not a member of this group.")
            return redirect("index")

        tournaments = (
            Tournament.objects.filter(group=group)
            .annotate(participant_count=models.Count("tournamentparticipation"))
            .order_by("-created_at")
        )

        context = {
            "group": group,
            "tournaments": tournaments,
            "user_membership": membership,
        }

        return render(request, "tournaments/tournament_list.html", context)


class CreateTournamentView(LoginRequiredMixin, View):
    """View for creating a new tournament within a group."""

    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)

        membership = Membership.objects.filter(user=request.user, group=group).first()

        if not membership and not request.user.is_superuser:
            messages.error(request, "You are not a member of this group.")
            return redirect("index")

        form = TournamentCreateForm(request=request, group_id=group_id)
        form.instance.group = group

        return render(
            request,
            "tournaments/create_tournament.html",
            {"form": form, "group": group},
        )

    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)

        membership = Membership.objects.filter(user=request.user, group=group).first()

        if not membership and not request.user.is_superuser:
            messages.error(request, "You are not a member of this group.")
            return redirect("index")

        form = TournamentCreateForm(request.POST, request=request, group_id=group_id)

        if form.is_valid():
            with transaction.atomic():
                tournament = form.save(commit=False)
                tournament.group = group
                tournament.save()

                TournamentParticipation.objects.create(
                    user=request.user,
                    tournament=tournament,
                    group=group,
                    role="admin",
                    points=0,
                )

                messages.success(
                    request,
                    f'Tournament "{tournament.name}" created successfully! You are now the admin.',
                )
                return redirect(
                    "tournaments:tournament_detail",
                    group_id=group.id,
                    tournament_id=tournament.id,
                )

        return render(
            request,
            "tournaments/create_tournament.html",
            {"form": form, "group": group},
        )


class TournamentDetailView(LoginRequiredMixin, View):
    """View for displaying tournament details and participants."""

    def get(self, request, group_id, tournament_id):
        group = get_object_or_404(Group, id=group_id)
        tournament = get_object_or_404(Tournament, id=tournament_id, group=group)

        membership = Membership.objects.filter(user=request.user, group=group).first()

        if not membership and not request.user.is_superuser:
            messages.error(request, "You are not a member of this group.")
            return redirect("index")

        participants = TournamentParticipation.objects.filter(
            tournament=tournament
        ).select_related("user")
        user_participation = participants.filter(user=request.user).first()

        admin_count = participants.filter(role="admin").count()
        moderator_count = participants.filter(role="moderator").count()
        total_points = participants.aggregate(total=models.Sum("points"))["total"] or 0

        match_count = tournament.matches.count()
        upcoming_match_count = tournament.matches.filter(status="scheduled").count()

        context = {
            "group": group,
            "tournament": tournament,
            "participants": participants,
            "user_membership": membership,
            "user_participation": user_participation,
            "admin_count": admin_count,
            "moderator_count": moderator_count,
            "total_points": total_points,
            "match_count": match_count,
            "upcoming_match_count": upcoming_match_count,
        }

        return render(request, "tournaments/tournament_detail.html", context)


class DeleteTournamentView(LoginRequiredMixin, View):
    """View for deleting a tournament."""

    def post(self, request, group_id, tournament_id):
        group = get_object_or_404(Group, id=group_id)
        tournament = get_object_or_404(Tournament, id=tournament_id, group=group)

        group_membership = Membership.objects.filter(
            user=request.user, group=group, role="admin"
        ).first()

        tournament_participation = TournamentParticipation.objects.filter(
            user=request.user, tournament=tournament, role="admin"
        ).first()

        if (
            not (group_membership or tournament_participation)
            and not request.user.is_superuser
        ):
            messages.error(
                request, "You don't have permission to delete this tournament."
            )
            return redirect(
                "tournaments:tournament_detail",
                group_id=group.id,
                tournament_id=tournament.id,
            )

        tournament_name = tournament.name
        tournament.delete()

        messages.success(
            request, f'Tournament "{tournament_name}" has been deleted successfully.'
        )
        return redirect("tournaments:group_tournaments", group_id=group.id)


class LeaveTournamentView(LoginRequiredMixin, View):
    """View for a member to leave a tournament."""

    def post(self, request, group_id, tournament_id):
        group = get_object_or_404(Group, id=group_id)
        tournament = get_object_or_404(Tournament, id=tournament_id, group=group)

        participation = TournamentParticipation.objects.filter(
            user=request.user, tournament=tournament
        ).first()

        if not participation:
            messages.error(request, "You are not a participant of this tournament.")
            return redirect(
                "tournaments:tournament_detail",
                group_id=group.id,
                tournament_id=tournament.id,
            )

        if participation.role == "admin":
            admin_count = TournamentParticipation.objects.filter(
                tournament=tournament, role="admin"
            ).count()

            if admin_count <= 1:
                messages.error(
                    request,
                    "You are the last admin of this tournament. Please assign another admin before leaving.",
                )
                return redirect(
                    "tournaments:tournament_detail",
                    group_id=group.id,
                    tournament_id=tournament.id,
                )

        participation.delete()

        messages.success(request, f'You have left the tournament "{tournament.name}".')
        return redirect("tournaments:group_tournaments", group_id=group.id)


class InviteToTournamentView(LoginRequiredMixin, View):
    """View for inviting users to a tournament."""

    def get(self, request, group_id, tournament_id):
        group = get_object_or_404(Group, id=group_id)
        tournament = get_object_or_404(Tournament, id=tournament_id, group=group)

        group_membership = Membership.objects.filter(
            user=request.user, group=group, role__in=["admin", "moderator"]
        ).first()

        tournament_participation = TournamentParticipation.objects.filter(
            user=request.user, tournament=tournament, role__in=["admin", "moderator"]
        ).first()

        if (
            not (group_membership or tournament_participation)
            and not request.user.is_superuser
        ):
            messages.error(
                request, "You don't have permission to invite users to this tournament."
            )
            return redirect(
                "tournaments:tournament_detail",
                group_id=group.id,
                tournament_id=tournament.id,
            )

        form = TournamentInviteForm()
        return render(
            request,
            "tournaments/invite_to_tournament.html",
            {"group": group, "tournament": tournament, "form": form},
        )

    def post(self, request, group_id, tournament_id):
        group = get_object_or_404(Group, id=group_id)
        tournament = get_object_or_404(Tournament, id=tournament_id, group=group)

        group_membership = Membership.objects.filter(
            user=request.user, group=group, role__in=["admin", "moderator"]
        ).first()

        tournament_participation = TournamentParticipation.objects.filter(
            user=request.user, tournament=tournament, role__in=["admin", "moderator"]
        ).first()

        if (
            not (group_membership or tournament_participation)
            and not request.user.is_superuser
        ):
            messages.error(
                request, "You don't have permission to invite users to this tournament."
            )
            return redirect(
                "tournaments:tournament_detail",
                group_id=group.id,
                tournament_id=tournament.id,
            )

        form = TournamentInviteForm(request.POST)

        if form.is_valid():
            emails = [
                email.strip()
                for email in form.cleaned_data["emails"].split(",")
                if email.strip()
            ]
            invited_users = []

            for email in emails:
                try:
                    from django.contrib.auth import get_user_model

                    User = get_user_model()
                    user = User.objects.get(email=email)

                    membership = Membership.objects.filter(
                        user=user, group=group
                    ).first()

                    if not membership:
                        messages.warning(
                            request,
                            f"{email} is not a member of the group. Please invite them to the group first.",
                        )
                        continue

                    if not TournamentParticipation.objects.filter(
                        user=user, tournament=tournament
                    ).exists():
                        TournamentParticipation.objects.create(
                            user=user,
                            tournament=tournament,
                            group=group,
                            role=form.cleaned_data["role"],
                            points=0,
                        )
                        invited_users.append(email)
                except Exception:
                    messages.warning(
                        request, f"User with email {email} does not exist."
                    )

            if invited_users:
                messages.success(
                    request,
                    f"Successfully invited {len(invited_users)} user(s) to the tournament.",
                )
            else:
                messages.warning(request, "No new users were invited.")

            return redirect(
                "tournaments:tournament_detail",
                group_id=group.id,
                tournament_id=tournament.id,
            )

        return render(
            request,
            "tournaments/invite_to_tournament.html",
            {"group": group, "tournament": tournament, "form": form},
        )


def _user_is_tournament_moderator(user, group, tournament):
    """True if user can moderate matches (group-role, tournament-role or superuser)."""
    if user.is_superuser:
        return True

    group_moderator = Membership.objects.filter(
        user=user, group=group, role__in=["admin", "moderator"]
    ).exists()

    tournament_moderator = TournamentParticipation.objects.filter(
        user=user, tournament=tournament, role__in=["admin", "moderator"]
    ).exists()

    return group_moderator or tournament_moderator


class MatchListView(LoginRequiredMixin, View):
    """View for listing matches within a tournament."""

    def get(self, request, group_id, tournament_id):
        group = get_object_or_404(Group, id=group_id)
        tournament = get_object_or_404(Tournament, id=tournament_id, group=group)

        membership = Membership.objects.filter(user=request.user, group=group).first()

        if not membership and not request.user.is_superuser:
            messages.error(request, "You are not a member of this group.")
            return redirect("index")

        matches = list(
            tournament.matches.prefetch_related("predictions").order_by("kickoff")
        )

        upcoming = [m for m in matches if m.status == "scheduled"]
        finished = [m for m in matches if m.status == "finished"]
        cancelled = [m for m in matches if m.status == "cancelled"]

        user_predictions = Prediction.objects.filter(
            match__in=matches, user=request.user
        )
        user_prediction_map = {p.match_id: p for p in user_predictions}
        for match in matches:
            match.user_prediction = user_prediction_map.get(match.id)

        is_moderator = _user_is_tournament_moderator(request.user, group, tournament)

        context = {
            "group": group,
            "tournament": tournament,
            "matches": matches,
            "upcoming": upcoming,
            "finished": finished,
            "cancelled": cancelled,
            "user_prediction_map": user_prediction_map,
            "is_moderator": is_moderator,
            "total_matches": len(matches),
        }

        return render(request, "tournaments/match_list.html", context)


class CreateMatchView(LoginRequiredMixin, View):
    """View for creating a new match within a tournament (moderators only)."""

    def get(self, request, group_id, tournament_id):
        group = get_object_or_404(Group, id=group_id)
        tournament = get_object_or_404(Tournament, id=tournament_id, group=group)

        if not _user_is_tournament_moderator(request.user, group, tournament):
            messages.error(request, "You don't have permission to create matches.")
            return redirect(
                "tournaments:tournament_detail",
                group_id=group.id,
                tournament_id=tournament.id,
            )

        form = MatchCreateForm()

        return render(
            request,
            "tournaments/create_match.html",
            {"form": form, "group": group, "tournament": tournament},
        )

    def post(self, request, group_id, tournament_id):
        group = get_object_or_404(Group, id=group_id)
        tournament = get_object_or_404(Tournament, id=tournament_id, group=group)

        if not _user_is_tournament_moderator(request.user, group, tournament):
            messages.error(request, "You don't have permission to create matches.")
            return redirect(
                "tournaments:tournament_detail",
                group_id=group.id,
                tournament_id=tournament.id,
            )

        form = MatchCreateForm(request.POST)

        if form.is_valid():
            match = form.save(commit=False)
            match.tournament = tournament
            match.save()

            messages.success(
                request,
                f'Match "{match.home_team} vs {match.away_team}" created successfully!',
            )
            return redirect(
                "tournaments:match_list",
                group_id=group.id,
                tournament_id=tournament.id,
            )

        return render(
            request,
            "tournaments/create_match.html",
            {"form": form, "group": group, "tournament": tournament},
        )


class SetMatchResultView(LoginRequiredMixin, View):
    """View for setting/updating a match result (moderators only, POST only)."""

    def post(self, request, group_id, tournament_id, match_id):
        group = get_object_or_404(Group, id=group_id)
        tournament = get_object_or_404(Tournament, id=tournament_id, group=group)
        match = get_object_or_404(Match, id=match_id, tournament=tournament)

        match_list_redirect = redirect(
            "tournaments:match_list",
            group_id=group.id,
            tournament_id=tournament.id,
        )

        if not _user_is_tournament_moderator(request.user, group, tournament):
            messages.error(
                request, "You don't have permission to set match results."
            )
            return match_list_redirect

        form = MatchResultForm(request.POST, instance=match)

        if form.is_valid():
            match = form.save()

            if match.status == "finished":
                settle_match(match)
                messages.success(
                    request,
                    f'Result for "{match.home_team} vs {match.away_team}" saved and points settled.',
                )
            else:
                messages.success(
                    request,
                    f'Result for "{match.home_team} vs {match.away_team}" updated.',
                )
            return match_list_redirect

        messages.error(
            request,
            "Invalid match result: "
            + "; ".join(
                error for errors in form.errors.values() for error in errors
            ),
        )
        return match_list_redirect


class PredictView(LoginRequiredMixin, View):
    """View for placing or updating a user's prediction on a match."""

    def _resolve(self, request, group_id, tournament_id, match_id):
        """Fetch scoped objects and run access checks.

        Returns (group, tournament, match, None) on success, otherwise
        (None, None, None, redirect_response).
        """
        group = get_object_or_404(Group, id=group_id)
        tournament = get_object_or_404(Tournament, id=tournament_id, group=group)
        match = get_object_or_404(Match, id=match_id, tournament=tournament)

        membership = Membership.objects.filter(user=request.user, group=group).first()

        if not membership and not request.user.is_superuser:
            messages.error(request, "You are not a member of this group.")
            return None, None, None, redirect("index")

        participation = TournamentParticipation.objects.filter(
            user=request.user, tournament=tournament, is_active=True
        ).first()

        if not participation:
            messages.error(request, "Join the tournament to place predictions.")
            return None, None, None, redirect(
                "tournaments:tournament_detail",
                group_id=group.id,
                tournament_id=tournament.id,
            )

        if not match.is_predictable():
            messages.warning(request, "Predictions for this match are closed.")
            return None, None, None, redirect(
                "tournaments:match_list",
                group_id=group.id,
                tournament_id=tournament.id,
            )

        return group, tournament, match, None

    def get(self, request, group_id, tournament_id, match_id):
        group, tournament, match, error = self._resolve(
            request, group_id, tournament_id, match_id
        )
        if error is not None:
            return error

        existing_prediction = Prediction.objects.filter(
            user=request.user, match=match
        ).first()
        form = PredictionForm(instance=existing_prediction)

        context = {
            "group": group,
            "tournament": tournament,
            "match": match,
            "form": form,
            "existing_prediction": existing_prediction,
        }

        return render(request, "tournaments/predict.html", context)

    def post(self, request, group_id, tournament_id, match_id):
        group, tournament, match, error = self._resolve(
            request, group_id, tournament_id, match_id
        )
        if error is not None:
            return error

        existing_prediction = Prediction.objects.filter(
            user=request.user, match=match
        ).first()
        form = PredictionForm(request.POST, instance=existing_prediction)

        if form.is_valid():
            prediction = form.save(commit=False)
            prediction.user = request.user
            prediction.match = match
            prediction.tournament = tournament

            try:
                prediction.save()
            except IntegrityError:
                messages.error(
                    request, "You already have a prediction for this match."
                )
                return redirect(
                    "tournaments:match_list",
                    group_id=group.id,
                    tournament_id=tournament.id,
                )

            if existing_prediction:
                messages.success(request, "Prediction updated.")
            else:
                messages.success(request, "Prediction placed.")

            return redirect(
                "tournaments:match_list",
                group_id=group.id,
                tournament_id=tournament.id,
            )

        context = {
            "group": group,
            "tournament": tournament,
            "match": match,
            "form": form,
            "existing_prediction": existing_prediction,
        }

        return render(request, "tournaments/predict.html", context)
