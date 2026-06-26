# 99 — Sumário Executivo do Sistema

## O que é o sistema

O projeto é uma **plataforma web full-stack para criação, distribuição e análise de questionários psicológicos**, com suporte específico ao instrumento **CHYPS-V** (escala de sensibilidade visual com 20 itens tipo Likert em 4 subescalas).

O sistema é voltado para pesquisadores que precisam:
1. Criar questionários com perguntas, instruções e termos de consentimento
2. Distribuir via links públicos criptografados
3. Coletar respostas anônimas
4. Analisar resultados com estatísticas avançadas (Alpha de Cronbach, correlação de Spearman, tabulação cruzada)
5. Exportar dados em CSV, XLSX ou JSON

---

## Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Frontend | Python + NiceGUI (componentes Vue.js server-side) |
| Backend | Python + FastAPI + Uvicorn |
| Banco de dados | PostgreSQL 15 |
| ORM | SQLAlchemy 2.0 |
| Migrações | Alembic |
| Validação | Pydantic v2 |
| Autenticação | bcrypt + passlib (sem JWT) |
| Analytics | numpy + scipy (stats) |
| Gráficos | Plotly (renderizado via NiceGUI) |
| Drag-and-drop | Sortable.js (wrapper Python) |
| Infraestrutura | Docker Compose (4 containers) |
| Proxy | nginx |
| Exportação XLSX | openpyxl |

---

## Superfície de API REST

**Base URL:** `http://host:8000/api/v1`

| Recurso | Endpoints disponíveis |
|---|---|
| `/users` | POST (criar), GET /{id}, PUT /{id}, DELETE /{id}, GET (listar), POST /login |
| `/questions` | POST, GET /{id}, GET /by-caption/{caption}, POST /{id}/options, GET (listar), DELETE /{id}, PUT /{id} |
| `/questionnaires` | POST /instructions, PUT /instructions/{id}, POST, GET /{id}, PUT /{id}, DELETE /{id}, GET (listar), GET /{id}/respond, POST /{id}/generate-link, GET /{id}/eligibility |
| `/responses` | POST /submit, GET /submissions/{id}, GET /questionnaires/{id}/submissions, GET /questionnaires/{id}/statistics, DELETE /submissions/{id} |
| `/reports` | GET /questionnaires/{id}/full-report, GET /questionnaires/{id}/summary, GET /questionnaires/{id}/export, GET /questionnaires/{id}/analytics, GET /questionnaires/{id}/questions/{q_id}/analysis, POST /questionnaires/{id}/custom-export |
| `/analytics` | POST /chyps-scores, POST /crosstab, GET /question-distributions, POST /text-responses, GET /filter-options, GET /dashboard-data, POST /filtered-analytics, GET /crosstab-variables |

**Total de endpoints:** ~34 endpoints REST

---

## Modelo de Dados (8 tabelas)

| Tabela | Registros representados |
|---|---|
| `users` | Pesquisadores/criadores |
| `questionnaires` | Questionários criados |
| `questionnaire_items` | Itens (perguntas/instruções/termos) vinculados a questionários |
| `questions` | Perguntas reutilizáveis (single, multiple, free_text) |
| `question_options` | Opções de resposta com pesos |
| `instructions` | Textos de instrução reutilizáveis |
| `questionnaire_submissions` | Respostas anônimas de respondentes |
| `answers` | Respostas individuais por questão |

---

## Fluxos Principais

1. **Cadastro/Login** → `users` → sessão NiceGUI storage
2. **Criar Questionário** → `questions` + `instructions` + `questionnaires` + `questionnaire_items`
3. **Responder Questionário** → link `/questionnaire/BASE64/respond` → `questionnaire_submissions` + `answers`
4. **Relatório** → `full_report` → `AnalyticsService` → CHYPS-V + Cronbach + Spearman
5. **Exportar** → CSV/XLSX/JSON wide-format com filtros de data

---

## Instrumento CHYPS-V (domínio específico)

O sistema é especializado para o instrumento CHYPS-V:
- **20 itens** (Q1-Q20) com escala Likert 4 pontos (0-3)
- **Score global:** 0-60
- **4 subescalas:**
  - Brilho (Q3,Q7,Q9,Q11,Q13,Q19) — 6 itens
  - Padrão (Q1,Q5,Q12,Q14,Q15,Q20) — 6 itens
  - Estroboscópico (Q2,Q6,Q10,Q16,Q18) — 5 itens
  - Ambiente Visual Intenso (Q4,Q8,Q17) — 3 itens
- **Alpha de Cronbach** calculado automaticamente para os 20 itens
- **Correlação cruzada de Spearman** entre todos os itens (matriz 20×20)
- **Filtros demográficos** por diagnóstico, medicação psiquiátrica e ano de nascimento

---

## Pontos Técnicos de Atenção

### Gargalo de Performance
`ReportService.get_full_report` carrega **todas** as submissões, answers, questions e options de um questionário em memória em uma única operação. Com volumes grandes (>10.000 respostas), isso pode causar pressão de memória e latência elevada. Todos os endpoints de analytics e dashboard dependem desta função.

### Acoplamento Alto
`ReportService.get_full_report` é consumido por 8 endpoints diferentes direta ou indiretamente. Qualquer mudança em seu contrato de retorno impacta todos esses consumidores.

### Autenticação Simplificada
O sistema não implementa JWT ou tokens de sessão stateless. A autenticação é baseada no storage server-side do NiceGUI por conexão websocket. Isso significa que o frontend não pode ser escalado horizontalmente sem solução de sessão compartilhada.

### CORS Permissivo
`allow_origins=["*"]` no backend é adequado para desenvolvimento mas representa risco em produção com dados de pesquisa.

### Código Duplicado
`_compute_filter_options` aparece tanto no módulo `analytics.py` (endpoint) quanto como método estático equivalente — lógica praticamente idêntica em dois locais.

`_get_crosstab_variables` e `get_crosstab_variables` (endpoint separado) têm lógica duplicada.

### Sem Paginação Real no `get_full_report`
A paginação de submissões no endpoint `/submissions` é feita na memória Python (fatiamento de lista) após carregar tudo do banco, não via `LIMIT/OFFSET` SQL.

### Deleção Manual em Cascata
`delete_questionnaire` realiza deleção em 7 passos manuais sem uso de transação explícita além do `db.commit()` final. Uma falha parcial pode deixar dados órfãos.

---

## Métricas do Código

| Métrica | Valor |
|---|---|
| Total de arquivos Python relevantes | ~55 |
| Total de tabelas no banco | 8 |
| Total de endpoints REST | ~34 |
| Linhas em `report_service.py` | ~465 |
| Linhas em `questionnaire_create_page.py` | ~596 |
| Linhas em `report_detailed.py` | ~625 |
| Linhas em `question_item_editor.py` | ~445 |
| Classes de serviço backend | 6 |
| Classes de componente frontend | ~18 |
| Migrações Alembic | 14 |
| Containers Docker | 4 |

---

## Histórico de Migrações Relevante (Alembic)

| Migração | Mudança |
|---|---|
| `069642e946ab` | initial migration |
| `696d44db5a92` | initial migration (variante) |
| `3bca61d15f99` | add_criador_id_to_questionnaires |
| `0b772bfe0146` | remove_respondent_personal_data |
| `3e7568103153` | add_nascimento_to_users |
| `f63800b574cd` | alterar_idade_para_nascimento |
| `967df56bd26a` | adicionar_campo_caption_nas_perguntas |
| `b2d1f3c7a9e0` | add_term_support |
| `a1d9f8c2b7e4` | add_obrigatoria_to_questions |
| `c3f1a2d4e5b6` | rename_columns_to_english |
| `caf9fb3a8e92` | initial_migration |
| `f99ef9af4889` | initial_migration |
