"""
URL configuration for blog project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path
from users.views import (
    RegisterView,
    CreateGroupView,
    GroupDetailView,
    DeleteGroupView,
    LeaveGroupView,
    InviteToGroupView,
)
from django.contrib.auth.views import LoginView, LogoutView


urlpatterns = [
    # Authentication URLs
    path("login/", LoginView.as_view(template_name="users/login.html"), name="login"),
    path(
        "logout/", LogoutView.as_view(template_name="users/logout.html"), name="logout"
    ),
    path("register/", RegisterView.as_view(), name="register"),
    # Group URLs
    path("groups/create/", CreateGroupView.as_view(), name="create_group"),
    path("groups/<int:group_id>/", GroupDetailView.as_view(), name="group_detail"),
    path(
        "groups/<int:group_id>/delete/", DeleteGroupView.as_view(), name="delete_group"
    ),
    path("groups/<int:group_id>/leave/", LeaveGroupView.as_view(), name="leave_group"),
    path(
        "groups/<int:group_id>/invite/",
        InviteToGroupView.as_view(),
        name="invite_to_group",
    ),
]
