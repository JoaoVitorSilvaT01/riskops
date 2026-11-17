# Roteiro de demonstração (90–120 segundos)

Vídeo disponível: [RiskOps — 93 segundos](demo/riskops.webm), sem áudio, com explicações na tela. Ele mostra o fluxo real com Gemini e receptor local em uma base isolada de dados sintéticos.

1. **Problema (10s):** “Relatos de campo chegam em texto livre. A equipe precisa organizar informações, priorizar a revisão e acompanhar o atendimento.”
2. **Visão geral (10s):** mostrar fila e prioridades. Explicar que os dados são sintéticos e a política é demonstrativa.
3. **Registrar (20s):** usar o cenário “Emergência”. Se o Gemini estiver configurado, apontar o nome do provedor; no modo local, dizer explicitamente que são regras, não LLM.
4. **Análise (20s):** abrir evidências literais e lacunas; explicar severidade potencial versus prioridade. A prioridade sugerida ainda não representa validação profissional.
5. **Revisão (15s):** confirmar prioridade, atribuir equipe, justificar e salvar. Mostrar histórico e versão. Concluir somente após revisão.
6. **Integração (15s):** mostrar alerta pendente; executar o worker com receptor local configurado. Atualizar Integrações para ver “Entregue” e mostrar `/receipts` no receptor.
7. **Qualidade (15s):** abrir Avaliação. Mostrar baseline, resultados, falhas e casos difíceis. Dizer que os rótulos são do autor, com acesso aos cenários durante o desenvolvimento.

## Texto para candidatura

> Desenvolvi o RiskOps, um protótipo de triagem assistida de ocorrências operacionais inspirado na minha experiência com digitalização de processos. A solução integra Gemini com saída estruturada, recuperação de procedimentos demonstrativos, validação de evidências, revisão humana, trilha de auditoria e webhooks assinados com novas tentativas. Incluí uma avaliação reproduzível com cenários sintéticos, comparação com baseline e exposição das divergências. O projeto demonstra o fluxo de ponta a ponta; não foi implantado na Vale nem validado para decisões reais de segurança.

Gemini já foi validado com chamadas reais na execução documentada. Não alegue horas economizadas, acidentes evitados ou uso corporativo sem medir e comprovar.

## Perguntas de entrevista

- **Por que usar IA?** Extrair contexto de relatos variados e organizar evidências/lacunas; o baseline demonstra os limites de poucas palavras-chave.
- **Por que não deixar o modelo decidir?** Consequências dependem de contexto ausente; há revisão humana, política explícita e avaliação exploratória.
- **Por que outbox?** Evita gravar uma ocorrência e perder o pedido de alerta se o destino falhar.
- **Por que não múltiplos agentes?** O fluxo exige um contrato de extração e controle de estado; múltiplos agentes não agregariam evidência de qualidade por si só.
- **Como comprovaria impacto?** Comparação de tempo e qualidade de triagem com profissionais, registro de correções e avaliação independente antes de qualquer piloto real.
