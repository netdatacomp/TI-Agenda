"""
TI Agenda API - Cloudflare Workers (Python + FastAPI + D1)
"""
import hmac, hashlib, base64, json, time, os
from datetime import datetime
from typing import Optional, Any
from fastapi import FastAPI, Request, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from workers import asgi, WorkerEntrypoint

# ---------- Helpers ----------
def get_secret(env) -> str:
    return getattr(env, "TI_AGENDA_SECRET", None) or "troque-esta-chave-secreta-antes-de-publicar"

def hash_password(pw: str, salt: bytes = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 180000)
    return base64.b64encode(salt).decode() + ":" + base64.b64encode(digest).decode()

def verify_password(pw: str, stored: str) -> bool:
    try:
        s, d = stored.split(":")
        salt = base64.b64decode(s)
        expected = base64.b64decode(d)
        return hmac.compare_digest(
            hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 180000), expected
        )
    except Exception:
        return False

def token_for(user_id: int, secret: str) -> str:
    payload = base64.urlsafe_b64encode(
        json.dumps({"uid": user_id, "exp": int(time.time()) + 43200}).encode()
    ).decode().rstrip("=")
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return payload + "." + sig

def parse_token(token: str, secret: str) -> Optional[dict]:
    try:
        payload, sig = token.split(".")
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if data["exp"] < time.time():
            return None
        return data
    except Exception:
        return None

# ---------- Pydantic models ----------
class LoginIn(BaseModel):
    username: str
    password: str

class UserIn(BaseModel):
    name: str
    username: str
    password: str
    role: str = "Técnico"

class PasswordIn(BaseModel):
    current_password: str
    new_password: str

class AppointmentIn(BaseModel):
    title: str
    type: str
    requester: str
    department: Optional[str] = ""
    location: Optional[str] = ""
    technician: Optional[str] = ""
    start: datetime
    end: datetime
    priority: Optional[str] = "Normal"
    status: Optional[str] = "Agendado"
    description: Optional[str] = ""
    notes: Optional[str] = ""

class AppointmentOut(AppointmentIn):
    id: int
    ticket_number: Optional[str] = None

class UserOut(BaseModel):
    id: int
    name: str
    username: str
    role: str
    active: int

# ---------- App ----------
app = FastAPI(title="TI Agenda API", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ajuste para o domínio do Pages depois
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_env(request: Request):
    return request.scope.get("env")

async def ensure_schema(db):
    """Cria tabelas se não existirem e seed do admin."""
    await db.prepare("""
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          username TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL,
          role TEXT DEFAULT 'Técnico',
          active INTEGER DEFAULT 1
        )
    """).run()
    await db.prepare("""
        CREATE TABLE IF NOT EXISTS appointments (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          ticket_number TEXT UNIQUE,
          title TEXT NOT NULL,
          type TEXT NOT NULL,
          requester TEXT NOT NULL,
          department TEXT DEFAULT '',
          location TEXT DEFAULT '',
          technician TEXT DEFAULT '',
          start TEXT NOT NULL,
          \"end\" TEXT NOT NULL,
          priority TEXT DEFAULT 'Normal',
          status TEXT DEFAULT 'Agendado',
          description TEXT DEFAULT '',
          notes TEXT DEFAULT ''
        )
    """).run()
    # seed admin
    r = await db.prepare("SELECT id FROM users WHERE username = ?").bind("admin").first()
    if not r:
        ph = hash_password("admin123")
        await db.prepare(
            "INSERT INTO users (name, username, password_hash, role, active) VALUES (?, ?, ?, ?, 1)"
        ).bind("Administrador TI", "admin", ph, "Administrador").run()

async def current_user(request: Request, authorization: str = Header(default="")):
    env = get_env(request)
    secret = get_secret(env)
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Sessão necessária.")
    data = parse_token(authorization[7:], secret)
    if not data:
        raise HTTPException(401, "Sessão inválida ou expirada.")
    db = env.DB
    row = await db.prepare("SELECT id, name, username, role, active FROM users WHERE id = ?").bind(data["uid"]).first()
    if not row or not row["active"]:
        raise HTTPException(401, "Sessão inválida ou expirada.")
    return dict(row)

async def admin_user(request: Request, authorization: str = Header(default="")):
    u = await current_user(request, authorization)
    if u["role"] != "Administrador":
        raise HTTPException(403, "Ação exclusiva do administrador.")
    return u

@app.get("/api/health")
async def health(request: Request):
    env = get_env(request)
    await ensure_schema(env.DB)
    return {"status": "ok", "version": "3.0.0", "runtime": "cloudflare-workers"}

@app.post("/api/auth/login")
async def login(data: LoginIn, request: Request):
    env = get_env(request)
    db = env.DB
    await ensure_schema(db)
    row = await db.prepare(
        "SELECT id, name, username, role, password_hash, active FROM users WHERE username = ? AND active = 1"
    ).bind(data.username).first()
    if not row or not verify_password(data.password, row["password_hash"]):
        raise HTTPException(401, "Usuário ou senha incorretos.")
    secret = get_secret(env)
    return {
        "access_token": token_for(row["id"], secret),
        "token_type": "bearer",
        "user": {"id": row["id"], "name": row["name"], "username": row["username"], "role": row["role"]},
    }

@app.get("/api/auth/me")
async def me(request: Request, authorization: str = Header(default="")):
    u = await current_user(request, authorization)
    return {"id": u["id"], "name": u["name"], "username": u["username"], "role": u["role"]}

@app.post("/api/auth/change-password")
async def change_password(data: PasswordIn, request: Request, authorization: str = Header(default="")):
    u = await current_user(request, authorization)
    env = get_env(request)
    db = env.DB
    row = await db.prepare("SELECT password_hash FROM users WHERE id = ?").bind(u["id"]).first()
    if not verify_password(data.current_password, row["password_hash"]):
        raise HTTPException(400, "Senha atual incorreta.")
    if len(data.new_password) < 8:
        raise HTTPException(400, "A nova senha deve ter ao menos 8 caracteres.")
    ph = hash_password(data.new_password)
    await db.prepare("UPDATE users SET password_hash = ? WHERE id = ?").bind(ph, u["id"]).run()
    return {"message": "Senha alterada."}

@app.get("/api/users")
async def list_users(request: Request, authorization: str = Header(default="")):
    await current_user(request, authorization)
    env = get_env(request)
    db = env.DB
    rows = await db.prepare(
        "SELECT id, name, username, role, active FROM users WHERE active = 1 ORDER BY name"
    ).all()
    return [dict(r) for r in rows.results]

@app.post("/api/users", status_code=201)
async def create_user(data: UserIn, request: Request, authorization: str = Header(default="")):
    await admin_user(request, authorization)
    if len(data.password) < 8:
        raise HTTPException(400, "A senha deve ter ao menos 8 caracteres.")
    if data.role not in ["Administrador", "Técnico", "Solicitante"]:
        raise HTTPException(400, "Perfil inválido.")
    env = get_env(request)
    db = env.DB
    exists = await db.prepare("SELECT id FROM users WHERE username = ?").bind(data.username).first()
    if exists:
        raise HTTPException(400, "Usuário já cadastrado.")
    ph = hash_password(data.password)
    result = await db.prepare(
        "INSERT INTO users (name, username, password_hash, role, active) VALUES (?, ?, ?, ?, 1) RETURNING id, name, username, role, active"
    ).bind(data.name, data.username, ph, data.role).first()
    return dict(result)

@app.patch("/api/users/{uid}/deactivate")
async def deactivate(uid: int, request: Request, authorization: str = Header(default="")):
    u = await admin_user(request, authorization)
    if uid == u["id"]:
        raise HTTPException(400, "Não é possível desativar a própria conta.")
    env = get_env(request)
    db = env.DB
    row = await db.prepare("SELECT id FROM users WHERE id = ?").bind(uid).first()
    if not row:
        raise HTTPException(404, "Usuário não encontrado.")
    await db.prepare("UPDATE users SET active = 0 WHERE id = ?").bind(uid).run()
    return {"message": "Usuário desativado."}

@app.get("/api/appointments")
async def list_appointments(request: Request, authorization: str = Header(default="")):
    await current_user(request, authorization)
    env = get_env(request)
    db = env.DB
    rows = await db.prepare(
        "SELECT id, ticket_number, title, type, requester, department, location, technician, start, \"end\", priority, status, description, notes FROM appointments ORDER BY start ASC"
    ).all()
    out = []
    for r in rows.results:
        d = dict(r)
        out.append(d)
    return out

@app.post("/api/appointments", status_code=201)
async def create_appointment(data: AppointmentIn, request: Request, authorization: str = Header(default="")):
    await current_user(request, authorization)
    if data.end <= data.start:
        raise HTTPException(400, "Horário final deve ser posterior ao inicial.")
    env = get_env(request)
    db = env.DB
    count = await db.prepare("SELECT COUNT(*) as c FROM appointments").first()
    n = (count["c"] if count else 0) + 1
    ticket = f"TI-{datetime.now().year}-{n:05d}"
    start_s = data.start.isoformat()
    end_s = data.end.isoformat()
    result = await db.prepare(
        """INSERT INTO appointments (ticket_number, title, type, requester, department, location, technician, start, \"end\", priority, status, description, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           RETURNING id, ticket_number, title, type, requester, department, location, technician, start, \"end\", priority, status, description, notes"""
    ).bind(
        ticket, data.title, data.type, data.requester, data.department or "",
        data.location or "", data.technician or "", start_s, end_s,
        data.priority or "Normal", data.status or "Agendado",
        data.description or "", data.notes or ""
    ).first()
    return dict(result)

@app.put("/api/appointments/{aid}")
async def update_appointment(aid: int, data: AppointmentIn, request: Request, authorization: str = Header(default="")):
    await current_user(request, authorization)
    if data.end <= data.start:
        raise HTTPException(400, "Horário final deve ser posterior ao inicial.")
    env = get_env(request)
    db = env.DB
    row = await db.prepare("SELECT id FROM appointments WHERE id = ?").bind(aid).first()
    if not row:
        raise HTTPException(404, "Agendamento não encontrado.")
    start_s = data.start.isoformat()
    end_s = data.end.isoformat()
    result = await db.prepare(
        """UPDATE appointments SET title=?, type=?, requester=?, department=?, location=?, technician=?,
           start=?, \"end\"=?, priority=?, status=?, description=?, notes=?
           WHERE id=?
           RETURNING id, ticket_number, title, type, requester, department, location, technician, start, \"end\", priority, status, description, notes"""
    ).bind(
        data.title, data.type, data.requester, data.department or "",
        data.location or "", data.technician or "", start_s, end_s,
        data.priority or "Normal", data.status or "Agendado",
        data.description or "", data.notes or "", aid
    ).first()
    return dict(result)

@app.delete("/api/appointments/{aid}")
async def delete_appointment(aid: int, request: Request, authorization: str = Header(default="")):
    await admin_user(request, authorization)
    env = get_env(request)
    db = env.DB
    row = await db.prepare("SELECT id FROM appointments WHERE id = ?").bind(aid).first()
    if not row:
        raise HTTPException(404, "Agendamento não encontrado.")
    await db.prepare("DELETE FROM appointments WHERE id = ?").bind(aid).run()
    return {"message": "Agendamento excluído."}

# ---------- Worker entrypoint ----------
class Default(WorkerEntrypoint):
    async def fetch(self, request):
        return await asgi.fetch(app, request, self.env)
