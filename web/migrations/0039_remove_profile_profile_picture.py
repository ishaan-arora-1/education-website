# Generated by Django 5.1.6 on 2025-03-22 23:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0038_profile_profile_picture'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='profile_picture',
        ),
    ]
