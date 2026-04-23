from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum
from django.utils import timezone


class Tournament(models.Model):
    """
    Tournament model that belongs to a group.
    Examples: World Cup, Champions League, Premier League season.
    """

    SPORT_TYPE_CHOICES = [
        ("football", "Football"),
        ("basketball", "Basketball"),
        ("tennis", "Tennis"),
        ("baseball", "Baseball"),
        ("hockey", "Hockey"),
        ("other", "Other"),
    ]

    TOURNAMENT_TYPE_CHOICES = [
        ("league", "League"),
        ("knockout", "Knockout"),
        ("round_robin", "Round Robin"),
        ("mixed", "Mixed Format"),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    group = models.ForeignKey(
        "users.Group", on_delete=models.CASCADE, related_name="tournaments"
    )
    sport_type = models.CharField(
        max_length=20, choices=SPORT_TYPE_CHOICES, default="football"
    )
    tournament_type = models.CharField(
        max_length=20, choices=TOURNAMENT_TYPE_CHOICES, default="league"
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Tournament"
        verbose_name_plural = "Tournaments"
        unique_together = (
            "name",
            "group",
        )

    def __str__(self):
        return f"{self.name} ({self.group.name})"

    def get_active_participants(self):
        """Get all active participants of this tournament."""
        return self.tournamentparticipation_set.filter(is_active=True).select_related(
            "user"
        )

    def get_total_points(self):
        """Get total points for all participants in this tournament."""
        return (
            TournamentParticipation.objects.filter(
                tournament=self, is_active=True
            ).aggregate(total=Sum("points"))["total"]
            or 0
        )

    def user_can_invite(self, user):
        """Check if user can invite others to this tournament."""
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True

        from users.models import Membership

        membership = Membership.objects.filter(
            user=user, group=self.group, role__in=["admin", "moderator"]
        ).first()
        if membership:
            return True

        participation = TournamentParticipation.objects.filter(
            user=user, tournament=self, role__in=["admin", "moderator"]
        ).first()
        return participation is not None


class TournamentParticipation(models.Model):
    """
    Model tracking user participation in a specific tournament.
    Stores points earned by user in this specific tournament.
    """

    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("moderator", "Moderator"),
        ("member", "Member"),
        ("predictor", "Predictor"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    group = models.ForeignKey("users.Group", on_delete=models.CASCADE)

    points = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10000)],
        help_text="Points earned by the user in this specific tournament",
    )

    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="member")

    class Meta:
        unique_together = ("user", "tournament")
        ordering = ["-joined_at"]
        verbose_name = "Tournament Participation"
        verbose_name_plural = "Tournament Participations"

    def __str__(self):
        return f"{self.user.username} in {self.tournament.name} ({self.points} points)"

    def is_admin(self):
        """Check if user is admin of this tournament."""
        return self.role == "admin"

    def is_moderator(self):
        """Check if user is moderator of this tournament."""
        return self.role == "moderator"

    def can_moderate(self):
        """Check if user can moderate this tournament."""
        return self.role in ["admin", "moderator"]
