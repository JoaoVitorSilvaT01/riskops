from django.core.management.base import BaseCommand, CommandError
from risk.models import Incident
from risk.services import verify_chain

class Command(BaseCommand):
    help = 'Verifica a cadeia de hashes de todas as ocorrências.'
    def handle(self, *args, **options):
        invalid = [str(i.id) for i in Incident.objects.all() if not verify_chain(i)]
        if invalid: raise CommandError('Cadeias inválidas: ' + ', '.join(invalid))
        self.stdout.write(self.style.SUCCESS(f'{Incident.objects.count()} cadeias verificadas.'))
