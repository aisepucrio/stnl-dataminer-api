# Generated by Django 5.1 on 2025-01-16 18:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('github', '0009_githubpullrequest_number'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='githubpullrequest',
            name='id',
        ),
        migrations.AddField(
            model_name='githubpullrequest',
            name='closed_at',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='githubpullrequest',
            name='merged_at',
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name='githubpullrequest',
            name='creator',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='githubpullrequest',
            name='number',
            field=models.IntegerField(null=True),
        ),
        migrations.AlterField(
            model_name='githubpullrequest',
            name='pr_id',
            field=models.IntegerField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='githubpullrequest',
            name='repository',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='githubpullrequest',
            name='state',
            field=models.CharField(max_length=50),
        ),
        migrations.AlterModelTable(
            name='githubpullrequest',
            table='github_pull_requests',
        ),
    ]
