#!/bin/bash
# Setup script for End of Day portfolio snapshot cron job

echo "=== Portfolio End of Day Snapshot - Cron Setup ==="
echo ""
echo "This script will help you set up automated daily snapshots at 5pm."
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

# Define the cron job
CRON_JOB="45 16 * * 1-5 /home/david/port1/.venv/bin/python3 /home/david/port1/manage.py end_of_day_snapshot >> /home/david/port1/logs/eod_snapshot.log 2>&1"

echo "The following cron job will be added:"
echo ""
echo "$CRON_JOB"
echo ""
echo "This will run at 5:00 PM Monday through Friday."
echo ""
read -p "Do you want to add this cron job? (y/n) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "end_of_day_snapshot"; then
        echo ""
        echo "Warning: An end_of_day_snapshot cron job already exists!"
        echo "Existing cron jobs:"
        crontab -l | grep "end_of_day_snapshot"
        echo ""
        read -p "Do you want to replace it? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Cancelled."
            exit 0
        fi
        # Remove existing job
        crontab -l | grep -v "end_of_day_snapshot" | crontab -
    fi
    
    # Add the new cron job
    (crontab -l 2>/dev/null; echo "# Portfolio End of Day Snapshot at 5pm weekdays"; echo "$CRON_JOB") | crontab -
    
    echo ""
    echo "✓ Cron job added successfully!"
    echo ""
    echo "Current crontab:"
    crontab -l
    echo ""
    echo "Logs will be written to: /home/david/port1/logs/eod_snapshot.log"
    echo ""
    echo "To view logs: tail -f /home/david/port1/logs/eod_snapshot.log"
    echo "To edit crontab: crontab -e"
    echo "To remove cron job: crontab -e (then delete the line)"
else
    echo "Cancelled."
    exit 0
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. The snapshot will run automatically at 5pm on weekdays"
echo "2. You can test it manually: python3 manage.py end_of_day_snapshot"
echo "3. View snapshots in Django admin: /admin/portfolio/dailysnapshot/"
echo ""

