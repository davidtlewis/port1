# Generated by Django 3.0.3 on 2020-04-18 15:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0020_auto_20200417_0925'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='historicprice',
            options={'ordering': ['date']},
        ),
        migrations.CreateModel(
            name='Dividend',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(blank=True)),
                ('amount', models.DecimalField(decimal_places=8, max_digits=10)),
                ('stock', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='portfolio.Stock')),
            ],
        ),
    ]