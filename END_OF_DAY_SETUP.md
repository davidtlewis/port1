# End of Day Snapshot - Setup Guide

## Overview

The end-of-day snapshot system automatically captures daily portfolio values at market close (5pm) and stores them for historical tracking.

## What Gets Captured

Each daily snapshot includes:
- **Total portfolio values** in GBP, USD, and Currency Index
- **H&D (David & Henri) portfolio values** in all three currencies
- **Exchange rates** (GBP/USD and Currency Index) at snapshot time
- **Timestamp** of when the snapshot was created

## Manual Usage

### Run End-of-Day Snapshot

```bash
# Activate virtual environment
source /home/david/.env/django2/bin/activate

# Run with full refresh (recommended for daily use)
python3 manage.py end_of_day_snapshot

# Run without refreshing prices (uses current values)
python3 manage.py end_of_day_snapshot --skip-refresh

# Run for a specific date
python3 manage.py end_of_day_snapshot --date 2026-03-08

# Run with verbose logging
python3 manage.py end_of_day_snapshot --verbose
```

### What the Command Does

1. **Refreshes stock prices** - Gets latest prices from FT/Yahoo Finance
2. **Refreshes holdings** - Recalculates holding values based on new prices
3. **Refreshes account values** - Updates total account values
4. **Creates snapshot** - Saves the portfolio state to the database

## Automated Scheduling with Cron

### Option 1: Using crontab (Recommended)

1. Open your crontab:
```bash
crontab -e
```

2. Add this line to run at 5:00 PM every weekday (Mon-Fri):
```cron
# End of day portfolio snapshot at 5pm (market close)
0 17 * * 1-5 cd /home/david/port1 && /home/david/.env/django2/bin/python3 manage.py end_of_day_snapshot >> /home/david/port1/logs/eod_snapshot.log 2>&1
```

3. For weekend snapshots at 5pm on Saturday (to capture Friday's close):
```cron
# Weekend portfolio snapshot at 5pm Saturday
0 17 * * 6 cd /home/david/port1 && /home/david/.env/django2/bin/python3 manage.py end_of_day_snapshot >> /home/david/port1/logs/eod_snapshot.log 2>&1
```

4. Save and exit (Ctrl+X, then Y, then Enter in nano)

### Option 2: Using systemd timer (Alternative)

Create a systemd service and timer for more control.

**Service file:** `/etc/systemd/system/portfolio-eod.service`
```ini
[Unit]
Description=Portfolio End of Day Snapshot
After=network.target

[Service]
Type=oneshot
User=david
WorkingDirectory=/home/david/port1
Environment="PATH=/home/david/.env/django2/bin:/usr/bin"
ExecStart=/home/david/.env/django2/bin/python3 manage.py end_of_day_snapshot
StandardOutput=append:/home/david/port1/logs/eod_snapshot.log
StandardError=append:/home/david/port1/logs/eod_snapshot.log

[Install]
WantedBy=multi-user.target
```

**Timer file:** `/etc/systemd/system/portfolio-eod.timer`
```ini
[Unit]
Description=Run Portfolio EOD Snapshot at 5pm weekdays

[Timer]
OnCalendar=Mon-Fri 17:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:
```bash
sudo systemctl enable portfolio-eod.timer
sudo systemctl start portfolio-eod.timer
sudo systemctl status portfolio-eod.timer
```

## Viewing Snapshots

### In Django Admin

1. Go to http://your-server/admin
2. Navigate to "Portfolio" → "Daily Snapshots"
3. View all historical snapshots

### Via Command Line

```bash
source /home/david/.env/django2/bin/activate
python3 manage.py shell -c "
from portfolio.models import DailySnapshot
snapshots = DailySnapshot.objects.all()[:10]
for s in snapshots:
    print(f'{s.date}: GBP £{s.total_value_gbp:,.2f}, USD \${s.total_value_usd:,.2f}')
"
```

## Logs

Logs are written to:
- **Application logs:** `/home/david/port1/logs/portfolio.log`
- **EOD snapshot logs:** `/home/david/port1/logs/eod_snapshot.log` (if using cron)

View recent logs:
```bash
tail -f /home/david/port1/logs/eod_snapshot.log
```

## Troubleshooting

### Snapshot already exists
If you see "Snapshot for [date] already exists", the snapshot has already been created for that day. This prevents duplicates.

### Failed to refresh prices
If price scraping fails, the command will continue with existing prices and create the snapshot anyway.

### Missing exchange rates
If GBPUSD or Currency Index stocks are not found, the system will use a rate of 1.0 as fallback.

## Database Model

The `DailySnapshot` model stores:
- `date` - Snapshot date (unique)
- `snapshot_time` - When snapshot was created
- `total_value_gbp` - Total portfolio in GBP
- `total_value_usd` - Total portfolio in USD
- `total_value_currency_index` - Total portfolio in Currency Index units
- `hd_value_gbp` - H&D portfolio in GBP
- `hd_value_usd` - H&D portfolio in USD
- `hd_value_currency_index` - H&D portfolio in Currency Index units
- `gbp_usd_rate` - GBP/USD exchange rate
- `currency_index_rate` - Currency Index value

