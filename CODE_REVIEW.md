# Code Review: Django Investment Portfolio Tracker

## Executive Summary
This is a Django project that tracks stock and investment holdings across multiple accounts. The codebase is functional but has several areas for improvement regarding security, performance, code quality, and maintainability.

---

## Critical Issues

### 1. **Security: Hardcoded Credentials in Settings** ⚠️ CRITICAL
**File:** `mysite/settings.py`
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'portfolio',
        'USER': 'portfolio',
        'PASSWORD': 'mervan',  # ← Exposed password!
        'HOST': 'localhost',
        'PORT': '3306',
    }
}

SECRET_KEY = '4n63e7wpm@knc6v1h^45t812+=e@z%l_s^p8)^s(#45)6*4kz2'  # ← Exposed secret key!
```

**Recommendations:**
- Use environment variables or a `.env` file (via `python-dotenv`)
- Move credentials to environment variables using `os.environ.get()`
- Never commit credentials to version control

**Example Fix:**
```python
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '3306'),
    }
}
```

### 2. **Security: Debug Mode in Production**
**File:** `mysite/settings.py`
```python
DEBUG = True  # Dangerous in production!
```

**Recommendations:**
```python
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
```

### 3. **Security: SQL Injection Risk in Web Scraping**
**File:** `portfolio/models.py` - `Stock.refresh_value()` and `Stock.refresh_perf()`

The code dynamically constructs URLs based on `self.code`, which could be vulnerable if not properly validated. While BeautifulSoup mitigates HTML injection, you should validate/sanitize the code field.

---

## High Priority Issues

### 4. **Web Scraping: Fragile HTML Parsing** ⚠️ IMPORTANT CAVEAT
**Files:** `portfolio/models.py` (multiple methods)

**Problem:** Hard-coded CSS selectors and table indices are brittle and will break when websites update their HTML structure.

```python
# Current approach - FRAGILE
scrapped_element = soup.find_all("span", class_='mod-ui-data-list__value')[0].string
scrapped_5y_perf = soup.find("div", class_='mod-ui-table--freeze-pane__scroll-container').find_all("tr")[1].find_all("td")[1].string
```

**Reality Check on UK Stock APIs:**
Your question is excellent. For UK quoted stocks (LSE), the situation is:

1. **Yahoo Finance** - Works via `yfinance` library, supports UK stocks, but:
   - Free API, intended for research/educational use only
   - Limited to historical data and closing prices
   - May have rate limits and blocking issues
   - Does NOT reliably provide real-time prices

2. **Financial Times (your current scraper)** - Provides real-time prices but:
   - No official API
   - HTML scraping is the only option
   - Subject to frequent breaking changes

3. **Official LSE/Refinitiv APIs** - Exist but require:
   - Paid subscriptions (expensive)
   - Professional/institutional accounts
   - Not practical for personal projects

4. **Other free options:**
   - **Alpha Vantage** - Limited, requires API key, has free tier but with strict rate limits
   - **IEX Cloud** - Good but primarily US-focused
   - **Twelve Data** - Supports UK stocks but limited free tier

**Recommendation:**
Since you're relying on FT data and it works for your use case, **keep the scraping approach BUT make it more robust:**

```python
def refresh_value(self):
    if not self.active or self.code == 'none':
        return
    
    try:
        url = self._build_url()
        price = self._fetch_price_with_retry(url, max_retries=3)
        if price:
            self.current_price = price
            self.price_updated = timezone.now()
            self.save()
            logger.info(f"Updated {self.nickname}: {price}")
    except ScrapingFailedException as e:
        logger.warning(f"Failed to scrape {self.nickname}: {e}")
        # Keep previous price, alert user instead of crashing
    except Exception as e:
        logger.error(f"Unexpected error refreshing {self.nickname}: {e}")

def _fetch_price_with_retry(self, url, max_retries=3):
    """Fetch price with retry logic and better error handling"""
    for attempt in range(max_retries):
        try:
            session = HTMLSession()
            page = session.get(url, timeout=10)  # Add timeout
            if page.status_code != 200:
                raise ScrapingFailedException(f"HTTP {page.status_code}")
            
            soup = BeautifulSoup(page.content, 'html.parser')
            # Try to parse with validation
            price = self._parse_price_from_soup(soup)
            if price and price > 0:
                return price
            
        except requests.Timeout:
            logger.warning(f"Timeout on attempt {attempt+1}/{max_retries} for {self.nickname}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            continue
        except Exception as e:
            logger.error(f"Attempt {attempt+1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            continue
    
    raise ScrapingFailedException(f"Failed after {max_retries} attempts")

def _parse_price_from_soup(self, soup):
    """Parse price with better error handling"""
    try:
        elements = soup.find_all("span", class_='mod-ui-data-list__value')
        if not elements:
            raise ScrapingFailedException("Price element not found")
        
        scrapped_price_str = elements[0].string
        if not scrapped_price_str:
            raise ScrapingFailedException("Price text is empty")
        
        price = locale.atof(scrapped_price_str)
        return price
    except (AttributeError, ValueError) as e:
        raise ScrapingFailedException(f"Parse error: {e}")

class ScrapingFailedException(Exception):
    """Raised when web scraping fails"""
    pass
```

**Additional Improvements:**
1. **Add caching** - Don't scrape if price was updated recently (< 1 hour)
2. **Add User-Agent rotation** - Some websites block requests that look robotic
3. **Monitor for changes** - Log when CSS selectors stop working, alert maintainers
4. **Implement graceful degradation** - Use cached/stale prices if scraping fails
5. **Use background tasks** - Move scraping to Celery, not request-response cycle

### 5. **Performance: N+1 Query Problem**
**File:** `portfolio/models.py` - `Holding.refresh_value()`

```python
def refresh_value(self):
    transactions = Transaction.objects.filter(stock=self.stock).filter(account=self.account)
    # Two separate database queries
    nett_volume_bought = transactions.filter(transaction_type='buy').aggregate(Sum('volume'))['volume__sum']
    nett_volume_sold = transactions.filter(transaction_type='sell').aggregate(Sum('volume'))['volume__sum']
```

**Better approach:**
```python
def refresh_value(self):
    transactions = Transaction.objects.filter(
        stock=self.stock,
        account=self.account
    ).aggregate(
        bought=Sum('volume', filter=Q(transaction_type='buy')),
        sold=Sum('volume', filter=Q(transaction_type='sell'))
    )
    
    nett_volume_bought = transactions['bought'] or 0
    nett_volume_sold = transactions['sold'] or 0
    self.volume = nett_volume_bought - nett_volume_sold
    # ... rest of method
```

### 6. **Performance: Web Scraping in Views/Models**
**Issue:** `Stock.refresh_value()` makes HTTP requests synchronously. If a website is slow, the entire Django request blocks.

**Recommendations:**
- Move scraping to **Celery tasks** or background jobs
- Use `management.py` commands called via scheduled tasks (cron/APScheduler)
- Add a `last_refresh_attempt` field to track retry logic

### 7. **Code Quality: Magic Numbers and Hard-Coded Values**
**File:** `portfolio/models.py`

```python
# Unclear: What's 135 batches? Why not parameterized?
batch = 135

# Hard-coded 2017 date for historical data
if last_date_record is None:
    last_date = date(2017, 1, 1)
```

**Recommendations:**
```python
BATCH_SIZE_DAYS = 135  # historical batch size
MIN_HISTORY_DATE = date(2017, 1, 1)

batch = settings.BATCH_SIZE_DAYS
```

### 8. **Code Quality: Repetitive Code in `refresh_perf()`**
**File:** `portfolio/models.py`

The performance scraping code repeats the same pattern 6 times:
```python
scrapped_5y_perf = soup.find(...).find_all(...)[1].find_all(...)[1].string
if scrapped_5y_perf != '--': self.perf_5y = locale.atof(scrapped_5y_perf[:-1])
# ... repeated 5 more times
```

**Refactor:**
```python
def refresh_perf(self):
    if self.stock_type in ('equity', 'curr'):
        return
    
    perf_fields = {
        'perf_5y': 1,
        'perf_3y': 2,
        'perf_1y': 3,
        'perf_6m': 4,
        'perf_3m': 5,
        'perf_1m': 6,
    }
    
    try:
        url = self._build_perf_url()
        soup = self._fetch_and_parse(url)
        rows = soup.find(...).find_all(...)
        
        for field_name, col_index in perf_fields.items():
            value_str = rows[1].find_all("td")[col_index].string
            if value_str and value_str != '--':
                setattr(self, field_name, locale.atof(value_str[:-1]))
        
        self.save()
    except Exception as e:
        logger.error(f"Failed to refresh performance for {self.nickname}: {e}")
```

---

## Medium Priority Issues

### 9. **Model Validation: No Validation on Stock Code**
**File:** `portfolio/models.py`

```python
class Stock(models.Model):
    code = models.CharField(max_length=20)  # No validation
```

**Recommendation:**
```python
from django.core.validators import RegexValidator

code = models.CharField(
    max_length=20,
    validators=[RegexValidator(r'^[A-Z0-9\-\.]+$', 'Only alphanumeric, dash, and period allowed')]
)
```

### 10. **Logging: No Logging Framework**
Files with print statements: `portfolio/models.py`, `portfolio/management/commands/`

**Problem:** `print()` statements aren't captured by production logging systems.

**Recommendation:**
```python
import logging

logger = logging.getLogger(__name__)

# Instead of:
print(f"Refreshing {self.nickname}.")

# Use:
logger.info(f"Refreshing {self.nickname}.")
logger.error(f"Failed to scrape: {e}")
```

### 11. **Views: Locale Settings in Model Methods**
**File:** `portfolio/models.py`

```python
def refresh_value(self):
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
```

**Problem:** Setting locale in model methods is not thread-safe and causes issues in concurrent environments.

**Recommendation:**
```python
from decimal import Decimal
import locale

def convert_to_decimal(value_str, current_locale='en_US.UTF-8'):
    """Convert string to Decimal using specified locale"""
    with locale.temporary_locale(current_locale):
        return Decimal(locale.atof(value_str))
```

### 12. **Database: Missing Indexes**
**File:** `portfolio/models.py`

Models that need index optimization:
```python
class Transaction(models.Model):
    account = models.ForeignKey(Account, db_index=True)  # Frequently filtered
    stock = models.ForeignKey(Stock, db_index=True)      # Frequently filtered
    date = models.DateField(db_index=True)               # Frequently sorted

class Holding(models.Model):
    stock = models.ForeignKey(Stock, db_index=True)
    account = models.ForeignKey(Account, db_index=True)
```

### 13. **Views: Filtering Logic Should Be in QuerySets**
**File:** `portfolio/views.py`

```python
def detailed_summary(request):
    # Hard-coded person names in view
    a = Account.objects.filter(person__name = "david") | Account.objects.filter(person__name = "henri")
```

**Better approach - use Manager:**
```python
class AccountManager(models.Manager):
    def for_users(self, user_names):
        from django.db.models import Q
        query = Q()
        for name in user_names:
            query |= Q(person__name=name)
        return self.filter(query)

class Account(models.Model):
    objects = AccountManager()
    # ...

# In view:
a = Account.objects.for_users(['david', 'henri'])
```

### 14. **Views: Missing Login Protection**
**File:** `portfolio/views.py`

Many views don't have `@login_required` decorator but should:
```python
class StockListView(SingleTableView, FilterView):  # No auth required!
    model = Stock
    table_class = StockTable
    template_name = 'portfolio/stock.html'
```

**Recommendation:**
```python
from django.contrib.auth.mixins import LoginRequiredMixin

class StockListView(LoginRequiredMixin, SingleTableView, FilterView):
    login_url = '/account/login/'
    # ...
```

### 15. **Models: Unused Field**
**File:** `portfolio/models.py`

```python
class Price(models.Model):
    # This model appears unused - holding.refresh_value() uses Stock.current_price instead
    # Consider removing or clarifying its purpose
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, null=True)
    date = models.DateTimeField(auto_now_add=True)
    price = models.DecimalField(max_digits=7, decimal_places=2)
```

---

## Low Priority Issues

### 16. **Code Style: Inconsistent Naming**
- `yahoo_code` vs `code` (camelCase vs snake_case)
- `tcost` should be `transaction_cost`
- `nett_volume` should be `net_volume`

### 17. **Type Hints Missing**
```python
# Add type hints for better IDE support and documentation
def refresh_value(self) -> None:
    # ...

def convert_to_decimal(value_str: str) -> Decimal:
    # ...
```

### 18. **Documentation: Missing Docstrings**
Most model methods lack documentation:
```python
def refresh_value(self):
    """
    Calculate current holdings value based on stock price.
    Updates volume from transaction history and refreshes related account values.
    """
    # ...
```

### 19. **Management Commands: No Error Handling**
**File:** `portfolio/management/commands/get_prices.py`

```python
def handle(self, *args, **options):
    stock_list = Stock.objects.filter(active=True)
    for s in stock_list:
        s.refresh_value()  # What if this raises an exception?
```

**Recommendation:**
```python
def handle(self, *args, **options):
    stock_list = Stock.objects.filter(active=True)
    total = len(stock_list)
    failed = []
    
    for idx, stock in enumerate(stock_list, 1):
        try:
            stock.refresh_value()
            self.stdout.write(self.style.SUCCESS(f'[{idx}/{total}] {stock.nickname}'))
        except Exception as e:
            failed.append((stock.nickname, str(e)))
            self.stdout.write(self.style.ERROR(f'[{idx}/{total}] {stock.nickname} - {e}'))
    
    if failed:
        self.stdout.write(self.style.WARNING(f'\n{len(failed)} stocks failed to update'))
```

### 20. **Requirements.txt: Pinned Versions**
Good that versions are pinned, but some very old versions should be updated:
- `Django==4.0.4` (current is 5.x)
- `beautifulsoup4==4.11.1` (current is 4.12.x)
- `requests==2.27.1` (current is 2.31.x)

---

## Suggested Refactoring Priority

**Phase 1 (Do Immediately):**
1. Move credentials to environment variables
2. Set `DEBUG = False` for production
3. Add `@login_required` to views
4. Add basic logging

**Phase 2 (High Value):**
1. Refactor web scraping to use API instead of HTML parsing
2. Move scraping to background tasks (Celery)
3. Add comprehensive error handling
4. Fix N+1 query problems

**Phase 3 (Code Quality):**
1. Add type hints
2. Add docstrings
3. Extract magic numbers to settings
4. Improve logging throughout

**Phase 4 (Long-term):**
1. Add unit tests
2. Add integration tests
3. Consider REST API instead of HTML views
4. Consider switching to PostgreSQL (better than MySQL for Django)

---

## Specific Recommendations by File

### `mysite/settings.py`
- Use environment variables for all secrets
- Add a `.env.example` file to git (without actual values)
- Separate development/production settings
- Add `ALLOWED_HOSTS` from environment

### `portfolio/models.py`
- Extract scraping logic to separate service/utility module
- Add proper error handling and logging
- Use database indexes on frequently queried fields
- Add `__repr__` methods for better debugging
- Consider adding model validation with `clean()` method

### `portfolio/views.py`
- Add `LoginRequiredMixin` to views
- Move complex queries to custom managers
- Add proper pagination to all list views
- Consider using generic views more consistently

### `portfolio/management/commands/`
- Add proper error handling in all commands
- Add progress indication for long-running tasks
- Return exit codes properly

---

## Testing Recommendations

Create a test suite with:
```
tests/
├── test_models.py      # Model logic and calculations
├── test_views.py       # View logic
├── test_scraping.py    # Web scraping functions
└── test_commands.py    # Management commands
```

Example test:
```python
from django.test import TestCase
from portfolio.models import Holding, Transaction, Account, Stock

class HoldingRefreshValueTestCase(TestCase):
    def setUp(self):
        self.account = Account.objects.create(name="Test Account")
        self.stock = Stock.objects.create(
            name="Test Stock",
            code="TEST",
            current_price=100.00
        )
    
    def test_refresh_value_calculates_correct_volume(self):
        Transaction.objects.create(
            account=self.account,
            stock=self.stock,
            transaction_type='buy',
            volume=10
        )
        Transaction.objects.create(
            account=self.account,
            stock=self.stock,
            transaction_type='sell',
            volume=3
        )
        
        holding = Holding.objects.create(
            account=self.account,
            stock=self.stock,
            volume=0
        )
        holding.refresh_value()
        
        self.assertEqual(holding.volume, 7)
```

---

## Summary

The codebase is functional but needs improvement in:
1. **Security** (credentials, debug mode, authentication)
2. **Performance** (N+1 queries, synchronous scraping)
3. **Maintainability** (error handling, logging, code organization)
4. **Reliability** (brittle HTML parsing, missing validation)

Following these recommendations will make the project more robust, maintainable, and production-ready.
