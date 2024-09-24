python manage.py makemigrations
python manage.py migrate --no-input

python manage.py createsuperuser --no-input --username $DJANGO_SUPERUSER_USERNAME --email $DJANGO_SUPERUSER_EMAIL

python manage.py runserver 0.0.0.0:8000
