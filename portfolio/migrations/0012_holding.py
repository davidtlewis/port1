# Generated by Django 3.0.2 on 2020-02-07 13:31

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0011_auto_20200207_1229'),
    ]

    operations = [
        migrations.CreateModel(
            name='Holding',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('volume', models.IntegerField()),
                ('book_cost', models.DecimalField(decimal_places=2, max_digits=10)),
                ('value', models.DecimalField(decimal_places=2, max_digits=10)),
                ('account', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='portfolio.Account')),
                ('stock', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='portfolio.Stock')),
            ],
        ),
    ]