import json
import os
import statistics
import time
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from risk.policies import POLICY_VERSION, baseline
from risk.providers import ProviderError, analyze, provider_info

class Command(BaseCommand):
    help = 'Compara baseline e motor em cenários sintéticos; preserva divergências.'
    def add_arguments(self, parser):
        parser.add_argument('--provider', choices=['rules', 'gemini', 'openai'], default='rules')
        parser.add_argument('--output', default='evaluation/results.json')
    def handle(self, *args, **options):
        cases = json.loads((settings.BASE_DIR / 'evaluation/cases.json').read_text(encoding='utf-8'))
        original = os.environ.get('AI_PROVIDER')
        os.environ['AI_PROVIDER'] = options['provider']
        try:
            if not provider_info()['configured']: raise CommandError('Configure a chave do provedor no .env antes da avaliação.')
            engines = []
            for name in ['baseline', options['provider']]:
                rows, times = [], []
                for case in cases:
                    started = time.perf_counter()
                    error, actual = None, None
                    try: actual = baseline(case['report']) if name == 'baseline' else analyze(case['report'])['effective_priority']
                    except ProviderError as exc: error = str(exc)
                    elapsed = round((time.perf_counter() - started) * 1000, 2)
                    times.append(elapsed)
                    rows.append({'id': case['id'], 'title': case['title'], 'tag': case['tag'], 'expected': case['priority'],
                                 'actual': actual, 'correct': actual == case['priority'], 'error': error, 'latency_ms': elapsed})
                    self.stdout.write(f'{name}: {case["id"]} {actual or "ERROR"} / referência {case["priority"]}')
                success = [r for r in rows if not r['error']]
                critical = [r for r in rows if r['expected'] == 'P1']
                matrix = {expected: {actual: sum(r['expected'] == expected and r['actual'] == actual for r in rows)
                                    for actual in ['P1', 'P2', 'P3', 'P4']} for expected in ['P1', 'P2', 'P3', 'P4']}
                engines.append({'name': name, 'accuracy': round(sum(r['correct'] for r in rows) / len(rows), 4),
                    'critical_undertriage': sum(r['actual'] is not None and r['actual'] != 'P1' for r in critical),
                    'critical_errors': sum(bool(r['error']) for r in critical), 'critical_count': len(critical),
                    'errors': len(rows) - len(success), 'median_latency_ms': round(statistics.median(times), 2),
                    'confusion_matrix': matrix, 'cases': rows})
            result = {'created_at': timezone.now().isoformat(), 'policy_version': POLICY_VERSION, 'case_count': len(cases),
                      'provider': provider_info(), 'independent_test': False,
                      'limitations': 'Dados sintéticos públicos; rótulos do autor sem validação especializada. Casos acessíveis durante desenvolvimento.',
                      'engines': engines}
            target = Path(options['output'])
            if not target.is_absolute(): target = settings.BASE_DIR / target
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            self.stdout.write(self.style.SUCCESS(f'Resultados salvos em {target}'))
        finally:
            if original is None: os.environ.pop('AI_PROVIDER', None)
            else: os.environ['AI_PROVIDER'] = original
