web: gunicorn invoices.wsgi --log-file -
worker: python worker.py
events: python clock.py
worker: python manage.py rqworker
worker: node ./node_service/server.js
web: honcho start
