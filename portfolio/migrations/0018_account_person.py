# Generated by Django 3.0.3 on 2020-04-13 13:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0017_auto_20200413_1340'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='person',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='portfolio.Person'),
        ),
    ]
