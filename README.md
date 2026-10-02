# TI Agenda v3

Vue 3 + FastAPI + SQLite (local) / Cloudflare D1 (produção).

Inclui autenticação por token, perfis Administrador/Técnico/Solicitante, cadastro/desativação de usuários (administrador), alteração de senha, agendamentos, calendário mensal, busca, status e número automático de chamado.

## Uso local
Python 3.10+ e Node.js 18+.

1. Extraia o ZIP ou clone o repositório.
2. Execute `INSTALAR_E_INICIAR.bat`.
3. Execute `INICIAR.bat`.
4. Acesse `http://127.0.0.1:5173`.

Primeiro acesso: usuário `admin`, senha `admin123`. Altere a senha imediatamente.

API local: `http://127.0.0.1:8000` · Docs: `/docs`.

## Deploy no Cloudflare (Pages + Workers + D1)

Veja o guia completo em [`worker/README-DEPLOY.md`](worker/README-DEPLOY.md).

Resumo:

1. Crie o banco D1: `npx wrangler d1 create ti-agenda-db`
2. Atualize o `database_id` em `worker/wrangler.toml`
3. Defina o secret: `npx wrangler secret put TI_AGENDA_SECRET`
4. Deploy da API: `cd worker && npx wrangler deploy`
5. Conecte o repositório no **Cloudflare Pages**:
   - Build command: `cd frontend && npm ci && npm run build`
   - Output: `frontend/dist`
   - Env var: `VITE_API_URL` = URL do Worker + `/api`

## Estrutura
- `frontend/` — Vue 3 + Vite
- `backend/` — FastAPI + SQLite (desenvolvimento local)
- `worker/` — FastAPI adaptado para Cloudflare Workers + D1 (produção)

## Atenção
Configure `TI_AGENDA_SECRET` com chave longa e aleatória. Esta é uma versão inicial; ainda não há regras de escopo por solicitante nem recuperação de senha.
