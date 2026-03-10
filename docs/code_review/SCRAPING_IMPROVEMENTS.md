# Scraping Improvements Summary

## Overview
This document outlines the improvements made to the web scraping and data refresh functionality of the portfolio tracker.

## Key Improvements

### 1. **New Scraper Module** (`portfolio/scraper.py`)
A dedicated module for all web scraping functionality with robust error handling.

#### Features:
- **Retry Logic with Exponential Backoff**
  - Automatic retry on timeout or failure
  - Exponential backoff (1s, 2s, 4s, 8s max)
  - Configurable max retries (default: 3)

- **Timeout Protection**
  - 10-second timeout on all HTTP requests
  - Prevents hanging/blocking requests

- **Better Error Handling**
  - Custom exception hierarchy (`ScraperException`, `ScraperTimeoutException`, `ScraperParseException`)
  - Meaningful error messages
  - Graceful fallback to previous prices

- **Logging**
  - Replaces `print()` statements with proper logging
  - Structured logging at different levels (DEBUG, INFO, WARNING, ERROR)
  - Logs failed attempts and retry actions

- **User-Agent Rotation**
  - Identifies requests as regular browser
  - Helps avoid being blocked by FT and Yahoo

- **Cleaner Code Structure**
  - Separated concerns (FT vs Yahoo scraping)
  - Reusable methods with clear responsibilities
  - Easy to maintain and extend

#### Classes:
1. **PriceScraper**
   - Handles current price scraping from FT and Yahoo
   - Methods: `scrape_ft_price()`, `scrape_yahoo_price()`

2. **PerformanceScraper**
   - Handles performance data (5y, 3y, 1y, 6m, 3m, 1m returns) from FT
   - Method: `scrape_performance()`

### 2. **Updated Stock Model** (`portfolio/models.py`)

#### `refresh_value()` Method:
**Before:**
- No error handling - crashes on failure
- `print()` statements instead of logging
- Inline HTML scraping logic
- Falls back to old price on error (confusing)

**After:**
- Uses new `PriceScraper` class
- Proper logging at all stages
- Handles ScraperException gracefully
- Keeps previous price on failure (better UX)
- Always refreshes related holdings
- Better code organization

```python
def refresh_value(self):
    """Refresh the current price with proper error handling"""
    if not self.active or self.code == 'none':
        return
    
    try:
        scraper = PriceScraper()
        current_price = scraper.scrape_ft_price(self.code, self.stock_type)
        
        if current_price and current_price > 0:
            self.current_price = current_price
            self.price_updated = timezone.now()
            self.save()
    except ScraperException as e:
        logger.error(f"Failed to refresh price: {e}")
        # Keeps existing price rather than crashing
    finally:
        self._refresh_related_holdings()
```

#### `refresh_perf()` Method:
**Before:**
- Repetitive code (6 nearly identical blocks)
- No error handling
- Hard-coded table indices

**After:**
- Uses new `PerformanceScraper` class
- DRY principle - data-driven approach
- Proper error handling and logging
- More maintainable

### 3. **Fixed N+1 Query Problem** in `Holding.refresh_value()`

**Before:**
```python
transactions = Transaction.objects.filter(stock=self.stock).filter(account=self.account)
nett_volume_bought = transactions.filter(transaction_type='buy').aggregate(Sum('volume'))['volume__sum']
nett_volume_sold = transactions.filter(transaction_type='sell').aggregate(Sum('volume'))['volume__sum']
# 3+ database queries!
```

**After:**
```python
transactions = Transaction.objects.filter(
    stock=self.stock,
    account=self.account
).aggregate(
    bought=Sum('volume', filter=Q(transaction_type='buy')),
    sold=Sum('volume', filter=Q(transaction_type='sell'))
)
# Single optimized query!
```

### 4. **Improved Management Commands**

All management commands now include:
- Better error handling with try/except
- Failure tracking and reporting
- Summary statistics at the end
- Progress tracking (e.g., `[15/100]`)
- `--verbose` flag for debugging
- Formatted output with styling

#### Updated Commands:
- `python manage.py get_prices` - Scrape current prices
- `python manage.py refresh_accounts` - Refresh account totals
- `python manage.py refresh_holdings` - Refresh holding values

Example output:
```
[1/45]: Scraping MSFT
[2/45]: Scraping AAPL
...
======================================================================
✓ Successfully updated: 43/45
✗ Failed: 2/45
  - Delisted Stock: Failed after 3 attempts
  - Invalid Ticker: Parse error
======================================================================
```

## Usage Examples

### Enable Logging
Configure logging in `settings.py`:
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'portfolio.log',
        },
    },
    'loggers': {
        'portfolio': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'portfolio.scraper': {
            'level': 'DEBUG',  # More verbose scraper logging
        },
    },
}
```

### Run with Verbose Logging
```bash
python manage.py get_prices --verbose
```

### Monitor Scraping
```bash
tail -f portfolio.log | grep scraper
```

## Benefits

1. **Reliability**
   - Automatic retries handle transient failures
   - Timeouts prevent hanging requests
   - Graceful degradation when scraping fails

2. **Maintainability**
   - Centralized scraping logic
   - Clear error handling
   - Proper logging for debugging

3. **Performance**
   - Fixed N+1 query problem in holdings
   - Single database query per refresh
   - User-Agent helps avoid rate limiting

4. **Observability**
   - Structured logging instead of print statements
   - Can monitor failures and retry patterns
   - Debug mode available

5. **Extensibility**
   - Easy to add new scraper sources
   - Clean separation of concerns
   - Reusable scraper classes

## Future Improvements

1. **Caching**
   - Cache prices for 1 hour to reduce hits to FT
   - Only refresh if price is > 1 hour old

2. **Background Tasks**
   - Use Celery to move scraping out of request cycle
   - Schedule periodic updates via celery-beat

3. **Monitoring**
   - Alert on persistent scraping failures
   - Track FT/Yahoo downtime
   - Metrics on success/failure rates

4. **Alternative APIs**
   - Evaluate premium APIs for UK stocks
   - Consider data feeds if available

5. **Testing**
   - Unit tests for scraper classes with mocked responses
   - Integration tests for model refresh methods
   - Test failure scenarios and retries

## Troubleshooting

### Common Issues

**Issue:** Scraping fails with "Price element not found"
- **Cause:** FT/Yahoo changed their HTML structure
- **Solution:** Update CSS selectors in scraper classes, add debug logging

**Issue:** Timeout errors
- **Cause:** Network issues or slow servers
- **Solution:** Automatic retry should handle this; check network connectivity

**Issue:** "User-Agent blocked"
- **Cause:** Too many requests from same IP
- **Solution:** Implement request caching or rate limiting

## Code Quality

- **Type hints**: Used for better IDE support
- **Docstrings**: Comprehensive documentation
- **Error handling**: Custom exceptions for different failure modes
- **Logging**: Replaces all print statements
- **Testing**: Structure allows for easy unit testing
