# Generated by Django 5.1.6 on 2025-03-22 23:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0039_remove_profile_profile_picture"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="avatar",
            field=models.ImageField(blank=True, default="", upload_to="avatars"),
        ),
    ]
