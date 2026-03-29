from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin


class Index(LoginRequiredMixin, View):
    def get(self, request):
        user_groups = (
            request.user.membership_set.select_related("group")
            .filter(is_active=True)
            .order_by("-joined_at")
        )
        return render(request, "core/index.html", {"user_groups": user_groups})
