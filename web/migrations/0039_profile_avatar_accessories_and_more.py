from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("web", "0038_coursematerial_due_date_and_more"),
    ]

    operations = [
        # Add all final field definitions in one go
        migrations.AddField(
            model_name="profile",
            name="avatar_accessory",
            field=models.CharField(default="none", max_length=50),
        ),
        migrations.AddField(
            model_name="profile",
            name="avatar_background_color",
            field=models.CharField(default="#FFFFFF", max_length=7),
        ),
        migrations.AddField(
            model_name="profile",
            name="avatar_clothing",
            field=models.CharField(default="hoodie", max_length=50),
        ),
        migrations.AddField(
            model_name="profile",
            name="avatar_clothing_color",
            field=models.CharField(default="#0000FF", max_length=7),
        ),
        migrations.AddField(
            model_name="profile",
            name="avatar_eyebrows",
            field=models.CharField(default="default", max_length=50),
        ),
        migrations.AddField(
            model_name="profile",
            name="avatar_eyes",
            field=models.CharField(default="default", max_length=50),
        ),
        migrations.AddField(
            model_name="profile",
            name="avatar_facial_hair",
            field=models.CharField(default="none", max_length=50),
        ),
        migrations.AddField(
            model_name="profile",
            name="avatar_hair_color",
            field=models.CharField(default="#000000", max_length=7),
        ),
        migrations.AddField(
            model_name="profile",
            name="avatar_mouth",
            field=models.CharField(default="default", max_length=50),
        ),
        migrations.AddField(
            model_name="profile",
            name="avatar_nose",
            field=models.CharField(default="default", max_length=50),
        ),
        migrations.AddField(
            model_name="profile",
            name="avatar_skin_color",
            field=models.CharField(default="light", max_length=50),
        ),
        migrations.AddField(
            model_name="profile",
            name="avatar_style",
            field=models.CharField(default="circle", max_length=50),
        ),
        migrations.AddField(
            model_name="profile",
            name="avatar_svg",
            field=models.TextField(blank=True, help_text="Stored SVG string of the custom avatar"),
        ),
        migrations.AddField(
            model_name="profile",
            name="avatar_top",
            field=models.CharField(default="short_flat", max_length=50),
        ),
        # Final avatar field configuration
        migrations.AlterField(
            model_name="profile",
            name="avatar",
            field=models.ImageField(blank=True, upload_to="avatars"),
        ),
    ]
