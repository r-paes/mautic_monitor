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

## Status Atual

| Camada      | Status     | Detalhes |
|-------------|------------|----------|
| Backend     | ✅ Completo | P1–P4 + Ajustes 1–4 + Auditoria 0A/0B |
| Frontend    | ✅ Completo | Blocos A–H + Ajustes 1–3 + Auditoria 0A/0B |
| Auditoria   | ✅ Completo | Correções bloqueantes + melhorias estruturais |
| Deploy      | 🔲 Pendente | Etapas 1–6 abaixo |

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
│         └────── HTTPS ────┘  ← EasyPanel proxy (Let's      │
│              monitor.dominio.com     Encrypt automático)    │
│                       │                                     │
│           ┌───────────┴────────────┐                        │
│           ▼                        ▼                        │
│   Instâncias Mautic          Gateways externos              │
│   (MySQL via aiomysql)       Sendpost / Avant SMS           │
│   VPS (SSH — chave RSA)      Webhook DLR Avant              │
└─────────────────────────────────────────────────────────────┘
```

---

## MVP — Escopo Definido

### Incluído no MVP
- [x] Autenticação JWT (login, refresh via HTTP-only cookie)
- [x] CRUD de instâncias Mautic (credenciais em tabelas separadas, Fernet)
- [x] Coleta de métricas via API Mautic
- [x] Coleta de métricas via banco MySQL das instâncias
- [x] Monitoramento VPS via SSH — chave RSA gerada pelo backend, wizard frontend
- [x] Integração Sendpost (emails enviados, entregues, bounces)
- [x] Integração Avant SMS (por cliente via costCenterCode + webhook DLR)
- [x] Motor de alertas com thresholds configuráveis
- [x] Relatórios automáticos 9h e 18h BRT — cross-instance (email + SMS)
- [x] Dashboard global + por instância
- [x] Frontend completo responsivo (desktop, tablet, mobile)
- [x] Credenciais de gateway editáveis via frontend (sem alterar .env)

### Fora do MVP (futuras versões)
- [ ] Autenticação multi-fator (2FA)
- [ ] API pública para integrações externas
- [ ] App mobile nativo
- [ ] Relatórios customizáveis (drag & drop)
- [ ] Múltiplos tenants / white-label
- [ ] Integração com outros gateways (além de Sendpost e Avant)

---

## Plano de Deploy — EasyPanel via GitHub

> **Pré-requisito:** VPS com EasyPanel instalado e acessível.
> O código é deployado a partir de um repositório GitHub.

---

### Etapa 1 — DNS e Repositório GitHub

**Objetivo:** Domínio apontando para a VPS + código no GitHub.

**1.1 — DNS**

Criar registro A no painel do domínio:
```
Tipo: A
Nome: monitor   (ou o subdomínio desejado)
Valor: <IP da VPS>
TTL: 300
```

Verificar propagação:
```bash
nslookup monitor.spacecrm.online
# Deve retornar o IP da VPS
```

**1.2 — GitHub**

Criar repositório privado e fazer push do código:
```bash
cd mautic-monitor
git remote add origin git@github.com:<usuario>/mautic-monitor.git
git push -u origin main
```

**Verificações:**
- [ ] Registro DNS tipo A criado e propagado (nslookup retorna IP da VPS)
- [ ] Repositório GitHub criado e código pushed na branch `main`

---

### Etapa 2 — Criar Projeto no EasyPanel

**Objetivo:** Configurar os 3 serviços (db, backend, frontend) no EasyPanel.

**2.1 — Criar Projeto**

1. Acesse o painel EasyPanel da VPS
2. Clique em **"Create Project"**
3. Nome: `mautic-monitor`

**2.2 — Serviço: Database (TimescaleDB)**

1. Dentro do projeto, clique **"+ Service" → "Database" → "Postgres"**
2. Ou se TimescaleDB não estiver disponível como preset, use **"Docker Image"**:
   - Image: `timescale/timescaledb-ha:pg16`
   - Environment:
     ```
     POSTGRES_DB=monitor_db
     POSTGRES_USER=monitor_user
     POSTGRES_PASSWORD=<SENHA_FORTE_AQUI>
     TZ=America/Sao_Paulo
     ```
   - Volume: `/home/postgres/pgdata/data` → persistente
   - **Não expor porta externamente** (apenas rede interna)
3. Anote o hostname interno do serviço (ex: `mautic-monitor_db` ou `db`)

**2.3 — Serviço: Backend (FastAPI)**

1. Clique **"+ Service" → "App"**
2. Nome: `backend`
3. Source: **GitHub** → selecione o repositório `mautic-monitor`
4. Build:
   - Build Path: `./backend`
   - Dockerfile Path: `./backend/Dockerfile`
5. Environment Variables (configurar na aba "Environment"):
   ```
   # Segurança
   SECRET_KEY=<GERAR_CHAVE_FORTE_32+_CHARS>
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   REFRESH_TOKEN_EXPIRE_DAYS=7
   ALLOWED_HOSTS=["https://monitor.spacecrm.online"]

   # Banco (usar hostname interno do serviço db)
   DATABASE_URL=postgresql+asyncpg://monitor_user:<SENHA_DB>@<HOSTNAME_DB>:5432/monitor_db
   DB_HOST=<HOSTNAME_DB>
   DB_PORT=5432
   DB_NAME=monitor_db
   DB_USER=monitor_user
   DB_PASSWORD=<SENHA_DB>

   # Produção
   APP_ENV=production
   APP_RELOAD=false
   APP_WORKERS=2
   DOCS_ENABLED=false
   LOG_LEVEL=info
   LOG_FORMAT=json

   # Sendpost (valores iniciais — podem ser alterados via UI depois)
   SENDPOST_API_BASE_URL=https://api.sendpost.io/api/v1
   SENDPOST_API_KEY=<SUA_CHAVE>
   SENDPOST_ALERT_FROM_EMAIL=<SEU_EMAIL>
   SENDPOST_ALERT_FROM_NAME=Space Monitor

   # Avant SMS
   AVANT_SMS_API_BASE_URL=https://channel.solucoesdigitais.dev/sms
   AVANT_SMS_TOKEN=<SEU_TOKEN>
   AVANT_SMS_ALERT_FROM=SpaceCRM

   # EasyPanel
   EASYPANEL_DOMAIN=monitor.spacecrm.online
   TZ=America/Sao_Paulo

   # Relatórios
   REPORT_STORAGE_PATH=/app/reports
   REPORT_RETENTION_DAYS=30
   REPORT_CRON_MORNING=9
   REPORT_CRON_EVENING=18
   ```
6. Volumes:
   - `/app/reports` → persistente (relatórios gerados)
7. Domain: configurar domínio interno ou não expor (frontend faz proxy)
8. Health Check: `GET /health` na porta 8000

**2.4 — Serviço: Frontend (Next.js)**

1. Clique **"+ Service" → "App"**
2. Nome: `frontend`
3. Source: **GitHub** → mesmo repositório
4. Build:
   - Build Path: `./frontend`
   - Dockerfile Path: `./frontend/Dockerfile`
   - Target stage: `runner` (produção)
5. Environment Variables:
   ```
   NEXT_PUBLIC_API_URL=https://monitor.spacecrm.online
   NEXT_PUBLIC_APP_NAME=Space Monitor
   NEXT_PUBLIC_APP_ENV=production
   TZ=America/Sao_Paulo
   ```
6. Domain: **monitor.spacecrm.online** → porta 3000
7. HTTPS: ativar (Let's Encrypt automático)

**Importante:** O `NEXT_PUBLIC_API_URL` deve apontar para o mesmo domínio do frontend. O Next.js faz proxy via `rewrites` no `next.config.mjs` — requests `/api/*` são redirecionadas ao backend internamente.

**2.5 — Rede Interna**

Verificar que os 3 serviços estão na mesma rede Docker interna do EasyPanel para que:
- Frontend consiga acessar o backend pelo hostname interno
- Backend consiga acessar o banco pelo hostname interno

**Verificações:**
- [ ] Projeto `mautic-monitor` criado no EasyPanel
- [ ] Serviço `db` (TimescaleDB) rodando com volume persistente
- [ ] Serviço `backend` conectado ao GitHub, variáveis configuradas
- [ ] Serviço `frontend` conectado ao GitHub, domínio com HTTPS ativo
- [ ] Os 3 serviços estão na mesma rede interna
- [ ] `GET https://monitor.spacecrm.online/health` retorna `{"status": "ok"}`

---

### Etapa 3 — Banco de Dados e Migrations

**Objetivo:** Criar schema completo no banco via Alembic.

Abra o terminal/console do serviço `backend` no EasyPanel (aba "Shell" ou "Terminal"):

```bash
# Rodar todas as migrations
alembic upgrade head

# Verificar versão aplicada
alembic current
# Deve mostrar: 008 (head)
```

Criar o usuário admin inicial:
```bash
python -c "
import asyncio
from app.database import AsyncSessionLocal
from app.models.users import User
from app.routers.auth import hash_password
import uuid

async def create_admin():
    async with AsyncSessionLocal() as db:
        admin = User(
            id=uuid.uuid4(),
            name='Admin',
            email='admin@spacecrm.online',
            password_hash=hash_password('SENHA_ADMIN_FORTE'),
            role='admin',
            active=True,
        )
        db.add(admin)
        await db.commit()
        print(f'Admin criado: {admin.email}')

asyncio.run(create_admin())
"
```

**Verificações:**
- [ ] Migrations 001–008 aplicadas sem erros
- [ ] `alembic current` mostra `008 (head)`
- [ ] Usuário admin criado com sucesso
- [ ] Login funciona: `POST /api/v1/auth/login` retorna access_token

---

### Etapa 4 — Verificação Funcional

**Objetivo:** Testar cada módulo do sistema em produção.

Acesse `https://monitor.spacecrm.online` no navegador:

**4.1 — Autenticação**
- [ ] Tela de login aparece
- [ ] Login com credenciais do admin funciona
- [ ] Redirect para dashboard após login
- [ ] Refresh token via cookie (sem localStorage)
- [ ] Logout limpa sessão e redireciona para login

**4.2 — Instâncias**
- [ ] Criar instância Mautic com credenciais API + MySQL
- [ ] Campos sensíveis criptografados no banco (verificar via shell do db)
- [ ] Lista atualiza via React Query após criar
- [ ] Editar instância funciona
- [ ] Excluir com confirmação

**4.3 — VPS & SSH**
- [ ] "Nova VPS": wizard 2 passos funciona
- [ ] Chave pública RSA gerada e exibida
- [ ] Botão "Copiar" funciona
- [ ] Após adicionar chave na VPS: "Testar Conexão" retorna sucesso
- [ ] Recursos (CPU/memória/disco) exibem dados após primeira coleta

**4.4 — Gateways**
- [ ] Tab Configurações: salvar credenciais Sendpost e Avant
- [ ] Tab Sendpost: exibe dados de entrega após coleta
- [ ] Tab Avant: exibe saldo real + tabela por cliente (após webhook configurado)
- [ ] Cost Centers: cadastrar correlação código↔cliente

**4.5 — Alertas**
- [ ] Motor de alertas roda (verificar logs do backend)
- [ ] Alerta gerado quando threshold é cruzado
- [ ] Email de alerta entregue (verificar caixa de entrada)
- [ ] SMS de alerta entregue (auth `alpha`)
- [ ] ACK move alerta para histórico

**4.6 — Relatórios**
- [ ] Criar ReportConfig com empresa + email
- [ ] "Gerar Relatório" manualmente funciona
- [ ] HTML renderizado com dados reais (cross-instance)
- [ ] Preview inline (iframe) funciona
- [ ] Download HTML funciona
- [ ] Jobs cron 9h e 18h: verificar logs do scheduler

**4.7 — Dashboard**
- [ ] Stat cards globais com dados reais
- [ ] Cards por instância com status
- [ ] DateRangePicker filtra dados

---

### Etapa 5 — Configurações Externas

**Objetivo:** Configurar integrações que dependem de serviços externos.

**5.1 — Webhook Avant SMS**

No painel da Avant SMS, configurar URL de callback DLR:
```
URL: https://monitor.spacecrm.online/webhooks/avant
Método: POST
Content-Type: application/json
```

Testar:
```bash
curl -X POST https://monitor.spacecrm.online/webhooks/avant \
  -H "Content-Type: application/json" \
  -d '{"id":"test_001","costCenterCode":"CLI001","recipient":"5511999999999","status":"DELIVRD","dateTime":"2026-04-06T10:00:00Z"}'
# Deve retornar: {"processed": 1}
```

**5.2 — Cost Centers Avant**

Via interface (tab Configurações → Cost Centers):
- Cadastrar cada `costCenterCode` com o nome do cliente correspondente

**5.3 — Credenciais via Interface**

Após primeiro login, configurar via tab Gateways → Configurações:
- Sendpost API Key e email remetente
- Avant SMS Token

Isso garante que as credenciais ficam no banco (prioridade) e não apenas no `.env`.

**Verificações:**
- [ ] Webhook Avant configurado e respondendo
- [ ] Cost Centers cadastrados
- [ ] Credenciais de gateway configuradas via UI

---

### Etapa 6 — Checklist Final de Produção

Somente após Etapas 1–5 aprovadas:

**Segurança:**
- [ ] `SECRET_KEY` é string forte com 32+ caracteres aleatórios
- [ ] `DB_PASSWORD` é forte e única
- [ ] `ALLOWED_HOSTS` contém apenas o domínio de produção
- [ ] `APP_ENV=production` (desabilita docs, reload, etc.)
- [ ] `DOCS_ENABLED=false` (Swagger não exposto em prod)
- [ ] HTTPS ativo com certificado válido (Let's Encrypt)
- [ ] Porta do banco NÃO exposta externamente

**Persistência:**
- [ ] Volume do banco mapeado e persistente (sobrevive a restart/rebuild)
- [ ] Volume de relatórios (`/app/reports`) mapeado e persistente
- [ ] Backup do banco configurado (pg_dump cron ou snapshot da VPS)

**Operacional:**
- [ ] Logs do backend acessíveis via EasyPanel
- [ ] APScheduler registra jobs sem erro nos logs
- [ ] Health check do backend retorna ok
- [ ] Frontend carrega sem erros no console do navegador
- [ ] Teste de login na URL de produção funciona

---

## Troubleshooting

### Backend não sobe
```bash
# No terminal do container backend:
python -c "from app.main import app; print('OK')"
# Se der erro de import, verifique os logs
```

### Frontend dá erro de API
- Verificar se `NEXT_PUBLIC_API_URL` está correto
- Verificar se o rewrite do Next.js funciona: `curl https://dominio/api/v1/auth/me`
- Verificar CORS: `ALLOWED_HOSTS` deve incluir o domínio com `https://`

### Migrations falham
```bash
# Ver estado atual
alembic current

# Ver histórico
alembic history

# Se precisar voltar
alembic downgrade -1
```

### Cookie de refresh não funciona
- Verificar se frontend e backend estão no mesmo domínio
- Verificar se `withCredentials: true` está no Axios (client.ts)
- Verificar se `secure=True` no cookie (requer HTTPS)

---

## Roadmap Pós-MVP

| Prioridade | Feature | Complexidade |
|------------|---------|--------------|
| Alta | Autenticação multi-fator (2FA) | Média |
| Alta | Gestão de usuários via frontend (API completa) | Média |
| Alta | Regras de alerta customizáveis via UI | Alta |
| Média | Webhooks de saída (Slack, Teams, etc.) | Média |
| Média | Relatórios com período personalizado via UI | Baixa |
| Média | Histórico de métricas com gráficos por período | Média |
| Baixa | App mobile (React Native) | Alta |
| Baixa | Multi-tenant / white-label | Alta |
| Baixa | Integração com outros gateways de email/SMS | Média |
