# Mini Plano de Ajustes — Pré-Verificação

> Ajustes definidos antes da fase de verificação e deploy do Mautic Monitor.
> Executados na ordem recomendada, sem alteração de comportamento existente.

---

## Status Geral

| Ajuste | Descrição | Status |
|--------|-----------|--------|
| 1 | VPS & Logs: cadastro de nova VPS via frontend | ✅ Concluído |
| 2 | Gateways: credenciais editáveis via frontend | ✅ Concluído |
| 3 | Avant SMS: coleta de dados por cliente via webhook | ✅ Concluído |
| 4 | Relatório MySQL: busca cross-instance por empresa | ✅ Concluído |

---

## Ajuste 1 — VPS & Logs: Cadastro de nova VPS via frontend ✅

**Objetivo:** Permitir que novas VPS sejam cadastradas e gerenciadas diretamente pelo frontend, sem necessidade de intervenção manual no servidor backend.

**Solução implementada:** Opção A — Backend gera o par de chaves RSA automaticamente.

### Fluxo UX (wizard 2 passos)
1. Usuário preenche: nome, host SSH, porta, usuário
2. Backend gera par RSA 4096 — chave privada armazenada criptografada (Fernet), chave pública retornada
3. Frontend exibe chave pública com botão "Copiar" e instruções para adicionar em `~/.ssh/authorized_keys` na VPS
4. Botão "Testar conexão" chama `POST /instances/{id}/test-ssh` e exibe resultado em tempo real

### Arquivos alterados

**Backend:**
- `backend/app/models/instance.py` — campos `ssh_private_key_enc` + `ssh_public_key`
- `backend/alembic/versions/003_add_ssh_keys.py` — migration ADD COLUMN
- `backend/app/routers/instances.py` — endpoints `generate-ssh-key` + `test-ssh` + `InstanceOut` com campos SSH
- `backend/app/collectors/vps_ssh.py` — aceita `private_key_pem` (banco) ou `key_path` (fallback legado)
- `backend/app/scheduler.py` — usa chave do banco se disponível

**Frontend:**
- `frontend/lib/api/instances.ts` — tipos `SshKeyOut`, `SshTestResult`; métodos `generateSshKey`, `testSsh`
- `frontend/lib/hooks/useInstances.ts` — hooks `useGenerateSshKey`, `useTestSsh`
- `frontend/components/dashboard/vps/VpsFormModal.tsx` — wizard 2 passos com UX completo
- `frontend/components/dashboard/vps/VpsResourceCards.tsx` — cards com badge SSH, editar/remover
- `frontend/components/ui/ConfirmModal.tsx` — novo componente reutilizável
- `frontend/app/(dashboard)/vps/page.tsx` — botão "Nova VPS" no topnav

---

## Ajuste 2 — Gateways: Credenciais editáveis via frontend ✅

**Objetivo:** Permitir que as credenciais de Sendpost e Avant SMS sejam configuradas pela interface, sem modificar variáveis de ambiente manualmente.

**Solução implementada:** Tabela `gateway_configs` (chave-valor com Fernet) + helper `get_gateway_setting()` com fallback para `.env`.

### Arquivos alterados

**Backend:**
- `backend/app/models/gateway_config.py` — modelo `GatewayConfig`: `key` (PK), `value_enc`, `updated_at`
- `backend/alembic/versions/004_add_gateway_configs.py` — migration CREATE TABLE
- `backend/app/routers/gateways.py` — `GET /gateways/config` + `PATCH /gateways/config`
- `backend/app/utils/gateway_settings.py` — helper `get_gateway_setting(db, key, fallback)`
- `backend/app/collectors/sendpost.py` — construtor aceita `api_key` + `from_email` (banco > settings)
- `backend/app/collectors/avant_sms.py` — construtor aceita `token` + `base_url` (banco > settings)
- `backend/app/scheduler.py` — `job_collect_gateways` usa `get_gateway_setting()` antes de instanciar coletores
- `backend/app/main.py` — router `gateways` registrado

**Frontend:**
- `frontend/lib/api/gateways.ts` — tipos `GatewayConfigField`, `GatewayConfigOut`, `GatewayConfigPatch`; métodos `getConfig`, `updateConfig`
- `frontend/lib/hooks/useGatewayConfig.ts` — hooks `useGatewayConfig`, `useSaveGatewayConfig`
- `frontend/lib/constants/ui.ts` — tab "Configurações" adicionada em `PAGE_TABS.gateways`
- `frontend/components/dashboard/gateways/GatewayCredentialsForm.tsx` — form com campos mascarados e badge "Configurado"
- `frontend/app/(dashboard)/gateways/page.tsx` — tab config renderiza `GatewayCredentialsForm`

**Chaves gerenciadas:**
- Sendpost: `sendpost_api_key`, `sendpost_alert_from_email`
- Avant: `avant_sms_token`, `avant_sms_api_base_url`

---

## Ajuste 3 — Avant SMS: Coleta de dados por cliente via webhook ✅

**Objetivo:** Coletar SMS enviados, entregues, falhas e saldo de créditos por cliente, usando `costCenterCode` como identificador de cliente.

**Abordagem aprovada:** Padrão webhook (DLR callbacks) + tabela de correlação `costCenterCode → nome do cliente`. A API Avant não possui endpoint de relatório por cliente — o `costCenterCode` é enviado com cada SMS e retornado nos callbacks de status.

### Especificação da API Avant (documentada)

| Item | Valor |
|------|-------|
| URL envio SMS | `https://channel.solucoesdigitais.dev/sms/message/send` |
| URL saldo | `http://api-messaging.solucoesdigitais.cc/sms/balance/get` |
| Auth header | `Authorization: alpha {TOKEN}` |
| Saldo — campo | `{"current": N}` |
| Callback — campo cliente | `costCenterCode` |
| Callback — status possíveis | `DELIVRD`, `UNDELIV`, `EXPIRED`, `UNKNOWN`, `REJECTD` |

### Itens

| # | Camada | Ação |
|---|--------|------|
| 3.1 | Backend — `avant_sms.py` | Corrigir URL base, auth (`alpha {token}`), balance endpoint e campo `current` |
| 3.2 | Backend — `report_sender.py` | Corrigir endpoint de envio SMS e header de autenticação |
| 3.3 | Backend — Modelos | Criar `AvantCostCenter`: `code` (PK), `client_name`, `active` |
| 3.4 | Backend — Modelos | Criar `AvantSmsLog`: `id`, `avant_message_id`, `cost_center_code`, `recipient`, `status`, `error_code`, `sent_at`, `delivered_at` |
| 3.5 | Backend — Migration | Migration 005 para as duas tabelas |
| 3.6 | Backend — Router | `GET/POST/DELETE /gateways/avant/cost-centers` — gerenciamento da tabela de correlação |
| 3.7 | Backend — Webhook | `POST /webhooks/avant` — recebe DLR callbacks, upsert em `AvantSmsLog` |
| 3.8 | Backend — `avant_sms.py` | `collect()` retorna saldo real + stats por `costCenterCode` do banco |
| 3.9 | Frontend | Tab Avant: stat cards globais + tabela por cliente (com `costCenterCode`) |
| 3.10 | Frontend | Tab Configurações: seção "Cost Centers" — cadastrar/remover correlações código↔cliente |

### Fluxo de dados

```
Envio SMS → costCenterCode incluso no payload
          ↓
Avant SMS → callback DLR → POST /webhooks/avant
                          ↓
                    AvantSmsLog (upsert por avant_message_id)
                          ↓
avant_sms.collect() → agrupa por costCenterCode → exibe no frontend
```

---

## Ajuste 4 — Relatório MySQL: Busca cross-instance por empresa ✅

**Objetivo:** O coletor MySQL deve buscar dados da empresa (por `mautic_company_id`) em **todas** as instâncias Mautic cadastradas, não apenas na instância vinculada ao `ReportConfig`.

**Solução implementada:** `report_generator.py` itera todas as instâncias ativas com MySQL configurado, coleta em paralelo via `asyncio.gather`, agrega totais e mantém breakdown por instância.

### Arquivos alterados

**Backend:**
- `backend/app/services/report_generator.py` — reescrito: coleta paralela cross-instance, `_aggregate()`, `_collect_instance()` com tolerância a falhas parciais
- `backend/app/templates/report.html.j2` — exibe totais globais + seção "Consolidado por Instância" (quando `show_breakdown = True`)

**Nota:** `ReportConfig.instance_id` passa a ser apenas referência de contexto — a coleta é sempre cross-instance por `mautic_company_id`.

---

## Ordem de execução

```
Ajuste 1 ✅  VPS frontend          → sem risco, só frontend + 2 endpoints backend
Ajuste 2 ✅  Gateway config        → backend + frontend, migration nova
Ajuste 4 ✅  MySQL cross-instance  → backend, sem nova tabela
Ajuste 3 ✅  Avant por cliente     → webhook DLR + costCenterCode + stats por cliente
```
