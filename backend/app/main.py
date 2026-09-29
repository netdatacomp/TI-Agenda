import os, hmac, hashlib, base64, json, time
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

DB=os.getenv("TI_AGENDA_DB","sqlite:///./ti_agenda.db")
engine=create_engine(DB,connect_args={"check_same_thread":False} if DB.startswith("sqlite") else {})
SessionLocal=sessionmaker(bind=engine,autocommit=False,autoflush=False)
Base=declarative_base()
SECRET=os.getenv("TI_AGENDA_SECRET","troque-esta-chave-secreta-antes-de-publicar")

class User(Base):
 __tablename__="users"
 id=Column(Integer,primary_key=True); name=Column(String(150),nullable=False)
 username=Column(String(80),unique=True,nullable=False,index=True)
 password_hash=Column(String(300),nullable=False); role=Column(String(30),default="Técnico")
 active=Column(Integer,default=1)
class Appointment(Base):
 __tablename__="appointments"
 id=Column(Integer,primary_key=True,index=True); ticket_number=Column(String(30),unique=True,index=True)
 title=Column(String(200),nullable=False); type=Column(String(50),nullable=False)
 requester=Column(String(150),nullable=False); department=Column(String(150),default="")
 location=Column(String(200),default=""); technician=Column(String(150),default="")
 start=Column(DateTime,nullable=False); end=Column(DateTime,nullable=False)
 priority=Column(String(30),default="Normal"); status=Column(String(30),default="Agendado")
 description=Column(Text,default=""); notes=Column(Text,default="")
Base.metadata.create_all(bind=engine)

def hash_password(pw,salt=None):
 salt=salt or os.urandom(16)
 digest=hashlib.pbkdf2_hmac("sha256",pw.encode(),salt,180000)
 return base64.b64encode(salt).decode()+":"+base64.b64encode(digest).decode()
def verify_password(pw,stored):
 try:
  s,d=stored.split(":"); salt=base64.b64decode(s); expected=base64.b64decode(d)
  return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256",pw.encode(),salt,180000),expected)
 except Exception:return False
def token_for(user):
 payload=base64.urlsafe_b64encode(json.dumps({"uid":user.id,"exp":int(time.time())+43200}).encode()).decode().rstrip("=")
 sig=hmac.new(SECRET.encode(),payload.encode(),hashlib.sha256).hexdigest()
 return payload+"."+sig
def db():
 s=SessionLocal()
 try:yield s
 finally:s.close()
with SessionLocal() as s:
 if not s.query(User).filter(User.username=="admin").first():
  s.add(User(name="Administrador TI",username="admin",password_hash=hash_password("admin123"),role="Administrador"));s.commit()

app=FastAPI(title="TI Agenda API",version="3.0.0")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:5173","http://127.0.0.1:5173"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
class LoginIn(BaseModel):username:str;password:str
class UserIn(BaseModel):name:str;username:str;password:str;role:str="Técnico"
class PasswordIn(BaseModel):current_password:str;new_password:str
class AppointmentIn(BaseModel):
 title:str;type:str;requester:str;department:Optional[str]="";location:Optional[str]="";technician:Optional[str]=""
 start:datetime;end:datetime;priority:Optional[str]="Normal";status:Optional[str]="Agendado";description:Optional[str]="";notes:Optional[str]=""
class AppointmentOut(AppointmentIn):
 id:int;ticket_number:Optional[str]=None
 class Config:from_attributes=True
class UserOut(BaseModel):
 id:int;name:str;username:str;role:str;active:int
 class Config:from_attributes=True
def current_user(authorization:str=Header(default=""),s:Session=Depends(db)):
 if not authorization.startswith("Bearer "):raise HTTPException(401,"Sessão necessária.")
 try:
  payload,sig=authorization[7:].split(".");expected=hmac.new(SECRET.encode(),payload.encode(),hashlib.sha256).hexdigest()
  if not hmac.compare_digest(sig,expected):raise ValueError()
  data=json.loads(base64.urlsafe_b64decode(payload+"="*(-len(payload)%4)))
  if data["exp"]<time.time():raise ValueError()
  u=s.get(User,data["uid"])
  if not u or not u.active:raise ValueError()
  return u
 except Exception:raise HTTPException(401,"Sessão inválida ou expirada.")
def admin(u=Depends(current_user)):
 if u.role!="Administrador":raise HTTPException(403,"Ação exclusiva do administrador.")
 return u
@app.get("/api/health")
def health():return {"status":"ok","version":"3.0.0"}
@app.post("/api/auth/login")
def login(data:LoginIn,s:Session=Depends(db)):
 u=s.query(User).filter(User.username==data.username,User.active==1).first()
 if not u or not verify_password(data.password,u.password_hash):raise HTTPException(401,"Usuário ou senha incorretos.")
 return {"access_token":token_for(u),"token_type":"bearer","user":{"id":u.id,"name":u.name,"username":u.username,"role":u.role}}
@app.get("/api/auth/me")
def me(u=Depends(current_user)):return {"id":u.id,"name":u.name,"username":u.username,"role":u.role}
@app.post("/api/auth/change-password")
def change_password(data:PasswordIn,u=Depends(current_user),s:Session=Depends(db)):
 if not verify_password(data.current_password,u.password_hash):raise HTTPException(400,"Senha atual incorreta.")
 if len(data.new_password)<8:raise HTTPException(400,"A nova senha deve ter ao menos 8 caracteres.")
 u.password_hash=hash_password(data.new_password);s.commit();return {"message":"Senha alterada."}
@app.get("/api/users",response_model=list[UserOut])
def users(u=Depends(current_user),s:Session=Depends(db)):return s.query(User).filter(User.active==1).order_by(User.name).all()
@app.post("/api/users",response_model=UserOut,status_code=201)
def create_user(data:UserIn,u=Depends(admin),s:Session=Depends(db)):
 if len(data.password)<8:raise HTTPException(400,"A senha deve ter ao menos 8 caracteres.")
 if data.role not in ["Administrador","Técnico","Solicitante"]:raise HTTPException(400,"Perfil inválido.")
 if s.query(User).filter(User.username==data.username).first():raise HTTPException(400,"Usuário já cadastrado.")
 x=User(name=data.name,username=data.username,password_hash=hash_password(data.password),role=data.role);s.add(x);s.commit();s.refresh(x);return x
@app.patch("/api/users/{uid}/deactivate")
def deactivate(uid:int,u=Depends(admin),s:Session=Depends(db)):
 x=s.get(User,uid)
 if not x:raise HTTPException(404,"Usuário não encontrado.")
 if x.id==u.id:raise HTTPException(400,"Não é possível desativar a própria conta.")
 x.active=0;s.commit();return {"message":"Usuário desativado."}
@app.get("/api/appointments",response_model=list[AppointmentOut])
def list_appointments(u=Depends(current_user),s:Session=Depends(db)):return s.query(Appointment).order_by(Appointment.start.asc()).all()
@app.post("/api/appointments",response_model=AppointmentOut,status_code=201)
def create_appointment(data:AppointmentIn,u=Depends(current_user),s:Session=Depends(db)):
 if data.end<=data.start:raise HTTPException(400,"Horário final deve ser posterior ao inicial.")
 n=s.query(Appointment).count()+1;ticket=f"TI-{datetime.now().year}-{n:05d}"
 x=Appointment(**data.model_dump(),ticket_number=ticket);s.add(x);s.commit();s.refresh(x);return x
@app.put("/api/appointments/{aid}",response_model=AppointmentOut)
def update_appointment(aid:int,data:AppointmentIn,u=Depends(current_user),s:Session=Depends(db)):
 x=s.get(Appointment,aid)
 if not x:raise HTTPException(404,"Agendamento não encontrado.")
 if data.end<=data.start:raise HTTPException(400,"Horário final deve ser posterior ao inicial.")
 for k,v in data.model_dump().items():setattr(x,k,v)
 s.commit();s.refresh(x);return x
@app.delete("/api/appointments/{aid}")
def delete_appointment(aid:int,u=Depends(admin),s:Session=Depends(db)):
 x=s.get(Appointment,aid)
 if not x:raise HTTPException(404,"Agendamento não encontrado.")
 s.delete(x);s.commit();return {"message":"Agendamento excluído."}
