# Generated by Django 3.0.2 on 2020-02-07 12:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0010_auto_20200207_1219'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stock',
            name='price_updated',
            field=models.DateTimeField(null=True),
        ),
    ]
