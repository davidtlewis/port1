# Generated by Django 3.0.2 on 2020-02-07 15:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0012_holding'),
    ]

    operations = [
        migrations.RenameField(
            model_name='holding',
            old_name='value',
            new_name='current_value',
        ),
    ]