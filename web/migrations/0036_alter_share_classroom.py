# Generated by Django 5.1.6 on 2025-03-27 11:31

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0035_share_delete_screenshare'),
    ]

    operations = [
        migrations.AlterField(
            model_name='share',
            name='classroom',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='screen_shares', to='web.virtualclassroom'),
        ),
    ]
