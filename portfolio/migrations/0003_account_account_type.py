# Generated by Django 3.0.2 on 2020-02-03 21:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0002_auto_20200203_2054'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='account_type',
            field=models.CharField(choices=[('ISA', 'ISA'), ('pension', 'PENSION'), ('standard', 'STANDARD')], default='buy', max_length=8),
        ),
    ]
