web: gunicorn invoices.wsgi --log-file -
worker: python worker.py
events: python clock.py
worker: celery -A inur worker --loglevel=info

