from django.urls import path

from .views import CtlCardSetListView, CtlUserCardCreateView, CtlUserCardListView, index

app_name = "core"
urlpatterns = [
    path("", index, name="index"),
    path("cardsets/", CtlCardSetListView.as_view()),
    path("cards/", CtlUserCardListView.as_view(), name="cards"),
    path("cards/create/", CtlUserCardCreateView.as_view(), name="cards-create"),
]
