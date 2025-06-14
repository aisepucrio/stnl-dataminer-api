from django.core.management.base import BaseCommand
from stackoverflow.functions.data_populator import populate_missing_data
from django.conf import settings

class Command(BaseCommand):
    help = 'Populate missing user data from Stack Exchange API'

    def handle(self, *args, **options):
        api_key = settings.STACK_EXCHANGE_API_KEY
        access_token = settings.STACK_EXCHANGE_ACCESS_TOKEN
        
        if not api_key or not access_token:
            self.stdout.write(self.style.ERROR('Stack Exchange API key or access token not found in settings'))
            return
            
        self.stdout.write(self.style.SUCCESS('Starting user data population...'))
        populate_missing_data(api_key, access_token)
        self.stdout.write(self.style.SUCCESS('User data population completed')) 