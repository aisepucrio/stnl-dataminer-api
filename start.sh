# Wait for the database
echo "Waiting for database to be ready..."
until nc -z db 5432; do
    echo "Database not ready yet. Retrying in 2 seconds..."
    sleep 2
done
echo "Database is ready."

# Apply migrations
echo "Applying migrations..."
python manage.py makemigrations
python manage.py migrate --no-input
if [ $? -ne 0 ]; then
    echo "Error: Failed to apply migrations."
    exit 1
fi
echo "Migrations applied successfully."

echo "Collecting static files..."
python manage.py collectstatic --no-input
echo "Static files collected successfully."

# Create superuser
echo "Checking for superuser..."
python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
if not User.objects.filter(username='${DJANGO_SUPERUSER_USERNAME}').exists():
    User.objects.create_superuser('${DJANGO_SUPERUSER_USERNAME}', '${DJANGO_SUPERUSER_EMAIL}', '${DJANGO_SUPERUSER_PASSWORD}')
" && echo "Superuser created successfully." || echo "Superuser already exists or failed to create."

# Start the server
if [ "$IS_DEBUG" = "False" ]; then
    echo "Starting Django server with gunicorn (IS_DEBUG=False)..."
    gunicorn dataminer_api.wsgi:application --bind 0.0.0.0:8000
else
    echo "Starting Django development server (IS_DEBUG=True)..."
    python manage.py runserver 0.0.0.0:8000
fi