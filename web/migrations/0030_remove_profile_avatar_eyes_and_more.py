# Generated by Django 5.1.6 on 2025-03-19 17:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0029_profile_avatar_eyes_profile_avatar_hair_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="profile",
            name="avatar_eyes",
        ),
        migrations.RemoveField(
            model_name="profile",
            name="avatar_hair",
        ),
        migrations.RemoveField(
            model_name="profile",
            name="avatar_hair_color",
        ),
        migrations.RemoveField(
            model_name="profile",
            name="avatar_skin_tone",
        ),
        migrations.AddField(
            model_name="profile",
            name="avatar_background",
            field=models.CharField(
                choices=[
                    ("b6e3f4", "Light Blue"),
                    ("c0aede", "Lavender"),
                    ("d1d4f9", "Periwinkle"),
                    ("ffd5dc", "Pink"),
                    ("ffdfbf", "Peach"),
                    ("d1f4d9", "Mint"),
                    ("f9f9f9", "Light Gray"),
                ],
                default="f9f9f9",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="avatar_seed",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="profile",
            name="avatar_style",
            field=models.CharField(
                choices=[
                    ("adventurer", "Adventurer"),
                    ("adventurer-neutral", "Adventurer Neutral"),
                    ("avataaars", "Avataaars"),
                    ("big-ears", "Big Ears"),
                    ("big-smile", "Big Smile"),
                    ("bottts", "Bottts"),
                    ("croodles", "Croodles"),
                    ("fun-emoji", "Fun Emoji"),
                    ("micah", "Micah"),
                    ("miniavs", "Mini Avatars"),
                    ("open-peeps", "Open Peeps"),
                    ("pixel-art", "Pixel Art"),
                ],
                default="avataaars",
                max_length=30,
            ),
        ),
    ]
