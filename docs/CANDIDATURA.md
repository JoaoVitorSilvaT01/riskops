# Material para a candidatura — João Vitor Silva

## Apresentação curta

Sou graduando em Engenharia de Computação na UNIFEI, com conclusão prevista para 2028. Tenho experiência na Vale com Power Apps, Power Automate e Power BI, levantamento de requisitos com áreas operacionais e construção de ferramentas internas. No laboratório Praxis, desenvolvo uma aplicação de gestão de acervo com React Native, Python e MongoDB, com atividades de pesquisa aplicada em ML/NLP.

Para demonstrar como aplico IA a um processo de ponta a ponta, desenvolvi, com apoio de IA no desenvolvimento, o RiskOps: um protótipo de triagem assistida de ocorrências operacionais. Integrei Gemini, recuperação de procedimentos demonstrativos, validação de evidências, revisão humana, auditoria e entrega assinada de alertas. Documentei os testes, resultados e limitações, incluindo falhas reais do provedor.

## Descrição do projeto para currículo ou formulário

**RiskOps — Triagem assistida de ocorrências operacionais | Python, Django REST Framework, Gemini, SQLite, JavaScript**

- Construção de aplicação com registro de relatos, análise estruturada por IA, revisão humana, responsáveis e acompanhamento do atendimento.
- Implementação de validação de evidências literais, recuperação lexical de procedimentos demonstrativos, controle de versão e histórico com cadeia de hashes.
- Integração de alertas por webhook com assinatura HMAC, persistência transacional e novas tentativas; preservação do relato quando a IA está indisponível.
- Avaliação exploratória com 36 cenários sintéticos e documentação de divergências, latência e falhas. Gemini validado em chamadas reais e fluxo completo testado no navegador.

Os links devem apontar para o repositório e para o vídeo efetivamente publicados. Não inserir endereços localhost no formulário como se fossem uma demonstração pública.

## Resultados que posso defender

- A integração Gemini foi executada de verdade; o sistema não treina um modelo próprio.
- Na execução documentada, 31 de 36 cenários concordaram com a referência; três receberam prioridade mais alta e dois falharam (tempo limite e HTTP 429).
- A mediana registrada foi aproximadamente 1,88 segundo. Não é uma garantia de desempenho.
- Os cenários são sintéticos, preparados pelo autor e não constituem avaliação independente ou validação profissional.
- O projeto foi inspirado na experiência com processos operacionais; não foi implantado na Vale, não usa seus documentos e não comprova redução de acidentes ou economia de horas.

## Explicação de 45 segundos

“Minha experiência combina automação corporativa e desenvolvimento de aplicações. No RiskOps, parti de um processo: organizar relatos de campo, identificar lacunas e encaminhar a avaliação. Usei Gemini para estruturar o texto, com um contrato de resposta e verificação de evidências. O relato é salvo antes da chamada à IA, e uma falha não impede revisão manual. O responsável confirma a prioridade, com histórico e controle de versão. Para os alertas, implementei uma caixa de saída e entrega assinada. Avaliei o sistema em cenários sintéticos e mantive as falhas visíveis. Meu próximo passo seria testar com usuários e especialistas antes de qualquer piloto real.”

## Antes de enviar

1. Conferir dados pessoais, previsão de formatura e modalidade diretamente no formulário.
2. Inserir o link confirmado do repositório e o vídeo disponível para o avaliador.
3. Citar resultados anteriores da Vale/Praxis apenas se puder explicar sua contribuição e comprovar o resultado; não inventar números.
4. Submeter a inscrição na sua própria conta. Este material prepara as respostas; não representa uma candidatura enviada.
