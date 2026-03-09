#!/bin/bash
screen -dmS django bash -c 'source /home/david/.env/django2/bin/activate && cd /home/david/port1 && python3 manage.py runserver 0.0.0.0:8000'
