# Generated by Django 5.1 on 2025-01-07 15:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('github', '0004_alter_githubauthor_email_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='githubbranch',
            name='repository',
            field=models.CharField(db_index=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='githubcommit',
            name='repository',
            field=models.CharField(db_index=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='githubissue',
            name='repository',
            field=models.CharField(db_index=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='githubpullrequest',
            name='repository',
            field=models.CharField(db_index=True, default='', max_length=255),
        ),
    ]
