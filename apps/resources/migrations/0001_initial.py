import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Facility",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=255, verbose_name="name")),
                (
                    "type",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=100,
                        verbose_name="type",
                    ),
                ),
                (
                    "location",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=255,
                        verbose_name="location",
                    ),
                ),
            ],
            options={
                "verbose_name": "facility",
                "verbose_name_plural": "facilities",
                "db_table": "facilities",
                "ordering": ("name",),
            },
        ),
    ]
