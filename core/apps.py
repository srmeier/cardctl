import requests
from django.apps import AppConfig
from django.db.models.signals import post_migrate


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        post_migrate.connect(update_references)


def update_references(sender: AppConfig, **kwargs):
    if not isinstance(sender, CoreConfig):
        return

    from .models import CtlCardSet, CtlRefCard  # noqa: E402

    card_set_objects = []
    ref_card_objects = []

    sets = []

    response = requests.get("https://api.scryfall.com/sets")
    response.raise_for_status()
    payload: dict = response.json()

    sets.extend(payload.get("data", []))

    while payload.get("has_more", False):
        response = requests.get(payload.get("next_page"))
        response.raise_for_status()
        payload: dict = response.json()

        sets.extend(payload.get("data", []))

    set_data: dict
    for set_data in sets:
        if set_data.get("tcgplayer_id") is None:
            continue

        try:
            card_set = CtlCardSet.objects.get(metadata__id=set_data.get("id"))
        except CtlCardSet.DoesNotExist:
            card_set = CtlCardSet(
                name=set_data.get("name"),
                source=CtlCardSet.Source.SCRYFALL,
                metadata=set_data,
            )
            card_set_objects.append(card_set)

        cards = []

        response = requests.get(set_data.get("search_uri"))
        response.raise_for_status()
        payload: dict = response.json()

        cards.extend(payload.get("data", []))

        while payload.get("has_more", False):
            response = requests.get(payload.get("next_page"))
            response.raise_for_status()
            payload: dict = response.json()

            cards.extend(payload.get("data", []))

        card_data: dict
        for card_data in cards:
            try:
                ref_card = CtlRefCard.objects.get(metadata__id=card_data.get("id"))
            except CtlRefCard.DoesNotExist:
                ref_card = CtlRefCard(
                    name=card_data.get("name"),
                    card_set=card_set,
                    metadata=card_data,
                )
                ref_card_objects.append(ref_card)

    CtlCardSet.objects.bulk_create(card_set_objects)
    CtlRefCard.objects.bulk_create(ref_card_objects)
