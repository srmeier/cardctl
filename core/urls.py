from django.urls import path

from .views import CtlCardSetListView, index

app_name = "core"
urlpatterns = [
    path("", index, name="index"),
    path("cardset/", CtlCardSetListView.as_view()),
]
