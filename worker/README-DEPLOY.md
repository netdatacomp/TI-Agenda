# Deploy TI Agenda no Cloudflare (Pages + Workers + D1)

## 1. Pré-requisitos
- Conta Cloudflare
- Node.js + npm
- Wrangler: `npm install -g wrangler` (ou use npx)

## 2. Banco D1
```bash
npx wrangler login
npx wrangler d1 create ti-agenda-db
```
Copie o `database_id` gerado e cole em `worker/wrangler.toml` no campo `database_id`.

Opcional – aplicar schema manualmente:
```bash
npx wrangler d1 execute ti-agenda-db --remote --file=worker/schema.sql
```
(O código também cria as tabelas automaticamente no primeiro request.)

## 3. Secret
```bash
cd worker
npx wrangler secret put TI_AGENDA_SECRET
```
Digite uma chave longa e aleatória (ex: `openssl rand -hex 32`).

## 4. Deploy da API (Workers)
```bash
cd worker
npx wrangler deploy
```
Anote a URL gerada, ex: `https://ti-agenda-api.<seu-subdominio>.workers.dev`

## 5. Frontend no Cloudflare Pages
1. Acesse [dash.cloudflare.com](https://dash.cloudflare.com) → Workers & Pages → Create → Pages → Connect to Git
2. Selecione o repositório `netdatacomp/TI-Agenda`
3. Configurações de build:
   - **Framework preset**: Vue
   - **Build command**: `cd frontend && npm ci && npm run build`
   - **Build output directory**: `frontend/dist`
   - **Root directory**: `/` (deixe em branco se pedir)
4. Variáveis de ambiente (Settings → Environment variables):
   - `VITE_API_URL` = `https://ti-agenda-api.<seu-subdominio>.workers.dev/api`
5. Save and Deploy

## 6. CORS (opcional mas recomendado)
Depois de ter a URL do Pages, edite `worker/main.py` e troque `allow_origins=["*"]` pelo domínio real do Pages, depois faça `npx wrangler deploy` de novo.

## Login inicial
- Usuário: `admin`
- Senha: `admin123`
- Altere a senha imediatamente.

## Desenvolvimento local
O backend original (FastAPI + SQLite local) continua funcionando com os arquivos `.bat`.
O frontend usa `VITE_API_URL` se definida, senão `http://127.0.0.1:8000/api`.
