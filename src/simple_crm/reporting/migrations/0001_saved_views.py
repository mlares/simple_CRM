from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("simple_crm_identity", "0002_seed_roles"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SavedView",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=120)),
                ("definition", models.JSONField(default=dict)),
                (
                    "visibility",
                    models.CharField(
                        choices=[("PRIVATE", "Privada"), ("SHARED", "Compartida")],
                        default="PRIVATE",
                        max_length=12,
                    ),
                ),
                ("version", models.PositiveIntegerField(default=1)),
                ("is_archived", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="saved_views_approved",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="saved_views",
                        to="simple_crm_identity.identityprofile",
                    ),
                ),
            ],
            options={
                "verbose_name": "Vista guardada",
                "verbose_name_plural": "Vistas guardadas",
                "ordering": ("name", "pk"),
            },
        ),
        migrations.AddConstraint(
            model_name="savedview",
            constraint=models.CheckConstraint(
                condition=models.Q(("name__gt", "")),
                name="reporting_saved_view_name_not_empty",
            ),
        ),
        migrations.AddConstraint(
            model_name="savedview",
            constraint=models.CheckConstraint(
                condition=models.Q(("visibility", "PRIVATE"))
                | models.Q(("approved_by__isnull", False)),
                name="reporting_shared_view_approved",
            ),
        ),
    ]
