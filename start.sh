# Esperar pelo banco de dados
echo "Waiting for database to be ready..."
until nc -z db 5432; do
    echo "Database not ready yet. Retrying in 2 seconds..."
    sleep 2
done
echo "Database is ready."

# Aplicar migrações
echo "Applying migrations..."
python manage.py makemigrations
python manage.py migrate --no-input
if [ $? -ne 0 ]; then
    echo "Error: Failed to apply migrations."
    exit 1
fi
echo "Migrations applied successfully."

# Criar superusuário
echo "Checking for superuser..."
python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@admin.com', 'adminpassword')
" && echo "Superuser created successfully." || echo "Superuser already exists or failed to create."

# Iniciar o servidor
echo "Starting Django development server..."
python manage.py runserver 0.0.0.0:8000