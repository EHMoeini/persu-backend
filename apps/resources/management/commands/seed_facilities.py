"""Seed the database with realistic mock facility listings."""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.resources.mock_data import (
    MOCK_FACILITIES,
    RETIRED_MOCK_FACILITY_KEYS,
    mock_facility_id,
)
from apps.resources.models import Facility


class Command(BaseCommand):
    help = (
        "Create or update the mock facility listings used to exercise the "
        "search API. Existing non-mock facilities are never modified."
    )

    def add_arguments(self, parser) -> None:
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--reset",
            action="store_true",
            help=(
                "Delete the previously seeded mock listings, including "
                "retired English mock rows, before creating them again. Real "
                "facilities are not affected."
            ),
        )
        group.add_argument(
            "--if-empty",
            action="store_true",
            help=(
                "Only seed when there are no real facilities. Existing mock "
                "rows are updated, retired mock rows are removed, and newly "
                "defined listings are added to a database seeded by an older "
                "version. This is used by the deployment startup script and "
                "never adds mock rows to a database that has real facilities."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        current_ids = [
            mock_facility_id(str(item["key"])) for item in MOCK_FACILITIES
        ]
        retired_ids = [
            mock_facility_id(key) for key in RETIRED_MOCK_FACILITY_KEYS
        ]
        known_mock_ids = current_ids + retired_ids

        if options["if_empty"] and Facility.objects.exclude(
            pk__in=known_mock_ids
        ).exists():
            self.stdout.write(
                "Real facilities already exist; skipping mock seed."
            )
            return

        if options["reset"]:
            deleted, _ = Facility.objects.filter(
                pk__in=known_mock_ids
            ).delete()
            self.stdout.write(f"Deleted {deleted} seeded mock listing(s).")
        else:
            deleted, _ = Facility.objects.filter(pk__in=retired_ids).delete()
            if deleted:
                self.stdout.write(
                    f"Deleted {deleted} retired mock listing(s)."
                )

        created = 0
        updated = 0
        for item in MOCK_FACILITIES:
            defaults = {
                field: value
                for field, value in item.items()
                if field != "key"
            }
            _, was_created = Facility.objects.update_or_create(
                pk=mock_facility_id(str(item["key"])),
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded mock facilities: {created} created, {updated} updated."
            )
        )
