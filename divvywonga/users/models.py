from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Group(models.Model):
    """
    Group model that users can belong to.
    """

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    # Many-to-many relationship with User through Membership model
    members = models.ManyToManyField(
        User, through="Membership", related_name="user_groups"
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Group"
        verbose_name_plural = "Groups"

    def __str__(self):
        return self.name

    def get_active_members(self):
        """Get all active members of this group."""
        return self.members.filter(membership__is_active=True)

    def get_total_points(self):
        """Get total points for all members in this group."""
        return (
            self.membership_set.filter(is_active=True).aggregate(
                total=models.Sum("points")
            )["total"]
            or 0
        )


class Membership(models.Model):
    """
    Auxiliary model for the many-to-many relationship between User and Group.
    This allows us to store additional attributes for each user-group relationship.
    """

    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("moderator", "Moderator"),
        ("member", "Member"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)

    # Additional attributes for the relationship
    points = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10000)],
        help_text="Points earned by the user in this group",
    )

    # Membership metadata
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="member")

    class Meta:
        unique_together = ("user", "group")
        ordering = ["-joined_at"]
        verbose_name = "Membership"
        verbose_name_plural = "Memberships"

    def __str__(self):
        return f"{self.user.username} in {self.group.name} ({self.points} points)"

    def is_admin(self):
        """Check if user is admin of this group."""
        return self.role == "admin"

    def is_moderator(self):
        """Check if user is moderator of this group."""
        return self.role == "moderator"

    def can_moderate(self):
        """Check if user can moderate this group."""
        return self.role in ["admin", "moderator"]
