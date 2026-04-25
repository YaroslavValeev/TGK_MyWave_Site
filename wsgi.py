"""
Production WSGI: один источник правды вместе с main.py.
Gunicorn:  gunicorn -c gunicorn.conf.py main:app
или:        gunicorn -c gunicorn.conf.py wsgi:application
"""
from main import app as application

# Совместимость с unit-тестами / uwsgi-стилем
app = application
