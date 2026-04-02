web: python manage.py migrate --noinput && python manage.py collectstatic --noinput && python reset_password.py && gunicorn config.wsgi --bind 0.0.0.0:$PORT
