from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("web", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="allow_individual_sessions",
            field=models.BooleanField(
                default=False,
                help_text="Allow students to register for individual sessions",
            ),
        ),
    ]
