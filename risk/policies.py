"""Demonstration policy, NOT an official company or regulatory risk matrix."""
import re
import unicodedata

POLICY_VERSION = 'demo-2026.11-v1'
POLICIES = [
    {'id': 'DEM-01', 'category': 'eletrico', 'title': 'Energia elétrica',
     'terms': ['eletric', 'energizad', 'fio exposto', 'fios expostos', 'curto', 'choque', 'painel'],
     'consequence': 'Lesão grave por contato com energia.', 'severity': 'grave',
     'guidance': 'Encaminhar à equipe habilitada para avaliação; não orientar intervenção elétrica.'},
    {'id': 'DEM-02', 'category': 'mecanico', 'title': 'Máquinas e partes móveis',
     'terms': ['esteira', 'correia', 'maquina', 'prens', 'engrenagem', 'protecao removida', 'partes moveis'],
     'consequence': 'Aprisionamento ou lesão por partes móveis.', 'severity': 'grave',
     'guidance': 'Solicitar avaliação do responsável pela operação e verificar o procedimento local.'},
    {'id': 'DEM-03', 'category': 'quimico', 'title': 'Substâncias e vazamentos',
     'terms': ['quimic', 'acido', 'solvente', 'gas', 'oleo', 'vazamento', 'combustivel', 'odor'],
     'consequence': 'Exposição a substância ou perda de contenção.', 'severity': 'indeterminada',
     'guidance': 'Solicitar identificação da substância, exposição e condição de contenção à equipe responsável.'},
    {'id': 'DEM-04', 'category': 'queda', 'title': 'Quedas e circulação',
     'terms': ['altura', 'andaime', 'queda', 'escada', 'piso', 'escorreg', 'buraco', 'guarda-corpo'],
     'consequence': 'Queda no mesmo nível ou em desnível, conforme contexto.', 'severity': 'indeterminada',
     'guidance': 'Encaminhar para avaliação das condições de acesso e proteção existentes.'},
    {'id': 'DEM-05', 'category': 'incendio', 'title': 'Fumaça e combustão',
     'terms': ['fogo', 'fumaca', 'incendio', 'chama', 'explos'],
     'consequence': 'Queimaduras, inalação ou propagação de incêndio.', 'severity': 'grave',
     'guidance': 'Encaminhar imediatamente ao responsável pelo protocolo local de emergência.'},
    {'id': 'DEM-06', 'category': 'ergonomico', 'title': 'Ergonomia',
     'terms': ['postura', 'ergonom', 'repetitiv', 'cadeira', 'lombar', 'peso', 'levantamento manual'],
     'consequence': 'Sobrecarga musculoesquelética.', 'severity': 'moderada',
     'guidance': 'Solicitar avaliação da atividade pela equipe responsável.'},
    {'id': 'DEM-07', 'category': 'ambiental', 'title': 'Aspectos ambientais',
     'terms': ['rio', 'solo', 'dreno', 'residuo', 'efluente', 'ambiental'],
     'consequence': 'Possível impacto ambiental, a depender da substância e extensão.', 'severity': 'indeterminada',
     'guidance': 'Encaminhar à equipe ambiental com substância, extensão e contenção observadas.'},
]

def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))

def sentences(report):
    return [s.strip() for s in re.split(r'(?<=[.!?;])\s+|\n+', report) if s.strip()]

STEMS = {'eletric', 'energizad', 'prens', 'quimic', 'escorreg', 'explos', 'ergonom', 'repetitiv'}

def term_matches(term, text):
    suffix = r'\w*' if term in STEMS else r'(?:s|es)?\b'
    return bool(re.search(r'\b' + re.escape(term) + suffix, text))

def retrieve(report, limit=3):
    """Transparent lexical retrieval; deliberately not advertised as semantic RAG."""
    text = normalize(report)
    ranked = [(sum(term_matches(term, text) for term in p['terms']), p) for p in POLICIES]
    return [dict(p, retrieval_score=score) for score, p in sorted(ranked, key=lambda x: -x[0]) if score][:limit]

def injection_detected(report):
    return bool(re.search(r'ignore.{0,35}(instru|regra|prompt)|system\s*:|retorne.{0,20}p4|classifique.{0,20}(baixo|rotina)|<\s*/?\s*system', normalize(report)))

def offline_analysis(report):
    context = retrieve(report)
    evidence = []
    for sentence in sentences(report):
        text = normalize(sentence)
        if any(term_matches(term, text) for p in context for term in p['terms']):
            evidence.append(sentence)
    text = normalize(report)
    # Negation/history are deliberately conservative: a reviewer resolves the ambiguity.
    uncertain = bool(re.search(r'\b(nao|sem|ontem|historico|simulado|simulacao|treinamento)\b', text))
    urgent = bool(re.search(r'\b(fogo|fumaca|incendio|chamas?|explosao|inconsciente|desmaiou|choque)\b|pessoa.{0,20}pres[ao]|fio[s]? exposto[s]?.{0,35}energizad|energizad.{0,35}fio[s]? exposto[s]?', text))
    elevated = bool(re.search(r'sem protecao|protecao removida|em movimento|em operacao|trabalhador.{0,30}altura|vazamento|cheiro de gas|odor de gas', text))
    priority = 'P1' if urgent and not uncertain else 'P2' if elevated or urgent or not context else 'P3'
    if any(t in text for t in ['resolvido', 'corrigido', 'substituida', 'regularizado']) and not urgent and not elevated:
        priority = 'P4'
    missing = ['Condições de exposição de pessoas e controles existentes.']
    if uncertain:
        missing.append('Confirmar se o perigo está presente agora; há negação, histórico ou simulação no relato.')
    if not context:
        missing.append('Descrever o perigo observado, sua localização e condição atual.')
    if context and context[0]['category'] == 'quimico':
        missing.append('Identificar substância, volume aproximado e contenção observada.')
    return {
        'category': context[0]['category'] if context else 'indefinido',
        'potential_severity': context[0]['severity'] if context else 'indeterminada',
        'suggested_priority': priority,
        'summary': 'Triagem preliminar por regras locais; confirmação do responsável é necessária.',
        'hazards': [p['consequence'] for p in context] or ['Perigo não identificado com o contexto disponível.'],
        'evidence': evidence[:5],
        'missing_information': missing,
        'recommended_actions': [p['guidance'] for p in context] or ['Solicitar informações adicionais e revisão humana.'],
        'policy_ids': [p['id'] for p in context],
    }

def baseline(report):
    text = normalize(report)
    if any(t in text for t in ['fogo', 'choque', 'gas']): return 'P1'
    if any(t in text for t in ['vazamento', 'maquina', 'altura']): return 'P2'
    return 'P4'
