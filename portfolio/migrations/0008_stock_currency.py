# Generated by Django 3.0.2 on 2020-02-07 08:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0007_auto_20200206_2014'),
    ]

    operations = [
        migrations.AddField(
            model_name='stock',
            name='currency',
            field=models.CharField(choices=[('gbp', 'GBP'), ('gbx', 'GBX'), ('usd', 'USD')], default='equity', max_length=6),
        ),
    ]
