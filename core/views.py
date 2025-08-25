import json
from os import getenv

import requests
import torch
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, DetailView, ListView
from opensearchpy import OpenSearch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor
from transformers.models.clip.modeling_clip import CLIPOutput

from .models import CtlCardSet, CtlRefCard, CtlUserCard


@csrf_exempt
def index(request: HttpRequest):
    if request.method == "POST":
        # NOTE: Instead of leveraging n8n, Airtable, and gotoHuman for this just leverage Django with a few forms and views
        # NOTE: I can create a similar experience but with more control (will just need to figure out the UI/UX)

        data: dict = json.loads(request.body.decode("utf-8"))
        print(json.dumps(data, indent=4))

        device = "cpu"  # "cuda" if torch.cuda.is_available() else "cpu"
        model = CLIPModel.from_pretrained(
            "openai/clip-vit-base-patch32",
            torch_dtype=torch.bfloat16,
            attn_implementation="sdpa",
        ).to(device)
        processor = CLIPProcessor.from_pretrained(
            "openai/clip-vit-base-patch32", use_fast=False
        )
        index_name = "ctlrefcards"
        images = [
            Image.open(requests.get(card.get("url"), stream=True).raw)
            for card in data.get("front", [])
        ]
        texts = [""] * len(images)
        inputs = processor(text=texts, images=images, return_tensors="pt", padding=True)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        outputs: CLIPOutput = model(**inputs)
        embeddings = outputs.image_embeds.detach().cpu().tolist()
        opensearch_client = OpenSearch(
            hosts=[
                {"host": getenv("OPENSEARCH_HOST"), "port": getenv("OPENSEARCH_PORT")}
            ],
            http_compress=True,
            http_auth=(getenv("OPENSEARCH_USERNAME"), getenv("OPENSEARCH_PASSWORD")),
            use_ssl=True,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
        )
        hits = []
        for embedding in embeddings:
            search_body = {
                "size": 5,
                "query": {"knn": {"embedding": {"vector": embedding, "k": 5}}},
            }
            results = opensearch_client.search(index=index_name, body=search_body)
            similar_images = []
            for hit in results["hits"]["hits"]:
                similar_images.append(
                    {
                        "id": hit["_source"]["card_id"],
                        "metadata": CtlRefCard.objects.get(
                            id=hit["_source"]["card_id"]
                        ).metadata,
                        "similarity_score": hit["_score"],
                    }
                )
            hits.append(similar_images)

        return JsonResponse({"id": data.get("id"), "results": hits})

    return render(request, "core/index.html")


class CtlCardSetListView(LoginRequiredMixin, ListView):
    model = CtlCardSet


class CtlUserCardListView(LoginRequiredMixin, ListView):
    model = CtlUserCard


class CtlUserCardCreateView(LoginRequiredMixin, CreateView):
    model = CtlUserCard
    success_url = reverse_lazy("cards")
    fields = ["front", "back"]

    def form_valid(self, form):
        instance: CtlUserCard = form.instance
        instance.user = self.request.user
        return super().form_valid(form)
