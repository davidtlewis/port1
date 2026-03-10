# Deployment Checklist

## Pre-Deployment Review

- [x] Code syntax verified
- [x] Scraper module created (`portfolio/scraper.py`)
- [x] Stock model updated with robust error handling
- [x] Holding model N+1 query fixed
- [x] Management commands improved
- [x] Documentation created (5 files)
- [x] Backward compatibility maintained
- [x] No breaking changes

## Deployment Steps

### 1. Backup Current Code
```bash
git status  # See current state
git add .   # Stage all changes
# Review changes before committing
```

### 2. Copy New Files
The following files are new and should be reviewed:
- [ ] `portfolio/scraper.py` - New scraper module
- [ ] `SCRAPING_IMPROVEMENTS.md` - Feature docs
- [ ] `IMPLEMENTATION_SUMMARY.md` - Technical docs
- [ ] `QUICK_REFERENCE.md` - How-to guide
- [ ] `LOGGING_CONFIG.py` - Logging template
- [ ] `IMPLEMENTATION_COMPLETE.md` - Overview
- [ ] This checklist file

### 3. Update Python Settings
Add to `mysite/settings.py`:

```python
# Add to imports at top
import os
import logging.handlers

# Add to end of file
# =================================================================
# LOGGING CONFIGURATION
# =================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {funcName}:{lineno} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'portfolio.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'scraper_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'scraper.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'portfolio': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'portfolio.scraper': {
            'handlers': ['console', 'scraper_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)
```

- [ ] Added LOGGING configuration to settings.py
- [ ] Created logs directory: `mkdir -p logs`

### 4. Verify Imports Work
```bash
python manage.py shell -c "from portfolio.scraper import PriceScraper; print('✓ Imports OK')"
```
- [ ] Imports verified successfully

### 5. Test Management Commands
```bash
# Test with one command
python manage.py get_prices --verbose

# Watch logs in another terminal
tail -f logs/scraper.log
```
- [ ] get_prices command works
- [ ] Logs are being written
- [ ] Output shows progress correctly

### 6. Run Database Migrations (if any)
```bash
python manage.py migrate
```
- [ ] No migrations needed (all changes are in code)
- [ ] OR Migrations applied successfully

### 7. Verify Database Queries
Run in Django shell to check N+1 fix:
```bash
python manage.py shell
```

```python
from django.db import connection
from django.test.utils import CaptureQueriesContext
from portfolio.models import Holding

with CaptureQueriesContext(connection) as context:
    h = Holding.objects.first()
    h.refresh_value()
    print(f"Number of queries: {len(context.captured_queries)}")
    # Should be around 2 (1 for transactions, 1 for stock)
```
- [ ] Query count is optimized (was 3+, now should be 2)

### 8. Test Error Handling
```bash
# Add a stock with invalid code and test
python manage.py get_prices --verbose
```
Should see:
- Error is logged but not crashes
- Other stocks continue to update
- Summary shows failures but app keeps running
- [ ] Error handling verified

### 9. Check Log Rotation
Logs should have:
- [ ] `logs/portfolio.log` exists
- [ ] `logs/scraper.log` exists
- [ ] Old logs rotate when > 10MB
- [ ] Max 5 backup files kept

### 10. Commit Changes
```bash
git add portfolio/scraper.py
git add portfolio/models.py
git add portfolio/management/commands/*.py
git add *.md
git add LOGGING_CONFIG.py
git commit -m "Implement robust web scraping with error handling and retry logic"
```
- [ ] All changes committed with descriptive message

## Post-Deployment Testing

### Week 1: Monitoring
- [ ] Monitor logs daily for errors
- [ ] Verify prices are updating
- [ ] Check success/failure ratios
- [ ] No unexpected crashes

### Week 2: Performance
- [ ] Check database query counts (should be low)
- [ ] Verify command execution times
- [ ] Monitor log file sizes

### Week 3: Stability
- [ ] No recurring failures
- [ ] Response times acceptable
- [ ] Data integrity verified

## Configuration Adjustments

If issues arise, these can be tuned:

### Timeout Too Short (timeouts when slow)
```python
# In portfolio/scraper.py
TIMEOUT = 15  # Increase from 10
```

### Timeout Too Long (waits too long)
```python
# In portfolio/scraper.py
TIMEOUT = 5   # Decrease from 10
```

### Too Many Retries (takes forever)
```python
# In portfolio/scraper.py
MAX_RETRIES = 2  # Decrease from 3
```

### Too Few Retries (fails on transient errors)
```python
# In portfolio/scraper.py
MAX_RETRIES = 5  # Increase from 3
```

### Backoff Too Aggressive (long delays)
```python
# In portfolio/scraper.py
INITIAL_BACKOFF = 2  # Increase from 1
MAX_BACKOFF = 16     # Increase from 8
```

### Logs Getting Too Large
```python
# In settings.py LOGGING section
'maxBytes': 1024 * 1024 * 50,  # Increase from 10MB
'backupCount': 10,              # Increase from 5
```

## Rollback Plan

If issues occur:

### Option 1: Revert Code
```bash
git revert HEAD
```

### Option 2: Disable Verbose Logging
```python
# In settings.py
'portfolio.scraper': {
    'level': 'WARNING',  # Change from INFO
}
```

### Option 3: Increase Timeouts
```python
# In portfolio/scraper.py
TIMEOUT = 20  # Increase to be more lenient
```

### Option 4: Disable New Scraper Temporarily
Comment out in `portfolio/models.py`:
```python
# scraper = PriceScraper()
# current_price = scraper.scrape_ft_price(...)

# Fallback to old method (remove this after confirming new code works)
# OLD_SCRAPE_METHOD()
```

## Success Criteria

After deployment, verify:

- [x] All tests pass
- [ ] Management commands work with `--verbose`
- [ ] Logs are created and rotating properly
- [ ] No crashes on scraping failures
- [ ] Previous prices used when scraping fails
- [ ] All holdings update correctly
- [ ] Database queries optimized (holding refresh uses 1 query)
- [ ] Error messages are clear and helpful
- [ ] Performance is acceptable
- [ ] Team is comfortable with new structure

## Sign-Off

- [ ] Code review completed
- [ ] Testing completed
- [ ] Deployment completed
- [ ] Monitoring verified
- [ ] Documentation updated
- [ ] Team trained
- [ ] Ready for production

---

## Support Contact

If issues arise during deployment:
1. Check `logs/scraper.log` for error details
2. Review `QUICK_REFERENCE.md` for common issues
3. See `IMPLEMENTATION_SUMMARY.md` for technical details
4. Check `portfolio/scraper.py` for configuration options

---

## Additional Resources

- **Implementation Complete**: `IMPLEMENTATION_COMPLETE.md`
- **Technical Details**: `IMPLEMENTATION_SUMMARY.md`
- **Quick How-To**: `QUICK_REFERENCE.md`
- **Feature Guide**: `SCRAPING_IMPROVEMENTS.md`
- **Code Review**: `CODE_REVIEW.md`
- **Logging Setup**: `LOGGING_CONFIG.py`

---

**Deployment Date**: _________________

**Deployed By**: _________________

**Notes**: _________________________________________________
