# Generated by Django 5.1.6 on 2025-03-19 17:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0028_certificate"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="avatar_eyes",
            field=models.CharField(
                choices=[("round", "Round"), ("almond", "Almond"), ("narrow", "Narrow")], default="round", max_length=20
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="avatar_hair",
            field=models.CharField(
                choices=[("short", "Short"), ("long", "Long"), ("curly", "Curly"), ("bald", "Bald")],
                default="short",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="avatar_hair_color",
            field=models.CharField(
                choices=[("black", "Black"), ("brown", "Brown"), ("blonde", "Blonde"), ("red", "Red")],
                default="black",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="avatar_skin_tone",
            field=models.CharField(
                choices=[("light", "Light"), ("medium", "Medium"), ("dark", "Dark")], default="medium", max_length=20
            ),
        ),
    ]
