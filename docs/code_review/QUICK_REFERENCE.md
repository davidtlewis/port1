# Quick Reference: Using the Improved Scraper

## Running Management Commands

### Get Latest Prices
```bash
# Standard run
python manage.py get_prices

# With verbose logging (shows all retries, timeouts, etc)
python manage.py get_prices --verbose

# Output example:
# [1/45]: Scraping MSFT
# [2/45]: Scraping AAPL
# ======================================================================
# ✓ Successfully updated: 43/45
# ✗ Failed: 2/45
#   - DelListed: Failed after 3 attempts
# ======================================================================
```

### Refresh Account Values
```bash
python manage.py refresh_accounts

# Output shows each account and its total value
# [1/3]: Refreshing ISA Account
#        Value: £125,432.50
```

### Refresh Holding Values
```bash
python manage.py refresh_holdings

# Output shows each holding with volume and value
# [1/50]: MSFT / ISA Account
#        Volume: 100, Value: £15,234.50
```

---

## Monitoring Logs

### Watch Scraper Log in Real-time
```bash
tail -f logs/scraper.log
```

### See Only Errors
```bash
grep ERROR logs/scraper.log | tail -20
```

### See Only Warnings
```bash
grep WARNING logs/scraper.log | tail -20
```

### Count Failures in Last Hour
```bash
grep "Failed to refresh" logs/scraper.log | tail -1000 | wc -l
```

### Find Which Stocks Failed
```bash
grep "Failed to refresh price for" logs/scraper.log | grep -o "for.*:" | sort | uniq -c
```

---

## Common Issues & Solutions

### Issue: "Failed after 3 attempts"
**Cause:** FT or Yahoo is not responding
**Solution:** 
- Try again in a few minutes
- Check if FT/Yahoo are down
- Check your internet connection
- Verify stock code is correct

### Issue: "Price element not found"
**Cause:** FT changed their HTML structure
**Solution:**
- This is expected occasionally as websites update
- Run again - usually resolves
- If persistent, may need CSS selector update
- Check `portfolio/scraper.py` for selector definitions

### Issue: Timeout errors
**Cause:** Network is slow or server is overloaded
**Solution:**
- Automatic retry with backoff should handle this
- Check network connectivity
- Try running again later

### Issue: Script takes a very long time
**Cause:** Scraping is waiting for websites to respond
**Solution:**
- Normal during high load
- Check logs: `tail -f logs/scraper.log`
- See progress updates on screen
- Ctrl+C to stop if needed

---

## Configuration

### Change Retry Settings
Edit `portfolio/scraper.py`:
```python
class PriceScraper:
    MAX_RETRIES = 3           # Change to 5 for more attempts
    INITIAL_BACKOFF = 1       # Change to 2 for longer initial wait
    TIMEOUT = 10              # Change to 15 for slower networks
```

### Change Logging Level
Edit `LOGGING_CONFIG` in `settings.py`:
```python
'portfolio.scraper': {
    'level': 'DEBUG',  # Change from INFO to DEBUG for more detail
}
```

---

## Scheduling Updates

### Using Django-extensions
```bash
# Setup (one time)
pip install django-extensions

# Run in background
python manage.py runserver_plus --keep-alive

# In another terminal, run updates periodically
while true; do
    python manage.py get_prices
    python manage.py refresh_accounts
    sleep 3600  # Run every hour
done
```

### Using Celery (Recommended for Production)
See `SCRAPING_IMPROVEMENTS.md` for future Celery setup.

### Using Cron (Linux/Mac)
```bash
# Edit crontab
crontab -e

# Add this to run every hour
0 * * * * cd /home/david/port1 && python manage.py get_prices

# Run every 6 hours
0 */6 * * * cd /home/david/port1 && python manage.py get_prices

# Run at 9 AM every weekday
0 9 * * 1-5 cd /home/david/port1 && python manage.py get_prices
```

---

## Debugging

### Enable Debug Logging Temporarily
```python
# In Django shell or management command
import logging
logging.getLogger('portfolio.scraper').setLevel(logging.DEBUG)
```

### Test Scraper Directly
```python
# In Django shell
python manage.py shell

from portfolio.scraper import PriceScraper

scraper = PriceScraper()
price = scraper.scrape_ft_price('MSFT:USD', 'equity')
print(f"MSFT price: {price}")
```

### Check Stock Configuration
```python
# In Django shell
from portfolio.models import Stock

s = Stock.objects.get(nickname='MSFT')
print(f"Code: {s.code}")
print(f"Source: {s.scraper_source}")
print(f"Type: {s.stock_type}")
print(f"Active: {s.active}")
print(f"Last updated: {s.price_updated}")
print(f"Current price: {s.current_price}")
```

---

## Performance Tips

### Speed up refresh_holdings
If you have many holdings:
```bash
# Run in background with verbose logging
python manage.py refresh_holdings --verbose > update.log 2>&1 &
```

### Monitor Database Queries
In development, enable query logging:
```python
# In settings.py
LOGGING['loggers']['django.db.backends'] = {
    'handlers': ['console'],
    'level': 'DEBUG',
}
```

### Bulk Updates
For very large portfolios, consider scheduling off-peak hours:
```bash
# Late night update (2 AM)
0 2 * * * cd /home/david/port1 && python manage.py get_prices
```

---

## Troubleshooting Checklist

- [ ] Run with `--verbose` flag for more detail
- [ ] Check `logs/scraper.log` for actual error messages
- [ ] Verify stock codes are correct
- [ ] Check internet connectivity
- [ ] Verify FT/Yahoo are not down
- [ ] Try one problem stock directly in Django shell
- [ ] Check if CSS selectors have changed (FT updates website)
- [ ] Review error type (timeout vs parse vs network)
- [ ] Check database connection
- [ ] Verify sufficient disk space for logs

---

## Useful Django Shell Commands

```python
# In Django shell: python manage.py shell

# Refresh one stock
from portfolio.models import Stock
s = Stock.objects.get(nickname='MSFT')
s.refresh_value()

# Refresh all active stocks
from portfolio.models import Stock
for s in Stock.objects.filter(active=True):
    s.refresh_value()

# Check for stocks with old prices
from django.utils import timezone
from datetime import timedelta
from portfolio.models import Stock

old_stocks = Stock.objects.filter(
    active=True,
    price_updated__lt=timezone.now() - timedelta(hours=24)
)
for s in old_stocks:
    print(f"{s.nickname}: {s.price_updated}")

# Find failing stocks (no update attempt)
from portfolio.models import Stock
failing = Stock.objects.filter(active=True, price_updated__isnull=True)
for s in failing:
    print(f"{s.nickname}: Never updated")

# Get portfolio total value
from portfolio.models import Account
from django.db.models import Sum

total = Account.objects.aggregate(Sum('account_value'))
print(f"Total portfolio value: £{total['account_value__sum']:,.2f}")
```

---

## Getting Help

1. **Check the logs:** `tail -f logs/scraper.log`
2. **Read documentation:** `SCRAPING_IMPROVEMENTS.md`
3. **Review code comments:** `portfolio/scraper.py`
4. **See implementation details:** `IMPLEMENTATION_SUMMARY.md`
5. **Search in Django shell:** Try the debugging commands above
