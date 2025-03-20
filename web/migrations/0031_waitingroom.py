# Generated by Django 5.1.6 on 2025-03-20 15:55

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0030_quiz_quizquestion_quizoption_userquiz"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="WaitingRoom",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("subject", models.CharField(max_length=100)),
                ("topics", models.TextField(help_text="Comma-separated list of topics")),
                ("status", models.CharField(
                    choices=[("open", "Open"), ("closed", "Closed"), ("fulfilled", "Fulfilled")],
                    default="open",
                    max_length=10,
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("creator", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="created_waiting_rooms",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("participants", models.ManyToManyField(
                    blank=True,
                    related_name="joined_waiting_rooms",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
