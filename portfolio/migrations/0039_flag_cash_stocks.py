from django.db import migrations

CASH_NICKNAMES = ["Bank", "P2P"]


def flag_cash(apps, schema_editor):
    Stock = apps.get_model('portfolio', 'Stock')
    Stock.objects.filter(nickname__in=CASH_NICKNAMES).update(is_cash=True)


def unflag_cash(apps, schema_editor):
    Stock = apps.get_model('portfolio', 'Stock')
    Stock.objects.filter(nickname__in=CASH_NICKNAMES).update(is_cash=False)


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0038_stock_is_cash'),
    ]

    operations = [
        migrations.RunPython(flag_cash, unflag_cash),
    ]
