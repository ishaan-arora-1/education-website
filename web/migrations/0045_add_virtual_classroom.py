# Create file: web/migrations/XXXX_add_virtual_classroom.py

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0044_waitingroom_fulfilled_course'),  # Add the previous migration here
    ]

    operations = [
        migrations.CreateModel(
            name='VirtualClassroom',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rows', models.PositiveSmallIntegerField(default=5)),
                ('columns', models.PositiveSmallIntegerField(default=6)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('session', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='virtual_classroom', to='web.session')),
            ],
        ),
        migrations.CreateModel(
            name='VirtualSeat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('row', models.PositiveSmallIntegerField()),
                ('column', models.PositiveSmallIntegerField()),
                ('status', models.CharField(choices=[('empty', 'Empty'), ('occupied', 'Occupied'), ('speaking', 'Speaking'), ('hand_raised', 'Hand Raised')], default='empty', max_length=20)),
                ('assigned_at', models.DateTimeField(blank=True, null=True)),
                ('classroom', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='seats', to='web.virtualclassroom')),
                ('student', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='virtual_seats', to='auth.user')),
            ],
            options={
                'ordering': ['row', 'column'],
                'unique_together': {('classroom', 'row', 'column')},
            },
        ),
        migrations.CreateModel(
            name='UpdateRound',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('duration_seconds', models.PositiveSmallIntegerField(default=120)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('ended_at', models.DateTimeField(blank=True, null=True)),
                ('classroom', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='update_rounds', to='web.virtualclassroom')),
            ],
            options={
                'ordering': ['-started_at'],
            },
        ),
        migrations.CreateModel(
            name='SharedContent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content_type', models.CharField(choices=[('screenshot', 'Screenshot'), ('document', 'Document'), ('link', 'Link')], max_length=20)),
                ('file', models.FileField(blank=True, null=True, upload_to='virtual_classroom/shared/')),
                ('link', models.URLField(blank=True)),
                ('description', models.TextField(blank=True)),
                ('shared_at', models.DateTimeField(auto_now_add=True)),
                ('seat', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shared_content', to='web.virtualseat')),
            ],
            options={
                'ordering': ['-shared_at'],
            },
        ),
        migrations.CreateModel(
            name='HandRaise',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('raised_at', models.DateTimeField(auto_now_add=True)),
                ('lowered_at', models.DateTimeField(blank=True, null=True)),
                ('acknowledged', models.BooleanField(default=False)),
                ('seat', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='hand_raises', to='web.virtualseat')),
            ],
            options={
                'ordering': ['raised_at'],
            },
        ),
        migrations.CreateModel(
            name='UpdateTurn',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('ended_at', models.DateTimeField(blank=True, null=True)),
                ('seat', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='update_turns', to='web.virtualseat')),
                ('update_round', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='turns', to='web.updateround')),
            ],
            options={
                'ordering': ['started_at'],
            },
        ),
    ]
