web: bash bin/get_git_hash.sh && gunicorn invoices.wsgi --log-file -
worker: bash bin/get_git_hash.sh && python worker.py
events: bash bin/get_git_hash.sh && python clock.py
worker: bash bin/get_git_hash.sh && python manage.py rqworker
