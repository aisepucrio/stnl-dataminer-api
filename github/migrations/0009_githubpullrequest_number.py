# Generated by Django 5.1 on 2025-01-16 17:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('github', '0008_alter_githubmethod_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='githubpullrequest',
            name='number',
            field=models.IntegerField(null=True, unique=True),
        ),
    ]
