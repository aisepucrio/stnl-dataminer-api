from django.core.management.base import BaseCommand
from stackoverflow.functions.data_populator import main

class Command(BaseCommand):
    help = 'Run the data population main function'

    def handle(self, *args, **options):
        main() 