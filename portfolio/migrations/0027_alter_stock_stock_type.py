# Generated by Django 3.2.3 on 2021-06-21 17:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0026_stock_active'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stock',
            name='stock_type',
            field=models.CharField(choices=[('fund', 'FUND'), ('equity', 'EQUITY'), ('etfs', 'ETFS'), ('curr', 'CURR')], default='equity', max_length=6),
        ),
    ]
