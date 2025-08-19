from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.core.exceptions import ValidationError
from users.forms import UserRegisterForm, GroupCreateForm, GroupInviteForm
from users.models import Group, Membership


class RegisterView(View):
    def get(self, request):
        form = UserRegisterForm()
        return render(request, "users/register.html", {"form": form})

    def post(self, request):
        form = UserRegisterForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("index")

        return render(request, "users/register.html", {"form": form})


class CreateGroupView(LoginRequiredMixin, View):
    """View for creating a new group with user invitations."""

    def get(self, request):
        form = GroupCreateForm(request=request)
        user_groups = Membership.objects.filter(user=request.user).select_related(
            "group"
        )
        return render(
            request,
            "users/create_group.html",
            {"form": form, "user_groups": user_groups},
        )

    def post(self, request):
        form = GroupCreateForm(request.POST, request=request)

        if form.is_valid():
            with transaction.atomic():
                # Create the group
                group = form.save()

                # Automatically make the creator an admin member of the group
                Membership.objects.create(
                    user=request.user, group=group, role="admin", points=0
                )

                # Process invited users by email
                invite_emails = form.cleaned_data.get("invite_users", "")
                invite_role = form.cleaned_data.get("invite_role", "member")

                if invite_emails:
                    # Split by comma and clean up whitespace
                    emails = [
                        email.strip()
                        for email in invite_emails.split(",")
                        if email.strip()
                    ]

                    # Get or create users for each email
                    for email in emails:
                        try:
                            # Try to find an existing user
                            user = User.objects.get(email=email)

                            # Check if user is already a member
                            if not Membership.objects.filter(
                                user=user, group=group
                            ).exists():
                                Membership.objects.create(
                                    user=user, group=group, role=invite_role, points=0
                                )

                        except User.DoesNotExist:
                            # In a real app, you might want to send an invitation email here
                            pass  # Skip non-existent users for now

                # Prepare success message
                message = (
                    f'Group "{group.name}" created successfully! You are now the admin.'
                )
                if invite_emails:
                    message += f" {invite_emails} users have been invited to the group."

                messages.success(request, message)
                return redirect(
                    "group_detail", group_id=group.id
                )  # Redirect to the new group's detail page

        # If form is invalid, show the form again with errors
        user_groups = Membership.objects.filter(user=request.user).select_related(
            "group"
        )
        return render(
            request,
            "users/create_group.html",
            {"form": form, "user_groups": user_groups},
        )


class GroupDetailView(LoginRequiredMixin, View):
    """View for displaying group details and members."""

    def get(self, request, group_id):
        # Get the group and ensure it exists
        group = get_object_or_404(Group, id=group_id)

        # Get all members of the group
        members = Membership.objects.filter(group=group).select_related("user")

        # Get the current user's membership (if they're a member)
        user_membership = members.filter(user=request.user).first()

        # Check if the user has permission to view this group
        if not user_membership and not request.user.is_superuser:
            messages.error(request, "You don't have permission to view this group.")
            return redirect("index")

        # Calculate statistics
        admin_count = members.filter(role="admin").count()
        moderator_count = members.filter(role="moderator").count()
        total_points = members.aggregate(total=Sum("points"))["total"] or 0

        context = {
            "group": group,
            "members": members,
            "user_membership": user_membership,
            "admin_count": admin_count,
            "moderator_count": moderator_count,
            "total_points": total_points,
        }

        return render(request, "users/group_detail.html", context)


class DeleteGroupView(LoginRequiredMixin, View):
    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)

        # Check if user is an admin of this group
        membership = Membership.objects.filter(
            user=request.user, group=group, role="admin"
        ).first()

        if not membership and not request.user.is_superuser:
            messages.error(request, "You don't have permission to delete this group.")
            return redirect("index")

        # Delete the group (this will cascade to memberships due to CASCADE in model)
        group_name = group.name
        group.delete()

        messages.success(
            request, f'Group "{group_name}" has been deleted successfully.'
        )
        return redirect("index")


class LeaveGroupView(LoginRequiredMixin, View):
    """View for a member to leave a group."""

    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)

        # Get the user's membership
        membership = Membership.objects.filter(user=request.user, group=group).first()

        if not membership:
            messages.error(request, "You are not a member of this group.")
            return redirect("index")

        # Check if this is the last admin
        if membership.role == "admin":
            admin_count = Membership.objects.filter(group=group, role="admin").count()

            if admin_count <= 1:
                messages.error(
                    request,
                    "You are the last admin of this group. Please assign another admin before leaving.",
                )
                return redirect("group_detail", group_id=group.id)

        # Remove the membership
        membership.delete()

        messages.success(request, f'You have left the group "{group.name}".')
        return redirect("index")


class InviteToGroupView(LoginRequiredMixin, View):
    """View for inviting users to a group."""

    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)

        # Check if user has permission to invite members
        membership = Membership.objects.filter(
            user=request.user, group=group, role__in=["admin", "moderator"]
        ).first()

        if not membership and not request.user.is_superuser:
            messages.error(
                request, "You don't have permission to invite members to this group."
            )
            return redirect("group_detail", group_id=group.id)

        form = GroupInviteForm()
        return render(
            request, "users/invite_to_group.html", {"group": group, "form": form}
        )

    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)

        # Check if user has permission to invite members
        membership = Membership.objects.filter(
            user=request.user, group=group, role__in=["admin", "moderator"]
        ).first()

        if not membership and not request.user.is_superuser:
            messages.error(
                request, "You don't have permission to invite members to this group."
            )
            return redirect("group_detail", group_id=group.id)

        form = GroupInviteForm(request.POST)

        if form.is_valid():
            emails = [
                email.strip()
                for email in form.cleaned_data["emails"].split(",")
                if email.strip()
            ]
            invited_users = []

            for email in emails:
                try:
                    user = User.objects.get(email=email)
                    # Check if user is already a member
                    if not Membership.objects.filter(user=user, group=group).exists():
                        Membership.objects.create(
                            user=user,
                            group=group,
                            role=form.cleaned_data["role"],
                            points=0,
                        )
                        invited_users.append(email)
                except User.DoesNotExist:
                    # In a real app, you might want to send an invitation email here
                    pass

            if invited_users:
                messages.success(
                    request,
                    f"Successfully invited {len(invited_users)} user(s) to the group.",
                )
            else:
                messages.warning(request, "No new users were invited.")

            return redirect("group_detail", group_id=group.id)

        return render(
            request, "users/invite_to_group.html", {"group": group, "form": form}
        )
