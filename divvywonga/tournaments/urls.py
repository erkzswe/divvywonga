from django.urls import path

from .views import (
    CreateMatchView,
    CreateTournamentView,
    DeleteTournamentView,
    InviteToTournamentView,
    LeaveTournamentView,
    MatchListView,
    PredictView,
    SetMatchResultView,
    TournamentDetailView,
    TournamentListView,
)

app_name = "tournaments"

urlpatterns = [
    path(
        "groups/<int:group_id>/tournaments/",
        TournamentListView.as_view(),
        name="group_tournaments",
    ),
    path(
        "groups/<int:group_id>/tournaments/create/",
        CreateTournamentView.as_view(),
        name="create_tournament",
    ),
    path(
        "groups/<int:group_id>/tournaments/<int:tournament_id>/",
        TournamentDetailView.as_view(),
        name="tournament_detail",
    ),
    path(
        "groups/<int:group_id>/tournaments/<int:tournament_id>/delete/",
        DeleteTournamentView.as_view(),
        name="delete_tournament",
    ),
    path(
        "groups/<int:group_id>/tournaments/<int:tournament_id>/leave/",
        LeaveTournamentView.as_view(),
        name="leave_tournament",
    ),
    path(
        "groups/<int:group_id>/tournaments/<int:tournament_id>/invite/",
        InviteToTournamentView.as_view(),
        name="invite_to_tournament",
    ),
    path(
        "groups/<int:group_id>/tournaments/<int:tournament_id>/matches/",
        MatchListView.as_view(),
        name="match_list",
    ),
    path(
        "groups/<int:group_id>/tournaments/<int:tournament_id>/matches/create/",
        CreateMatchView.as_view(),
        name="create_match",
    ),
    path(
        "groups/<int:group_id>/tournaments/<int:tournament_id>/matches/<int:match_id>/predict/",
        PredictView.as_view(),
        name="predict",
    ),
    path(
        "groups/<int:group_id>/tournaments/<int:tournament_id>/matches/<int:match_id>/result/",
        SetMatchResultView.as_view(),
        name="set_match_result",
    ),
]

