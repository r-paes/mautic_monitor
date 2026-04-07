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
| Backend     | ✅ Completo | P1–P4 + Ajustes 1–4 + Auditoria 0A/0B |
| Frontend    | ✅ Completo | Blocos A–H + Ajustes 1–3 + Auditoria 0A/0B |
| Auditoria   | ✅ Completo | Correções bloqueantes + melhorias estruturais |
| Deploy      | 🟡 Em andamento | Etapas 1–4 concluídas, Etapa 5 parcial |

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

**4.3 — VPS & SSH ✅ (UI)**
- [x] Wizard 2 passos funciona
- [x] Chave RSA gerada e copiável
- [ ] Teste de conexão SSH com VPS real (pendente — requer VPS configurada)

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

### Etapa 5 — Configurações Externas 🟡 EM ANDAMENTO

**5.1 — Sendpost ✅ Parcial**
- [x] Account API Key configurada (coleta de stats on-demand)
- [x] Endpoint `GET /gateways/sendpost/stats` consulta API direto por período
- [x] 3 sub-accounts listadas automaticamente
- [ ] SubAccount API Key para envio de alertas/relatórios (campo existe na UI, falta preencher)

**5.2 — Avant SMS** 🔲 Pendente
- [ ] Token Alpha configurado via Gateways → Configurações
- [ ] URL da API configurada
- [ ] Webhook DLR: `POST https://appmonitor.spacecrm.online/webhooks/avant`
- [ ] Cost Centers cadastrados

**5.3 — Instâncias Mautic** 🔲 Pendente
- [ ] Cadastrar instância real com credenciais API Mautic
- [ ] Cadastrar credenciais MySQL da instância
- [ ] Configurar SSH para VPS da instância

---

### Etapa 6 — Checklist Final de Produção 🔲 PENDENTE

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

## Próximos Passos (Próxima Sessão)

1. **Redeploy frontend** com últimas alterações de cards/percentuais
2. **Configurar Avant SMS** (Token + URL + Webhook + Cost Centers)
3. **Configurar SubAccount API Key** Sendpost para envio de alertas
4. **Cadastrar instância Mautic real** com credenciais API + MySQL
5. **Testar alertas** com dados reais
6. **Testar relatórios** com dados reais
7. **Completar Etapa 6** (backup, scheduler check)

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
