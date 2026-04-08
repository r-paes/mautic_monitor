# Plano de Implantação — Mautic Monitor

## Visão Geral

**Mautic Monitor** é um painel de monitoramento centralizado para múltiplas instâncias Mautic,
coletando métricas de performance, alertas e status de envio via API, banco de dados e SSH.

---

## Stack Tecnológica

| Camada     | Tecnologia                              |
|------------|-----------------------------------------|
| Frontend   | Next.js 14 (App Router) + Tailwind CSS  |
| Backend    | FastAPI (Python 3.11+)                  |
| Banco      | TimescaleDB (PostgreSQL 16)             |
| Scheduler  | APScheduler (coleta periódica)          |
| Infra      | Docker via EasyPanel (VPS)              |
| Auth       | JWT (Bearer token + HTTP-only cookie)   |
| Deploy     | GitHub → EasyPanel (auto-build)         |

---

## Ambiente de Produção

| Item | Valor |
|------|-------|
| Domínio | `appmonitor.spacecrm.online` |
| Projeto EasyPanel | `mautic_space` |
| Serviço DB | `monitor_db` (TimescaleDB) |
| Serviço Backend | `monitor_backend` (FastAPI :8000) |
| Serviço Frontend | `monitor_frontend` (Next.js :3000) |
| DB interno | `mautic_space_monitor_db:5432` |
| DB credentials | `monitor_db` / `monitor_user` / `a7d1caa30cf457239e58` |
| Admin | `ricardo@space2.com.br` |
| Repositório | `https://github.com/r-paes/mautic_monitor.git` |
| Roteamento | Traefik path-based: `/api/*`, `/webhooks/*`, `/health` → backend; `/` → frontend |
| API URL | Relativa `/api/v1` (mesmo domínio, cookie funciona nativamente) |

---

## Status Atual

| Camada      | Status     | Detalhes |
|-------------|------------|----------|
| Backend     | ✅ Completo | P1–P4 + Reestruturação VPS + Auditoria S1-S7 |
| Frontend    | ✅ Completo | Blocos A–H + VPS/Instâncias separados + Scheduler UI |
| Auditoria   | ✅ Completo | 5 categorias auditadas, P0+P1 corrigidos |
| Deploy      | 🟡 Em andamento | Etapas 1–4 + Reestruturação VPS concluídas |
| Integração  | 🟡 Em andamento | Etapa 7 — testes com dados reais |

---

## Arquitetura de Serviços (EasyPanel)

```
┌─────────────────────────────────────────────────────────────┐
│                    EasyPanel (VPS)                           │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   frontend   │  │   backend    │  │  db (TimescaleDB) │  │
│  │   :3000      │  │   :8000      │  │  :5432 (interno)  │  │
│  │   Next.js    │  │   FastAPI    │  │  PostgreSQL 16    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────┘  │
│         │                 │                                 │
│         └────── HTTPS ────┘  ← Traefik reverse proxy        │
│              appmonitor.spacecrm.online                     │
│                       │                                     │
│           ┌───────────┴────────────┐                        │
│           ▼                        ▼                        │
│   Instâncias Mautic          Gateways externos              │
│   (MySQL via aiomysql)       Sendpost / Avant SMS           │
│   VPS (SSH — chave RSA)      Webhook DLR Avant              │
└─────────────────────────────────────────────────────────────┘
```

---

## Etapas de Deploy

### Etapa 1 — DNS e Repositório ✅ CONCLUÍDA

- [x] Domínio `appmonitor.spacecrm.online` apontado via registro A
- [x] Repositório GitHub `r-paes/mautic_monitor` criado e pushed

---

### Etapa 2 — Criar Serviços no EasyPanel ✅ CONCLUÍDA

- [x] Projeto `mautic_space` criado
- [x] Serviço `monitor_db` (TimescaleDB) rodando com volume persistente
- [x] Serviço `monitor_backend` conectado ao GitHub, variáveis configuradas
- [x] Serviço `monitor_frontend` conectado ao GitHub, domínio HTTPS ativo
- [x] Traefik path routing configurado (`/api/*` → backend, `/` → frontend)
- [x] Volume `reports-data` montado em `/app/reports`

---

### Etapa 3 — Banco de Dados e Migrations ✅ CONCLUÍDA

- [x] Migrations 001–009 aplicadas
- [x] Usuário admin criado (`ricardo@space2.com.br`)
- [x] Hypertables TimescaleDB com composite PK corrigidas
- [x] ENUMs PostgreSQL aplicados
- [x] Credenciais extraídas para tabelas dedicadas (migration 008)
- [x] Campos Sendpost detalhados + sub-account (migration 009)

**Fixes aplicados durante deploy:**
- TimescaleDB requer PK composta incluindo coluna de partição (`time`)
- ENUM default precisa de `DROP DEFAULT` antes de `ALTER TYPE`
- `bcrypt==4.0.1` pinado para compatibilidade com passlib

---

### Etapa 4 — Verificação Funcional ✅ CONCLUÍDA

**4.1 — Autenticação ✅**
- [x] Login funciona
- [x] Refresh token via HTTP-only cookie
- [x] Logout limpa sessão
- [x] Middleware protege rotas do dashboard
- [x] UUID serialization corrigida em todos os schemas

**4.2 — Instâncias ✅**
- [x] Criar instância funciona
- [x] Editar instância funciona
- [x] Excluir com confirmação funciona

**4.3 — VPS & SSH ✅**
- [x] VPS separada de instâncias (entidade independente)
- [x] CRUD VPS funciona (criar, editar, excluir)
- [x] Wizard 2 passos funciona (dados + chave SSH)
- [x] Chave RSA 4096 gerada e copiável
- [x] Cards CPU/Memória/Disco por VPS
- [x] Instância associada via dropdown
- [x] Serviços (Web/DB/Crons) configuráveis por instância
- [x] Tabela instâncias com status VPS + status containers (Web/DB/Crons)
- [ ] Teste de conexão EasyPanel com VPS real (Etapa 7.1)

**4.4 — Gateways ✅**
- [x] Tab Configurações: credenciais salvas (Account API Key + SubAccount API Key)
- [x] Tab Sendpost: dados on-demand da API Sendpost por sub-account
- [x] 8 stat cards com percentuais (Processed, Delivered, Dropped, Hard Bounce, Soft Bounce, Opened, Clicked, Spam)
- [x] Tabela por sub-account com valor + percentual
- [x] Filtro de data funciona (consulta Sendpost API para o período)
- [x] Botão Atualizar com animação spinner
- [x] 3 sub-accounts detectadas: Safex Broker, Veloc Broker, Space CRM
- [x] Dados fantasma antigos limpos do banco
- [ ] Avant SMS: credenciais não configuradas
- [ ] Cost Centers: nenhum cadastrado

**4.5 — Alertas** 🔲 Pendente (requer dados reais)
- [ ] Motor de alertas roda e gera alertas
- [ ] Email de alerta entregue
- [ ] SMS de alerta entregue
- [ ] ACK funciona

**4.6 — Relatórios** 🔲 Pendente (requer dados reais)
- [ ] ReportConfig criado
- [ ] Geração manual funciona
- [ ] Preview/download funciona
- [ ] Cron 9h/18h roda

**4.7 — Dashboard** 🔲 Pendente (requer instâncias Mautic configuradas)
- [ ] Stat cards globais com dados reais
- [ ] Cards por instância

---

### Etapa 5 — Configurações Externas ✅ CONCLUÍDA (UI pronta)

**5.1 — Sendpost ✅ Parcial**
- [x] Account API Key configurada (coleta de stats on-demand)
- [x] Endpoint `GET /gateways/sendpost/stats` consulta API direto por período
- [x] 3 sub-accounts listadas automaticamente
- [ ] SubAccount API Key para envio de alertas/relatórios (Etapa 7.3)

**5.2 — Avant SMS** → Etapa 7.3
**5.3 — Instâncias Mautic** → Etapa 7.2
**5.4 — VPS** → Etapa 7.1

---

### Etapa 6 — Reestruturação VPS vs Instâncias ✅ CONCLUÍDA (2026-04-07)

---

### Etapa 9 — Checklist Final de Produção 🔲 PENDENTE

**Segurança:**
- [x] `SECRET_KEY` forte configurada
- [x] `DB_PASSWORD` forte e única
- [x] `ALLOWED_HOSTS` com domínio de produção
- [x] `APP_ENV=production`
- [x] HTTPS ativo (Let's Encrypt)
- [x] Porta do banco não exposta
- [ ] `DOCS_ENABLED=false` (verificar)

**Persistência:**
- [x] Volume do banco persistente
- [x] Volume de relatórios (`reports-data`) persistente
- [ ] Backup do banco configurado (pg_dump cron)

**Operacional:**
- [x] Logs acessíveis via EasyPanel
- [x] Health check funcionando
- [x] Frontend sem erros de console
- [ ] APScheduler jobs sem erros nos logs (verificar com dados reais)

---

## Alterações Técnicas Realizadas Durante Deploy

### Sendpost — Multi-SubAccount via X-Account-ApiKey
- Collector reescrito para usar `X-Account-ApiKey` (conta) em vez de `X-SubAccount-ApiKey` (sub-account)
- Lista sub-accounts automaticamente via `GET /account/subaccount/`
- Stats on-demand: `GET /gateways/sendpost/stats?start=...&end=...` consulta API Sendpost direto
- Sanitização: apenas `id` e `name` extraídos da resposta (apiKey, smtpAuths descartados)
- Modelo `GatewayMetric` com `subaccount_id`, `subaccount_name` + campos detalhados
- Frontend: 8 stat cards com percentuais, tabela por sub-account com valor+%

### Autenticação
- Refresh token em HTTP-only cookie (não localStorage)
- UUID serialization corrigida em 8 schemas Pydantic (5 routers)
- `bcrypt==4.0.1` pinado para compatibilidade

### Frontend
- API URL sempre relativa `/api/v1` (Traefik roteia)
- Datas enviadas em UTC (`toISOString()`) em todas as páginas
- Docker build com cache (BuildKit + .dockerignore)

---

## Detalhes Técnicos — Reestruturação VPS vs Instâncias (Etapa 6)

### Concluído
- **Fase 1:** Novos modelos `VpsServer`, `InstanceService`, `SchedulerConfig` + migration 010
- **Fase 2:** Novos routers `vps_servers`, `scheduler_config` + ajustes em instances, vps, scheduler
- **Fase 3:** Frontend — API layer, hooks, componentes VPS reescritos para usar `VpsServer`
- **Fase 4:** Frontend — `ServiceManager` (CRUD containers), `SchedulerSettings` (intervalos editáveis)
- **Fase 5:** Frontend — Tab "Intervalos" em Settings
- **Fase 6 — Auditoria:**
  - S1: `vps_id` adicionado ao modelo Alert + migration 011 + engine/scheduler corrigidos
  - S2: `SchedulerSettings` movido para `components/dashboard/settings/`
  - S3: `__init__.py` adicionado em `backend/app/services/`
  - S4: `UserOut` duplicado renomeado para `UserAuthOut` em `auth.py`
  - S5: Whitelist de intervalos SQL no collector PostgreSQL
  - S7 (parcial): `AVANT_SEND_URL` movida de collector para `config.py` (desacoplamento alert↔collector)

### Pendente — Prioridade 2 (Melhorias Estruturais Futuras)

**S6. Criar camada de serviço para gateways**
- Criar `backend/app/services/gateway_service.py`
- Mover instanciação de `SendpostCollector` e `AvantSMSCollector` de `routers/gateways.py` e `routers/avant.py` para o service
- Routers chamam service, não collectors diretamente
- Benefício: testabilidade, reuso entre scheduler e API, menor acoplamento

**S7. Completar desacoplamento de módulos**
- Avaliar extração de job implementations do `scheduler.py` para módulos separados (ex: `jobs/collect_vps.py`)
- Separar criação de alertas da notificação no `alerts/engine.py` (criar `alerts/dispatcher.py`)
- Benefício: scheduler como orquestrador puro, cada job isolado e testável

---

## Etapa 7 — Integração com Dados Reais 🟡 EM ANDAMENTO

Testes etapa a etapa conectando infraestrutura real:
- 3 instâncias Mautic
- 2 VPS
- Gateways: Sendpost (email) + Avant SMS

### 7.1 — Cadastrar VPS Reais ✅

Para cada VPS (2 servidores via EasyPanel API):

| Passo | Ação | Verificação |
|-------|------|-------------|
| 1 | VPS & Logs → Nova VPS (nome, URL EasyPanel, API Key) | VPS aparece na lista |
| 2 | Editar VPS → Testar conexão | "Conexão estabelecida com sucesso" + info CPUs/RAM/Disco |
| 3 | Verificar coleta automática (aguardar 15 min ou próximo ciclo) | Cards CPU/Memória/Disco com dados |

### 7.2 — Cadastrar Instâncias Mautic 🟡 PARCIAL

Para cada instância (3 instâncias):

| Passo | Ação | Verificação |
|-------|------|-------------|
| 1 | Instâncias → Nova Instância (nome, URL Mautic, API user/password) | Instância aparece na tabela |
| 2 | Associar VPS no dropdown | Coluna VPS mostra nome da VPS |
| 3 | Editar → Adicionar serviços (Web, DB, Crons selecionando containers do EasyPanel) | Serviços listados no modal |
| 4 | Configurar credenciais MySQL (host, porta, banco, user, password) | — |
| 5 | Verificar coleta API Mautic (aguardar 5 min) | Dashboard com dados da instância |
| 6 | Verificar coleta DB Mautic (aguardar 15 min) | Emails queued, sent no dashboard |
| 7 | Verificar status containers Web/DB/Crons na tabela | Badges OK/Parado/Erro |
| 8 | Verificar Status VPS na tabela | Badge Online/Atenção/Crítico |

### 7.3 — Configurar Gateways 🟡 PARCIAL

**Sendpost (email):** ✅

| Passo | Ação | Verificação |
|-------|------|-------------|
| 1 | Account API Key | ✅ Configurado |
| 2 | SubAccount API Key | ✅ Configurado |
| 3 | Tab Email (Sendpost) → stats on-demand | ✅ Funcionando |

**Avant SMS:** ⏸️ AGUARDANDO REESTRUTURAÇÃO (ver Etapa 9)

### 7.4 — Testar Alertas 🔲

| Passo | Ação | Verificação |
|-------|------|-------------|
| 1 | Aguardar motor de alertas rodar (1 min) | Sem erros nos logs do scheduler |
| 2 | Verificar se alertas aparecem na página Alertas | Lista de alertas ativos |
| 3 | Testar ACK de alerta | Alerta movido para Histórico |
| 4 | Verificar email de alerta (se SubAccount Key configurada) | Email recebido |
| 5 | Verificar SMS de alerta (se Avant configurado, apenas CRITICAL) | SMS recebido |

### 7.5 — Testar Relatórios 🔲

| Passo | Ação | Verificação |
|-------|------|-------------|
| 1 | Relatórios → Agendamento → Nova config | Config criada |
| 2 | Gerar relatório manual | Status "success", arquivo gerado |
| 3 | Preview/download do relatório | PDF/HTML visível |
| 4 | Verificar cron 9h/18h | Relatório gerado automaticamente |
| 5 | Verificar envio por email/SMS | Entregue |

### 7.6 — Testar Dashboard 🔲

| Passo | Ação | Verificação |
|-------|------|-------------|
| 1 | Dashboard → Global | 4 stat cards com dados reais |
| 2 | Dashboard → por instância | Cards por instância com dados |
| 3 | Filtro de período funciona | Dados mudam conforme período |
| 4 | Auto-refresh (60s) | Dados atualizam sem recarregar |

### 7.7 — Configurações do Scheduler 🔲

| Passo | Ação | Verificação |
|-------|------|-------------|
| 1 | Configurações → Intervalos | 5 intervalos editáveis |
| 2 | Alterar intervalo (ex: VPS de 15 para 10 min) | Valor salvo |
| 3 | Reiniciar backend | Novo intervalo aplicado |
| 4 | Verificar nos logs do scheduler | Job roda no novo intervalo |

---

## Etapa 8 — Reestruturação Avant SMS 🔲 PENDENTE

Redesign completo da integração Avant SMS: de token único para múltiplas contas com monitoramento de saldo.

### Fase A — Backend: Model + Migration

| Item | Descrição |
|------|-----------|
| Criar `AvantAccount` | `id`, `name` (conta), `company_name` (razão social), `token_enc` (Fernet), `active`, `is_alert_account` (bool), `created_at` |
| Criar `AvantBalanceHistory` | `id`, `account_id`, `balance`, `captured_at` — snapshot periódico de saldo |
| Remover `AvantSmsLog` | Não mais necessário (rastreava DLR do monitor, não do Mautic) |
| Remover `AvantCostCenter` | Substituído por `AvantAccount` |
| Migration 013 | Cria novas tabelas, dropa antigas |
| URL da API Avant | Config global (mesma para todas as contas) |

### Fase B — Backend: Collector + Router

| Item | Descrição |
|------|-----------|
| Simplificar `avant_sms.py` | `get_balance(token)` + `send_sms(token, ...)` |
| Novo router `avant_accounts.py` | CRUD de contas + `GET /balances` (saldo on-demand de todas) |
| Atualizar `sms_alert.py` | Busca conta com `is_alert_account=True` |
| Scheduler | Job periódico grava snapshot de saldo em `AvantBalanceHistory` |
| Remover router `avant.py` | Cost centers e stats antigos |

### Fase C — Frontend

| Item | Descrição |
|------|-----------|
| Tab SMS (Avant) | Tabela de contas com saldos on-demand (Razão Social, Nome, Saldo, Status) + consumo diário |
| Configurações → Avant | CRUD de contas (nome, razão social, token) + marcar conta de alertas |
| Remover | `CostCenterManager`, referências ao `AvantSmsLog` |

### Fase D — Configurações de Alerta SMS

| Item | Descrição |
|------|-----------|
| Configurações → Alertas | Dropdown para selecionar conta Avant para envio de alertas |
| Número(s) destinatário(s) | Campo para configurar destinatários de SMS de alerta |

### O que permanece igual

- Coleta de SMS do Mautic via MySQL → Dashboard (`HealthMetric.sms_sent_mautic`)
- URL base da API Avant (global)

---

## Etapa 9 — Checklist Final de Produção 🔲 PENDENTE

---

## Troubleshooting

### Backend não sobe
```bash
python -c "from app.main import app; print('OK')"
```

### Frontend dá erro de API
- API URL é relativa (`/api/v1`), Traefik roteia
- Verificar CORS: `ALLOWED_HOSTS=["https://appmonitor.spacecrm.online"]`
- Cookie: `withCredentials: true` no Axios + `secure=True` no cookie

### Migrations falham
```bash
alembic current    # ver estado
alembic history    # ver histórico
alembic downgrade -1  # voltar uma
```

### TimescaleDB PK
Hypertables requerem PK composta incluindo a coluna de partição:
```sql
PRIMARY KEY (id, time)
```

### ENUM default casting
```sql
ALTER TABLE t ALTER COLUMN c DROP DEFAULT;
ALTER TABLE t ALTER COLUMN c TYPE new_enum USING c::text::new_enum;
ALTER TABLE t ALTER COLUMN c SET DEFAULT 'value'::new_enum;
```
