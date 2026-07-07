from django.db import migrations

LATE_PRICING_NICKNAMES = ["Aviva UK Tracker", "Aviva World Tracker"]


def flag_late_pricing(apps, schema_editor):
    Stock = apps.get_model('portfolio', 'Stock')
    Stock.objects.filter(nickname__in=LATE_PRICING_NICKNAMES).update(late_pricing=True)


def unflag_late_pricing(apps, schema_editor):
    Stock = apps.get_model('portfolio', 'Stock')
    Stock.objects.filter(nickname__in=LATE_PRICING_NICKNAMES).update(late_pricing=False)


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0036_stock_late_pricing'),
    ]

    operations = [
        migrations.RunPython(flag_late_pricing, unflag_late_pricing),
    ]
