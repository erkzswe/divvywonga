from django.contrib import admin

from .models import Match, Prediction, Tournament, TournamentParticipation


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ("name", "group", "created_at", "is_active")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "group__name")
    raw_id_fields = ("group",)


@admin.register(TournamentParticipation)
class TournamentParticipationAdmin(admin.ModelAdmin):
    list_display = ("user", "tournament", "group", "role", "points")
    list_filter = ("role",)
    raw_id_fields = ("user", "tournament", "group")


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = (
        "home_team",
        "away_team",
        "tournament",
        "kickoff",
        "status",
        "home_score",
        "away_score",
    )
    list_filter = ("status", "kickoff")
    search_fields = ("home_team", "away_team", "tournament__name")
    raw_id_fields = ("tournament",)


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "match",
        "tournament",
        "predicted_home_score",
        "predicted_away_score",
        "points_awarded",
    )
    list_filter = ("points_awarded",)
    search_fields = ("user__username", "match__home_team", "match__away_team")
    raw_id_fields = ("user", "match", "tournament")
