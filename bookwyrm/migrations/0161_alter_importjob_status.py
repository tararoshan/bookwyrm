# Generated by Django 3.2.15 on 2022-11-05 20:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bookwyrm", "0160_auto_20221105_2030"),
    ]

    operations = [
        migrations.AlterField(
            model_name="importjob",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("active", "Active"),
                    ("complete", "Complete"),
                    ("stopped", "Stopped"),
                ],
                default="pending",
                max_length=50,
                null=True,
            ),
        ),
    ]