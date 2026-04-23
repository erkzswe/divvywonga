import logging

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from users.models import Group, Membership

from .forms import TournamentCreateForm, TournamentInviteForm
from .models import Tournament, TournamentParticipation

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

        context = {
            "group": group,
            "tournament": tournament,
            "participants": participants,
            "user_membership": membership,
            "user_participation": user_participation,
            "admin_count": admin_count,
            "moderator_count": moderator_count,
            "total_points": total_points,
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
