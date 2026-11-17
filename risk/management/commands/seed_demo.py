import os
from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand, CommandError
from risk.models import Incident
from risk.services import create_incident, review_incident

SAMPLES = [
    ('Fumaça no painel da linha 3', 'Há fumaça saindo do painel elétrico da linha 3 agora. A equipe observou a ocorrência durante a operação.', 'Usina · Linha 3'),
    ('Proteção removida da esteira', 'A esteira está em movimento com a proteção removida. Há circulação de trabalhadores próximo às partes móveis.', 'Beneficiamento · Esteira 02'),
    ('Vazamento próximo à drenagem', 'Foi observado vazamento de óleo no piso próximo ao dreno da oficina. O volume e a contenção ainda precisam ser verificados.', 'Oficina · Ala B'),
    ('Ajuste de posto de trabalho', 'O operador relata postura desconfortável na cadeira durante atividades repetitivas no posto de trabalho.', 'Administrativo · Sala 04'),
    ('Guarda-corpo com fixação solta', 'O guarda-corpo do acesso à plataforma apresenta uma fixação solta. Não há informação sobre uso atual da passagem.', 'Pátio · Plataforma 07'),
    ('Inspeção de painel concluída', 'A equipe verificou o painel elétrico ontem. Não há fumaça nem sinais de aquecimento no momento.', 'Subestação · Bloco A'),
    ('Cadeira substituída após avaliação', 'A cadeira do posto foi substituída e o ajuste foi corrigido. O registro foi regularizado pela equipe responsável.', 'Administrativo · Sala 02'),
    ('Relato com informação incompleta', 'Foi observado algo diferente na área durante a ronda. Precisamos confirmar o que ocorreu e quais condições estão presentes.', 'Pátio · Área externa'),
]

class Command(BaseCommand):
    help = 'Cria usuário local e ocorrências sintéticas. Nunca chama um provedor externo.'
    def handle(self, *args, **options):
        if not settings.DEBUG: raise CommandError('O seed de demonstração só é permitido com DEBUG=true.')
        user, created = User.objects.get_or_create(username='demo')
        if created: user.set_password(os.getenv('DEMO_PASSWORD', 'demo-local-2026')); user.save()
        group, _ = Group.objects.get_or_create(name='Responsáveis')
        group.permissions.add(Permission.objects.get(codename='change_incident', content_type__app_label='risk'))
        user.groups.add(group)
        original = os.environ.get('AI_PROVIDER')
        os.environ['AI_PROVIDER'] = 'rules'
        try:
            for title, report, location in SAMPLES:
                if Incident.objects.filter(title=title, is_synthetic=True).exists(): continue
                incident = create_incident({'title': title, 'report': report, 'location': location,
                    'reporter': 'Equipe de demonstração', 'is_synthetic': True}, user)
                if 'posto de trabalho' in title:
                    review_incident(incident.id, {'expected_version': incident.version, 'priority': 'P3',
                        'assigned_to': 'Equipe de ergonomia', 'reason': 'Revisão demonstrativa: encaminhar para avaliação do posto.'}, user)
        finally:
            if original is None: os.environ.pop('AI_PROVIDER', None)
            else: os.environ['AI_PROVIDER'] = original
        self.stdout.write(self.style.SUCCESS('Demonstração preparada. Usuário: demo. Senha: DEMO_PASSWORD do .env (padrão documentado no README).'))
