from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db import transaction
from users.forms import UserRegisterForm, GroupCreateForm
from users.models import Group, Membership


class RegisterView(View):
    def get(self, request):
        form = UserRegisterForm()
        return render(request, 'users/register.html', {"form": form})
    
    def post(self, request):
        form = UserRegisterForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('index')
        
        return render(request, 'users/register.html', {"form": form})


class CreateGroupView(LoginRequiredMixin, View):
    """View for creating a new group with user invitations."""
    
    def get(self, request):
        form = GroupCreateForm(request=request)
        user_groups = Membership.objects.filter(user=request.user).select_related('group')
        return render(request, 'users/create_group.html', {
            'form': form,
            'user_groups': user_groups
        })
    
    def post(self, request):
        form = GroupCreateForm(request.POST, request=request)
        
        if form.is_valid():
            with transaction.atomic():
                # Create the group
                group = form.save()
                
                # Automatically make the creator an admin member of the group
                Membership.objects.create(
                    user=request.user,
                    group=group,
                    role='admin',
                    points=0
                )
                
                # Process invited users by email
                invite_emails = form.cleaned_data.get('invite_users', '')
                invite_role = form.cleaned_data.get('invite_role', 'member')
                
                if invite_emails:
                    # Split by comma and clean up whitespace
                    emails = [email.strip() for email in invite_emails.split(',') if email.strip()]
                    
                    # Get or create users for each email
                    for email in emails:
                        try:
                            # Try to find an existing user
                            user = User.objects.get(email=email)
                            
                            # Check if user is already a member
                            if not Membership.objects.filter(user=user, group=group).exists():
                                Membership.objects.create(
                                    user=user,
                                    group=group,
                                    role=invite_role,
                                    points=0
                                )
                                
                        except User.DoesNotExist:
                            # In a real app, you might want to send an invitation email here
                            pass  # Skip non-existent users for now
                
                # Prepare success message
                message = f'Group "{group.name}" created successfully! You are now the admin.'
                if invite_emails:
                    message += f' {invite_emails} users have been invited to the group.'
                
                messages.success(request, message)
                return redirect('index')  # Redirect to home or group detail page
        
        # If form is invalid, show the form again with errors
        user_groups = Membership.objects.filter(user=request.user).select_related('group')
        return render(request, 'users/create_group.html', {
            'form': form,
            'user_groups': user_groups
        })