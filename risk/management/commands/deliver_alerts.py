import time
from django.core.management.base import BaseCommand, CommandError
from risk.webhooks import deliver_pending

class Command(BaseCommand):
    help = 'Entrega a caixa de saída com assinatura HMAC e até cinco tentativas.'
    def add_arguments(self, parser):
        parser.add_argument('--watch', action='store_true')
    def handle(self, *args, **options):
        try:
            while True:
                try: self.stdout.write(str(deliver_pending()))
                except ValueError as exc: raise CommandError(str(exc))
                if not options['watch']: break
                time.sleep(10)
        except KeyboardInterrupt:
            self.stdout.write('Worker encerrado.')
