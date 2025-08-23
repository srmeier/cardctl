from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.generic import ListView

from .models import CtlCardSet


def index(request):
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
    return render(request, "core/index.html")


class CtlCardSetListView(LoginRequiredMixin, ListView):
    model = CtlCardSet
