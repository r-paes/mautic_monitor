# Plano de Implantação — Mautic Monitor

## Visão Geral do Projeto

**Mautic Monitor** é um painel de monitoramento centralizado para múltiplas instâncias Mautic, coletando métricas de performance, alertas e status de envio via API, banco de dados e SSH.

---

## Stack Tecnológica

| Camada     | Tecnologia                              |
|------------|-----------------------------------------|
| Frontend   | Next.js 14 (App Router) + Tailwind CSS  |
| Backend    | FastAPI (Python 3.11+)                  |
| Banco      | TimescaleDB (PostgreSQL 16)             |
| Scheduler  | APScheduler (coleta periódica)          |
| Infra      | Docker + Docker Compose                 |
| Auth       | JWT (Bearer token)                      |

---

## Arquitetura de Serviços

```
┌─────────────────────────────────────────────┐
│                  Docker Compose             │
│                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ frontend │  │ backend  │  │    db    │  │
│  │ :3000    │→ │ :8000    │→ │ :5433    │  │
│  │ Next.js  │  │ FastAPI  │  │Timescale │  │
│  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────┘
```

---

## Estrutura de Diretórios

```
mautic-monitor/
├── backend/
│   ├── app/
│   │   ├── alerts/          # Motor de alertas (email, SMS)
│   │   ├── collectors/      # Coletores de métricas
│   │   │   ├── avant_sms.py
│   │   │   ├── mautic_api.py
│   │   │   ├── mautic_db.py
│   │   │   ├── sendpost.py
│   │   │   └── vps_ssh.py
│   │   ├── models/          # Modelos SQLAlchemy
│   │   │   ├── alerts.py
│   │   │   ├── instance.py
│   │   │   ├── metrics.py
│   │   │   ├── users.py
│   │   │   └── vps_metrics.py
│   │   ├── routers/         # Endpoints FastAPI
│   │   │   ├── alerts.py
│   │   │   ├── auth.py
│   │   │   ├── instances.py
│   │   │   ├── metrics.py
│   │   │   ├── users.py
│   │   │   └── vps.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── main.py
│   │   └── scheduler.py
│   ├── alembic/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── (auth)/
│   │   └── (dashboard)/
│   ├── components/
│   ├── lib/
│   ├── public/
│   └── styles/
├── docker-compose.yml
├── docker-compose.prod.yml
└── .env.example
```

---

## Coletores de Dados

### `mautic_api.py`
Coleta via API REST do Mautic:
- Contatos ativos / novos
- Campanhas em execução
- Emails enviados / abertos / clicados
- Bounces e unsubscribes

### `mautic_db.py`
Acesso direto ao banco de dados Mautic:
- Métricas de fila de email
- Stats de segmentos
- Dados históricos

### `vps_ssh.py`
Coleta via SSH no servidor VPS:
- CPU, memória, disco
- Load average
- Status de processos (cron, workers)

### `sendpost.py`
Integração com SendPost:
- Reputação de IP/domínio
- Taxa de entrega
- Logs de bounce

### `avant_sms.py`
Integração com Avant SMS:
- Status de envio de SMS
- Créditos disponíveis
- Taxa de entrega

---

## Modelos de Dados

### `Instance`
Registro de cada instância Mautic monitorada.

| Campo         | Tipo     | Descrição                    |
|---------------|----------|------------------------------|
| id            | UUID     | Identificador único          |
| name          | string   | Nome da instância            |
| url           | string   | URL base do Mautic           |
| api_user      | string   | Usuário da API               |
| api_password  | string   | Senha da API (criptografada) |
| db_host       | string   | Host do banco Mautic         |
| ssh_host      | string   | IP do VPS                    |
| active        | boolean  | Instância ativa              |
| created_at    | datetime | Data de criação              |

### `Metrics`
Série temporal de métricas por instância (TimescaleDB hypertable).

### `VpsMetrics`
Métricas de infraestrutura do servidor.

### `Alerts`
Configuração e histórico de alertas disparados.

---

## Endpoints da API

### Autenticação
| Método | Rota            | Descrição          |
|--------|-----------------|--------------------|
| POST   | `/auth/login`   | Login, retorna JWT |
| POST   | `/auth/refresh` | Renovar token      |

### Instâncias
| Método | Rota                    | Descrição              |
|--------|-------------------------|------------------------|
| GET    | `/instances`            | Listar instâncias      |
| POST   | `/instances`            | Criar instância        |
| GET    | `/instances/{id}`       | Detalhe da instância   |
| PUT    | `/instances/{id}`       | Atualizar instância    |
| DELETE | `/instances/{id}`       | Remover instância      |

### Métricas
| Método | Rota                          | Descrição                  |
|--------|-------------------------------|----------------------------|
| GET    | `/metrics/{instance_id}`      | Métricas da instância      |
| GET    | `/metrics/{instance_id}/vps`  | Métricas do VPS            |

### Alertas
| Método | Rota              | Descrição             |
|--------|-------------------|-----------------------|
| GET    | `/alerts`         | Listar alertas        |
| POST   | `/alerts`         | Criar regra de alerta |
| DELETE | `/alerts/{id}`    | Remover alerta        |

---

## Scheduler (Coleta Periódica)

| Job                   | Intervalo | Descrição                          |
|-----------------------|-----------|------------------------------------|
| `collect_mautic_api`  | 5 min     | Coleta métricas via API Mautic     |
| `collect_mautic_db`   | 10 min    | Coleta métricas via banco Mautic   |
| `collect_vps_metrics` | 2 min     | Coleta CPU/memória/disco via SSH   |
| `collect_sendpost`    | 15 min    | Coleta reputação e entrega         |
| `run_alert_engine`    | 1 min     | Avalia regras e dispara alertas    |

---

## Sistema de Alertas

### Canais Suportados
- **Email** — via SMTP configurável
- **SMS** — via Avant SMS

### Tipos de Regra
- Threshold (ex: CPU > 80%)
- Anomalia (desvio de baseline)
- Status down (instância inacessível)

---

## Variáveis de Ambiente

```env
# Banco de dados
DB_NAME=monitor
DB_USER=monitor_user
DB_PASSWORD=

# App
APP_ENV=development
TZ=America/Sao_Paulo
NEXT_PUBLIC_APP_NAME=Mautic Monitor
NEXT_PUBLIC_APP_ENV=development

# JWT
JWT_SECRET=
JWT_EXPIRE_MINUTES=60

# Email (alertas)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
ALERT_FROM_EMAIL=

# Avant SMS
AVANT_SMS_API_KEY=
AVANT_SMS_SENDER=
```

---

## Deploy Local (Desenvolvimento)

```bash
# 1. Clonar o repositório
git clone https://github.com/r-paes/mautic_monitor.git
cd mautic_monitor

# 2. Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com os valores corretos

# 3. Subir os serviços
docker compose up --build

# 4. Acessar
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# Docs API: http://localhost:8000/docs
```

---

## Deploy Produção

```bash
# Usar docker-compose.prod.yml
docker compose -f docker-compose.prod.yml up -d --build
```

---

## Roadmap

- [x] Estrutura base do backend (FastAPI + TimescaleDB)
- [x] Coletores: Mautic API, DB, VPS SSH, SendPost, Avant SMS
- [x] Modelos de dados e routers
- [x] Scheduler de coleta periódica
- [x] Motor de alertas (email + SMS)
- [x] Preview do frontend (design aprovado)
- [ ] Frontend Next.js — implementação
- [ ] Migrations Alembic
- [ ] Testes automatizados
- [ ] CI/CD GitHub Actions
