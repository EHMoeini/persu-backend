"""Idempotent management command to import real scraped Iranian sports facilities."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.resources.models import Facility


class Command(BaseCommand):
    help = "Import or update scraped Iranian sports facilities from apps/resources/fixtures/facilities.json"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--file",
            type=str,
            default="",
            help="Optional custom path to facilities.json fixture",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing Facility rows before importing",
        )

    def handle(self, *args, **options) -> None:
        default_path = (
            Path(__file__).resolve().parents[2] / "fixtures" / "facilities.json"
        )
        path = Path(options["file"]) if options["file"] else default_path
        if not path.exists():
            self.stderr.write(self.style.ERROR(f"Fixture not found: {path}"))
            return

        data = json.loads(path.read_text(encoding="utf-8"))
        if options["clear"]:
            Facility.objects.all().delete()

        objs = []
        for item in data:
            if item.get("model") != "resources.facility":
                continue
            fields = dict(item["fields"])
            price_irr = fields.get("price_irr")
            toman = Decimal(price_irr // 10) if price_irr else Decimal("0")
            raw_rating = fields.get("rating")
            rating_val = Decimal(str(round(min(max(float(raw_rating), 0.0), 5.0), 1))) if raw_rating else Decimal("0.0")

            fields.setdefault("category", fields.get("type", "")[:100])
            fields["price"] = toman
            fields["rating"] = rating_val
            fields.setdefault("picture", fields.get("image_url", "")[:500])
            fields.setdefault("availability", True)
            objs.append(Facility(id=item["pk"], **fields))

        with transaction.atomic():
            Facility.objects.bulk_create(
                objs,
                batch_size=500,
                update_conflicts=True,
                unique_fields=["id"],
                update_fields=[
                    "name",
                    "description",
                    "category",
                    "type",
                    "location",
                    "price",
                    "picture",
                    "rating",
                    "availability",
                    "city",
                    "province",
                    "district",
                    "address",
                    "latitude",
                    "longitude",
                    "phone",
                    "price_irr",
                    "price_display",
                    "rating_count",
                    "opening_hours",
                    "sports",
                    "amenities",
                    "gender",
                    "image_url",
                    "source_name",
                    "source_url",
                    "external_id",
                ],
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(objs)} scraped facilities (total in DB: {Facility.objects.count()})."
            )
        )
