# Generated by Django 3.1.5 on 2021-04-10 17:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0023_auto_20200821_1522'),
    ]

    operations = [
        migrations.AddField(
            model_name='stock',
            name='stock_region',
            field=models.CharField(choices=[('world', 'WORLD'), ('us', 'US'), ('uk', 'UK')], default='world', max_length=6),
        ),
    ]
