from os import getenv

import requests
import torch
from django.apps import AppConfig
from django.db.models.signals import post_migrate
from opensearchpy import OpenSearch, helpers
from PIL import Image
from transformers import CLIPModel, CLIPProcessor


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

    device = "cuda" if torch.cuda.is_available() else "cpu"

    model = CLIPModel.from_pretrained(
        "openai/clip-vit-base-patch32",
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa",
    ).to(device)

    processor = CLIPProcessor.from_pretrained(
        "openai/clip-vit-base-patch32", use_fast=False
    )

    batch_size = 512
    cards = list(CtlRefCard.objects.all())
    card_ids, embeddings = [], []

    for i in range(0, len(cards), batch_size):
        batch_cards = cards[i : i + batch_size]
        images = [
            Image.open(
                requests.get(card.metadata["image_uris"]["large"], stream=True).raw
            )
            for card in batch_cards
            if ("image_uris" in card.metadata)  # TODO: Handle multi-face cards
        ]
        texts = [""] * len(batch_cards)

        inputs = processor(text=texts, images=images, return_tensors="pt", padding=True)
        inputs = {k: v.to(device) for k, v in inputs.items()}

        outputs = model(**inputs)
        batch_embeddings = outputs.image_embeds.detach().cpu().tolist()

        embeddings.extend(batch_embeddings)
        card_ids.extend([card.id for card in batch_cards])

    dimensions = 512
    index_name = "ctlrefcards"

    opensearch_client = OpenSearch(
        hosts=[{"host": getenv("OPENSEARCH_HOST"), "port": getenv("OPENSEARCH_PORT")}],
        http_compress=True,
        http_auth=(getenv("OPENSEARCH_USERNAME"), getenv("OPENSEARCH_PASSWORD")),
        use_ssl=True,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
    )

    index_body = {
        "settings": {
            "index": {
                "knn": True,
            }
        },
        "mappings": {
            "properties": {
                "card_id": {"type": "keyword"},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": dimensions,
                    "index": True,
                    "similarity": "cosine",
                },
            }
        },
    }

    if opensearch_client.indices.exists(index=index_name):
        opensearch_client.indices.delete(index=index_name)

    opensearch_client.indices.create(index=index_name, body=index_body)

    actions = []
    for card_id, embedding in zip(card_ids, embeddings):
        action = {
            "_index": index_name,
            "_source": {"embedding": embedding, "card_id": card_id},
        }
        actions.append(action)

    helpers.bulk(opensearch_client, actions)
    opensearch_client.indices.refresh(index=index_name)

    # search_body = {
    #     "size": 5,
    #     "query": {"knn": {"embedding": {"vector": embedding.tolist(), "k": 5}}},
    # }

    # results = opensearch_client.search(index=index_name, body=search_body)

    # similar_images = []
    # for hit in results["hits"]["hits"]:
    #     similar_images.append(
    #         {
    #             "card_id": hit["_source"]["card_id"],
    #             "similarity_score": hit["_score"],
    #         }
    #     )
