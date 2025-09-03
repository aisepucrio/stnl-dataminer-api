from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0004_auto_20250819_1952"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="date_init",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="task",
            name="date_end",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="task",
            name="date_last_update",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="task",
            name="type",
            field=models.CharField(max_length=100),
        ),
    ]
