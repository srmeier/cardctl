import zipfile

from django.core.exceptions import ValidationError
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


def validate_zip_file(value):
    try:
        with zipfile.ZipFile(value) as zf:
            zf.testzip()
    except zipfile.BadZipFile:
        raise ValidationError("Invalid zip file.")


def validate_file_size(value):
    limit = 150 * 1024 * 1024
    if value.size > limit:
        raise ValidationError("File size must be less than 150 MB.")


class CtlUserBatch(models.Model):
    class ScanOrder(models.IntegerChoices):
        FRONT_ONLY = 1, "Front Only"
        FRONT_BACK_FF = 2, "Front & Back - Front First"
        FRONT_BACK_BF = 3, "Front & Back - Back First"

    name = models.CharField(max_length=200)
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
    )
    task_id = models.UUIDField(default=None, null=True, blank=True)
    card_scans = models.FileField(
        upload_to="ctluserbatch__card_scans",
        validators=[validate_zip_file, validate_file_size],
    )
    scan_order = models.IntegerField(choices=ScanOrder)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Batch"
        verbose_name_plural = "Batches"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def card_count(self) -> int:
        return CtlUserCard.objects.filter(batch=self).count()


class CtlUserCard(models.Model):
    batch = models.ForeignKey(
        CtlUserBatch,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    ref = models.ForeignKey(
        CtlRefCard,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
    )
    accepted = models.BooleanField(default=None, null=True, blank=True)
    front = models.ImageField(upload_to="ctlusercard__front")
    back = models.ImageField(upload_to="ctlusercard__back", null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User card"
        verbose_name_plural = "User cards"
        ordering = ["ref__name"]

    def __str__(self):
        if self.ref is None:
            return "Unidentified"
        return self.ref.name
