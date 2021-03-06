# Generated by Django 3.0.3 on 2020-02-12 11:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0014_stock_nickname'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='account_value',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=9),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='tcost',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
    ]
