from django.contrib import admin

from .models import Tournament, TournamentParticipation


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
