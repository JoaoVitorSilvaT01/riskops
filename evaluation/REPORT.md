# Execução local de referência

Executada em 17/11/2026 com `python manage.py evaluate`. Arquivo detalhado: `results.json`, gerado localmente e não versionado. Pode ser reproduzido a partir de `cases.json`.

| Abordagem | Cenários | Concordância de prioridade | P1 subestimados | Falhas de execução |
|---|---:|---:|---:|---:|
| Baseline de palavras-chave | 36 | 36,11% | 6 | 0 |
| Regras locais com recuperação lexical | 36 | 88,89% | 2 | 0 |

Há dez casos P1 de referência no conjunto. As quatro divergências do motor local são E25 (fixação solta no guarda-corpo), E32 (correção de uma condição), E33 (histórico e emergência atual em frases diferentes) e E34 (faíscas e estalos). Os casos estão disponíveis para inspeção no painel.

Os números acima avaliam regras locais, não Gemini.

## Execução real com Gemini

Executada em 17/11/2026 com `python manage.py evaluate --provider gemini --output evaluation/results-gemini.json`, usando `gemini-3.1-flash-lite`. Essa execução está disponível no painel da aplicação; o resultado anterior das regras foi preservado em `evaluation/results-rules.json`.

| Medida | Resultado |
|---|---:|
| Cenários tentados | 36 |
| Análises válidas | 34 |
| Prioridades concordantes com a referência | 31 de 36 (86,11%) |
| Prioridades divergentes em análises válidas | 3 |
| Falhas de execução | 2 |
| Latência mediana de todas as tentativas | 1.877,71 ms |

Falhas: E03 não obteve resposta válida no tempo limite; E22 recebeu HTTP 429 do provedor. Divergências: E09 resultou em P1 (referência P2); E32 em P3 (referência P4); E35 em P1 (referência P2). Todas as três foram prioridades mais altas que a referência.

Dos dez cenários P1, nove tiveram resposta válida com P1 e um falhou na execução. Portanto, “zero P1 subestimados entre as respostas válidas” **não** significa que todos os casos urgentes foram analisados com sucesso. O painel mostra separadamente casos P1 sem análise válida. Não foram feitas novas tentativas para substituir as falhas dessa execução.

O resultado mede o sistema híbrido: Gemini, validação de evidências e piso de prioridade das regras locais. Não isola a qualidade do modelo.

Também foram verificados com chamadas reais o fluxo de cadastro pela API, revisão humana, conflito de versão (409), conclusão, cadeia de auditoria e geração do alerta; o receptor local confirmou a entrega assinada. O teste no navegador passou em desktop e celular com o provedor real.

## Limitações

Esses resultados não medem segurança em operação nem comprovam generalização. Os casos são sintéticos, públicos e estavam disponíveis durante o desenvolvimento. Os rótulos foram definidos pelo autor e não validados por especialista. O baseline é deliberadamente elementar e não representa um classificador corporativo bem ajustado. Respostas e latências podem variar entre execuções.

Para uma próxima etapa, construir um conjunto independente com avaliadores qualificados, definir o custo de cada tipo de erro e comparar com um baseline mais forte antes de qualquer piloto.
