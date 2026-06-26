# Outros instrumentos

## CHYPS_Price2025

[**CHYPS_Price2025**](./Chyps_Price2025.pdf) corresponde ao questionário *Cardiff Hypersensitivity Scale – Visual* (CHYPS-V), desenvolvido originalmente em inglês.

O CHYPS-V é uma escala criada para medir subtipos de hipersensibilidade visual, conforme descrito nos trabalhos de Price et al. (2025). O questionário avalia diferentes dimensões de sensibilidade visual e pode ser utilizado em pesquisas envolvendo neurodivergência, neurologia e saúde mental.

Este arquivo contém exclusivamente a versão **em inglês** da escala CHYPS-V.

## NeuroVision — sistema de aplicação do questionário

O **NeuroVision** é o sistema web criado especificamente para esta pesquisa para aplicar o questionário CHYPS-BR (a versão em Português Brasileiro da escala CHYPS-V) aos participantes de forma digital.

- **Sistema:** [https://neurovision.me](https://neurovision.me)
- **Questionário aplicado na pesquisa:** [https://neurovision.me/questionnaire/Mw/respond](https://neurovision.me/questionnaire/Mw/respond)

O questionário servido pelo NeuroVision usa a tradução selecionada pelo estudo de tradução (versão **DeepSeek v3.2 DeepThink**, escolhida em [`Codigos/cardiff-translation/`](../Codigos/cardiff-translation/)), com os 20 itens da escala e resposta em 4 pontos: Quase Nunca (0) · Ocasionalmente (1) · Frequentemente (2) · Quase Sempre (3).

As respostas coletadas pelos participantes são exportadas em CSV e processadas pelo pipeline em [`Codigos/erg-analysis/`](../Codigos/erg-analysis/) (módulo `scripts/questionnaire/`), onde são vinculadas aos dados de ERG, featurizadas (cálculo do `chyps_score` por subscala) e anonimizadas. O detalhamento técnico desse fluxo está no [README dos Códigos](../Codigos/README.md#sistema-de-coleta--neurovision).
