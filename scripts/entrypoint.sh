#!/bin/sh

set -e

python3 manange.py collecstatic --noinput

uwsgi --socket :8000 --master --enable-threads --module invoices.wsgi
