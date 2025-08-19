from django.forms import EmailField
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.core.exceptions import ValidationError
from users.models import Group, Membership


class UserRegisterForm(UserCreationForm):
    email = EmailField()

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class GroupCreateForm(forms.ModelForm):
    """Form for creating a new group with user invitations."""

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Get all users except the current user for invitations
        if self.request and hasattr(self.request, "user"):
            self.fields["invite_users"] = forms.ModelMultipleChoiceField(
                queryset=User.objects.exclude(pk=self.request.user.pk),
                required=False,
                widget=forms.SelectMultiple(
                    attrs={
                        "class": "form-select",
                        "data-choices": "data-choices",
                        "data-options": '{"removeItemButton": true, "searchEnabled": true}',
                    }
                ),
                help_text="Select users to invite to this group (optional)",
            )

            # Add role selection for invited users
            self.fields["invite_role"] = forms.ChoiceField(
                choices=Membership.ROLE_CHOICES[1:],  # Exclude 'admin' role for invites
                initial="member",
                widget=forms.Select(
                    attrs={"class": "form-select", "data-role": "role-selector"}
                ),
                help_text="Default role for invited users",
            )

            # Change to CharField to accept email addresses
            self.fields["invite_users"] = forms.CharField(
                required=False,
                widget=forms.TextInput(
                    attrs={
                        "class": "form-control",
                        "placeholder": "Enter email addresses, separated by commas",
                        "data-role": "email-input",
                    }
                ),
                help_text="Enter email addresses of users to invite (comma-separated)",
            )

    class Meta:
        model = Group
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter group name",
                    "autofocus": True,
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Enter group description (optional)",
                }
            ),
        }
        help_texts = {
            "name": "Choose a unique name for your group.",
            "description": "Describe what this group is about (optional).",
        }


class GroupInviteForm(forms.Form):
    """Form for inviting users to an existing group."""

    emails = forms.CharField(
        label="Email Addresses",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Enter email addresses, separated by commas",
            }
        ),
        help_text="Enter one or more email addresses, separated by commas",
        required=True,
    )

    role = forms.ChoiceField(
        label="Role",
        choices=Membership.ROLE_CHOICES[1:],  # Exclude 'admin' role for invites
        initial="member",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
        help_text="Select the role for the invited users",
    )

    def clean_emails(self):
        emails = self.cleaned_data.get("emails", "")
        email_list = [email.strip() for email in emails.split(",") if email.strip()]

        # Basic email validation
        for email in email_list:
            if "@" not in email or "." not in email:
                raise ValidationError(f'"{email}" is not a valid email address')

        return emails
