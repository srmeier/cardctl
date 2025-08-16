from django.db import models


class CtlCardSet(models.Model):
    class Source(models.TextChoices):
        TCDB = "https://www.tcdb.com", "Trading Card Database"
        TCGCSV = "https://tcgcsv.com", "TCGCSV"
        POKEMON = "https://api.pokemontcg.io", "Pokémon TCG API"
        SCRYFALL = "https://api.scryfall.com", "Scryfall API"

    name = models.CharField(max_length=200)
    source = models.CharField(max_length=50, choices=Source)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Card set"
        verbose_name_plural = "Card sets"
        ordering = ["name"]

    def __str__(self):
        return self.name


class CtlRefCard(models.Model):
    name = models.CharField(max_length=200)
    card_set = models.ForeignKey(CtlCardSet, on_delete=models.CASCADE)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Reference card"
        verbose_name_plural = "Reference cards"
        ordering = ["card_set", "name"]

    def __str__(self):
        return f"{self.card_set} - {self.name}"
