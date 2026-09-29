# TI Agenda v3

Vue 3 + FastAPI + SQLite. Inclui autenticação por token, perfis Administrador/Técnico/Solicitante, cadastro/desativação de usuários (administrador), alteração de senha, agendamentos, calendário mensal, busca, status e número automático de chamado.

## Requisitos
Python 3.10+ e Node.js 18+.

## Instalar e iniciar
1. Extraia o ZIP em uma pasta, por exemplo `C:\\netdata\\ti-agenda-v3`.
2. Execute `INSTALAR_E_INICIAR.bat`.
3. Execute `INICIAR.bat`.
4. Acesse `http://127.0.0.1:5173`.

Primeiro acesso: usuário `admin`, senha `admin123`. Altere a senha imediatamente em Alterar senha.
API: `http://127.0.0.1:8000`; documentação: `/docs`.

## Atenção antes de disponibilizar na rede
Configure `TI_AGENDA_SECRET` com uma chave longa e aleatória, use HTTPS e implemente política de backup do arquivo `backend/ti_agenda.db`. Esta é uma versão inicial; os perfis autenticam usuários e restringem operações administrativas, mas ainda não há regras de escopo por solicitante nem recuperação de senha.
