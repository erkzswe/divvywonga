from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Match, Prediction, Tournament, TournamentParticipation


class TournamentCreateForm(forms.ModelForm):
    """Form for creating a new tournament within a group."""

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        self.group_id = kwargs.pop("group_id", None)
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            self.fields["start_date"].initial = timezone.now()
            self.fields["end_date"].initial = timezone.now() + timezone.timedelta(
                days=7
            )

    class Meta:
        model = Tournament
        fields = [
            "name",
            "description",
            "sport_type",
            "tournament_type",
            "start_date",
            "end_date",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter tournament name",
                    "autofocus": True,
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Enter tournament description (optional)",
                }
            ),
            "sport_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "tournament_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "start_date": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                }
            ),
            "end_date": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                }
            ),
        }
        help_texts = {
            "name": "Choose a unique name for your tournament within this group.",
            "description": "Describe what this tournament is about (optional).",
            "sport_type": "Select the sport type for this tournament.",
            "tournament_type": "Select the format of the tournament.",
            "start_date": "When the tournament starts.",
            "end_date": "When the tournament ends (optional).",
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and end_date <= start_date:
            raise forms.ValidationError("End date must be after the start date.")

        return cleaned_data


class TournamentInviteForm(forms.Form):
    """Form for inviting users to an existing tournament."""

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
        choices=TournamentParticipation.ROLE_CHOICES[1:],
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

        for email in email_list:
            if "@" not in email or "." not in email:
                raise ValidationError(f'"{email}" is not a valid email address')

        return emails


class MatchCreateForm(forms.ModelForm):
    """Form for creating a new match within a tournament."""

    class Meta:
        model = Match
        fields = ["home_team", "away_team", "kickoff"]
        widgets = {
            "home_team": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter home team name",
                }
            ),
            "away_team": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter away team name",
                }
            ),
            "kickoff": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                }
            ),
        }
        help_texts = {
            "home_team": "The home team for this match.",
            "away_team": "The away team for this match.",
            "kickoff": "When the match kicks off.",
        }

    def clean_home_team(self):
        return self.cleaned_data["home_team"].strip()

    def clean_away_team(self):
        return self.cleaned_data["away_team"].strip()

    def clean(self):
        cleaned_data = super().clean()
        home_team = cleaned_data.get("home_team")
        away_team = cleaned_data.get("away_team")

        if (
            home_team
            and away_team
            and home_team.strip().lower() == away_team.strip().lower()
        ):
            raise ValidationError("Home and away teams must be different.")

        return cleaned_data


class MatchResultForm(forms.ModelForm):
    """Form for entering or updating the result of a match."""

    class Meta:
        model = Match
        fields = ["home_score", "away_score", "status"]
        widgets = {
            "home_score": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "placeholder": "Home score",
                }
            ),
            "away_score": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "placeholder": "Away score",
                }
            ),
            "status": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }
        help_texts = {
            "home_score": "Final home score (required for finished matches).",
            "away_score": "Final away score (required for finished matches).",
            "status": "Select the current status of the match.",
        }

    def clean(self):
        cleaned_data = super().clean()
        home_score = cleaned_data.get("home_score")
        away_score = cleaned_data.get("away_score")
        status = cleaned_data.get("status")

        if status == "finished" and (home_score is None or away_score is None):
            raise ValidationError(
                "Both scores are required for a finished match."
            )
        if status != "finished" and (
            home_score is not None or away_score is not None
        ):
            raise ValidationError("Scores can only be set for finished matches.")

        return cleaned_data


class PredictionForm(forms.ModelForm):
    """Form for a user's score prediction on a match."""

    class Meta:
        model = Prediction
        fields = ["predicted_home_score", "predicted_away_score"]
        widgets = {
            "predicted_home_score": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "placeholder": "Predicted home score",
                }
            ),
            "predicted_away_score": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "placeholder": "Predicted away score",
                }
            ),
        }
        help_texts = {
            "predicted_home_score": "Your predicted home score.",
            "predicted_away_score": "Your predicted away score.",
        }
