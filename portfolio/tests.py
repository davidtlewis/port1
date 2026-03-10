from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from portfolio.models import DailySnapshot
from portfolio.templatetags.portfolio_extras import signed_thousands_k, thousands_k


class PortfolioExtrasTests(SimpleTestCase):
    def test_thousands_k_formats_values(self):
        self.assertEqual(thousands_k(7144894), '7,145k')

    def test_signed_thousands_k_formats_positive_and_negative_values(self):
        self.assertEqual(signed_thousands_k(12345), '+12k')
        self.assertEqual(signed_thousands_k(-12345), '-12k')
        self.assertEqual(signed_thousands_k(0), '0k')


class DailySnapshotsViewTests(TestCase):
    def create_snapshot(self, day):
        return DailySnapshot.objects.create(
            date=date(2026, 3, day),
            total_value_gbp=Decimal(f'{1000 + day}.00'),
            total_value_usd=Decimal(f'{1200 + day}.00'),
            total_value_currency_index=Decimal(f'{1190 + day}.00'),
            hd_value_gbp=Decimal(f'{700 + day}.00'),
            hd_value_usd=Decimal(f'{840 + day}.00'),
            hd_value_currency_index=Decimal(f'{833 + day}.00'),
            gbp_usd_rate=Decimal('1.2000'),
            currency_index_rate=Decimal('1.1900'),
        )

    def test_daily_snapshots_view_renders_in_descending_date_order(self):
        older = self.create_snapshot(8)
        newer = self.create_snapshot(9)

        response = self.client.get(reverse('daily_snapshots'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portfolio/daily_snapshots.html')
        self.assertEqual(list(response.context['snapshots']), [newer, older])
        self.assertContains(response, '2026-03-09')
        self.assertContains(response, '2026-03-08')
        self.assertContains(response, '1,320.00')

    def test_daily_snapshots_view_is_paginated(self):
        for day in range(1, 28):
            self.create_snapshot(day)

        first_page = self.client.get(reverse('daily_snapshots'))
        second_page = self.client.get(reverse('daily_snapshots'), {'page': 2})

        self.assertEqual(first_page.status_code, 200)
        self.assertTrue(first_page.context['is_paginated'])
        self.assertEqual(len(first_page.context['snapshots']), 25)
        self.assertContains(first_page, '2026-03-27')
        self.assertNotContains(first_page, '2026-03-02')

        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(list(second_page.context['snapshots'])[0].date, date(2026, 3, 2))
        self.assertContains(second_page, '2026-03-02')
        self.assertContains(second_page, '2026-03-01')
