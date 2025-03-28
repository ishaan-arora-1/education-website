# Generated by Django 5.1.6 on 2025-03-25 04:36

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0032_rename_completion_date_teamgoalmember_completed_at_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='VirtualClassroom',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('grid_rows', models.IntegerField(default=5)),
                ('grid_columns', models.IntegerField(default=6)),
                ('is_active', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('session', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='virtual_classroom', to='web.session')),
            ],
        ),
        migrations.CreateModel(
            name='UpdateRound',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('duration', models.IntegerField(help_text='Duration in seconds')),
                ('is_active', models.BooleanField(default=True)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('completed_speakers', models.ManyToManyField(related_name='completed_rounds', to=settings.AUTH_USER_MODEL)),
                ('current_speaker', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='speaking_rounds', to=settings.AUTH_USER_MODEL)),
                ('classroom', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='update_rounds', to='web.virtualclassroom')),
            ],
            options={
                'ordering': ['-started_at'],
            },
        ),
        migrations.CreateModel(
            name='ScreenShare',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('share_type', models.CharField(choices=[('screenshot', 'Screenshot'), ('live', 'Live Share')], max_length=10)),
                ('content', models.ImageField(blank=True, null=True, upload_to='screen_shares/')),
                ('live_share_url', models.URLField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='screen_shares', to=settings.AUTH_USER_MODEL)),
                ('classroom', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='screen_shares', to='web.virtualclassroom')),
            ],
        ),
        migrations.CreateModel(
            name='VirtualHand',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('raised_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('selected_for_speaking', models.BooleanField(default=False)),
                ('classroom', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='raised_hands', to='web.virtualclassroom')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='hand_raises', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['raised_at'],
            },
        ),
        migrations.CreateModel(
            name='VirtualSeat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('row', models.IntegerField()),
                ('column', models.IntegerField()),
                ('is_occupied', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('classroom', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='seats', to='web.virtualclassroom')),
                ('student', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='virtual_seats', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['row', 'column'],
                'unique_together': {('classroom', 'row', 'column')},
            },
        ),
    ]
