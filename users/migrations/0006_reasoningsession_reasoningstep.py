# Generated by Django 5.2 on 2025-04-24 23:28

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_chatmessage'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ReasoningSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_complete', models.BooleanField(default=False)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reasoning_sessions', to='users.project')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ReasoningStep',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('step_number', models.PositiveIntegerField()),
                ('step_type', models.CharField(choices=[('planning', 'Planning'), ('analysis', 'Analysis'), ('code_generation', 'Code Generation'), ('code_execution', 'Code Execution'), ('testing', 'Testing'), ('refinement', 'Refinement'), ('conclusion', 'Conclusion')], max_length=50)),
                ('prompt', models.TextField()),
                ('response', models.TextField(blank=True)),
                ('model_used', models.CharField(default='gpt-4o', max_length=50)),
                ('tool_calls', models.JSONField(blank=True, null=True)),
                ('tool_results', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_complete', models.BooleanField(default=False)),
                ('error', models.TextField(blank=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='steps', to='users.reasoningsession')),
            ],
            options={
                'ordering': ['session', 'step_number'],
                'unique_together': {('session', 'step_number')},
            },
        ),
    ]
