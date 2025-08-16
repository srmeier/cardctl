from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.generic import ListView

from .models import CtlCardSet


def index(request):
    return render(request, "core/index.html")


class CtlCardSetListView(LoginRequiredMixin, ListView):
    model = CtlCardSet
