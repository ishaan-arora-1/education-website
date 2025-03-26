# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0045_add_virtual_classroom'),
    ]

    operations = [
        migrations.AddField(
            model_name='virtualseat',
            name='laptop_open',
            field=models.BooleanField(default=False),
        ),
    ]
