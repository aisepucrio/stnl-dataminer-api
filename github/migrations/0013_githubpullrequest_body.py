# Generated by Django 5.1 on 2025-02-18 13:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('github', '0012_alter_githubissue_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='githubpullrequest',
            name='body',
            field=models.TextField(blank=True, null=True),
        ),
    ]
