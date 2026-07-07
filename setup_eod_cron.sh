#!/bin/bash
# Setup script for End of Day portfolio snapshot cron jobs
#
# Three passes, because different prices settle at different times:
#   16:30 - FX rate only (GBPUSD / currency index are real-time, so grab them
#           right at market close rather than 15 min later)
#   16:45 - everything else (equities/ETFs/most funds, delayed ~15 min after close)
#   17:00 - late-pricing funds (NAV published after close) - retries a few times
#           if the price hasn't moved yet, then corrects the 16:45 snapshot in place

echo "=== Portfolio End of Day Snapshot - Cron Setup ==="
echo ""
echo "This script will help you set up the automated daily snapshot cron jobs."
echo ""

# Check if running as the correct user
if [ "$USER" != "david" ]; then
    echo "Warning: This script should be run as user 'david'"
    echo "Current user: $USER"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

PYTHON=/home/david/port1/.venv/bin/python3
MANAGE=/home/david/port1/manage.py
LOG=/home/david/port1/logs/eod_snapshot.log

FX_JOB="30 16 * * 1-5 $PYTHON $MANAGE end_of_day_snapshot --fx-only >> $LOG 2>&1"
MAIN_JOB="45 16 * * 1-5 $PYTHON $MANAGE end_of_day_snapshot >> $LOG 2>&1"
LATE_JOB="0 17 * * 1-5 $PYTHON $MANAGE end_of_day_snapshot --late-only >> $LOG 2>&1"

echo "The following cron jobs will be added:"
echo ""
echo "# Portfolio End of Day Snapshot - FX rate at market close"
echo "$FX_JOB"
echo "# Portfolio End of Day Snapshot - main refresh"
echo "$MAIN_JOB"
echo "# Portfolio End of Day Snapshot - late-pricing fund correction"
echo "$LATE_JOB"
echo ""
read -p "Do you want to add these cron jobs? (y/n) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Remove any existing end_of_day_snapshot jobs (old single-job setup or a previous run of this script)
    if crontab -l 2>/dev/null | grep -q "end_of_day_snapshot"; then
        echo ""
        echo "Warning: existing end_of_day_snapshot cron job(s) found - these will be replaced:"
        crontab -l | grep "end_of_day_snapshot"
        echo ""
        read -p "Continue and replace them? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Cancelled."
            exit 0
        fi
        crontab -l | grep -v "end_of_day_snapshot" | grep -v "Portfolio End of Day Snapshot" | crontab -
    fi

    (crontab -l 2>/dev/null
     echo "# Portfolio End of Day Snapshot - FX rate at market close"
     echo "$FX_JOB"
     echo "# Portfolio End of Day Snapshot - main refresh"
     echo "$MAIN_JOB"
     echo "# Portfolio End of Day Snapshot - late-pricing fund correction"
     echo "$LATE_JOB") | crontab -

    echo ""
    echo "✓ Cron jobs added successfully!"
    echo ""
    echo "Current crontab:"
    crontab -l
    echo ""
    echo "Logs will be written to: $LOG"
    echo ""
    echo "To view logs: tail -f $LOG"
    echo "To edit crontab: crontab -e"
else
    echo "Cancelled."
    exit 0
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Snapshots will now be created/corrected automatically on weekdays"
echo "2. Test manually if needed, e.g.:"
echo "   python3 manage.py end_of_day_snapshot --fx-only"
echo "   python3 manage.py end_of_day_snapshot"
echo "   python3 manage.py end_of_day_snapshot --late-only"
echo "3. View snapshots in Django admin: /admin/portfolio/dailysnapshot/"
echo ""
