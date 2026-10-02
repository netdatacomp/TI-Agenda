<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const API=import.meta.env.VITE_API_URL||'http://127.0.0.1:8000/api'
const token=ref(localStorage.getItem('ti_token')||'')
const user=ref(JSON.parse(localStorage.getItem('ti_user')||'null'))
const loginData=ref({username:'',password:''})
const loginError=ref('')

const api=axios.create({baseURL:API})

api.interceptors.request.use(c=>{
  if(token.value)c.headers.Authorization=`Bearer ${token.value}`
  return c
})

const appointments=ref([])
const users=ref([])
const modal=ref(false)
const userModal=ref(false)
const passModal=ref(false)
const editId=ref(null)
const search=ref('')
const status=ref('Todos')
const view=ref('lista')
const month=ref(new Date())
const loading=ref(false)

const newUser=ref({
  name:'',
  username:'',
  password:'',
  role:'Técnico'
})

const pw=ref({
  current_password:'',
  new_password:''
})

const blank=()=>({
  title:'',
  type:'Suporte técnico',
  requester:'',
  department:'',
  location:'',
  technician:'',
  date:new Date().toISOString().slice(0,10),
  startTime:'08:00',
  endTime:'09:00',
  priority:'Normal',
  status:'Agendado',
  description:'',
  notes:''
})

const form=ref(blank())

const isAdmin=computed(()=>user.value?.role==='Administrador')

const filtered=computed(()=>appointments.value.filter(a=>{
  let q=search.value.toLowerCase()

  return (!q||`${a.ticket_number} ${a.title} ${a.requester} ${a.department} ${a.technician}`
    .toLowerCase().includes(q))
    &&(status.value==='Todos'||a.status===status.value)
}))

const today=computed(()=>appointments.value.filter(a=>
  new Date(a.start).toDateString()===new Date().toDateString()
).length)

const openCount=computed(()=>appointments.value.filter(a=>
  ['Agendado','Em andamento'].includes(a.status)
).length)

const monthLabel=computed(()=>month.value.toLocaleDateString('pt-BR',{
  month:'long',
  year:'numeric'
}))

const days=computed(()=>{
  let y=month.value.getFullYear()
  let m=month.value.getMonth()
  let f=new Date(y,m,1)
  let l=new Date(y,m+1,0)
  let a=[]

  for(let i=0;i<f.getDay();i++)a.push(null)
  for(let d=1;d<=l.getDate();d++)a.push(new Date(y,m,d))

  return a
})

async function signIn(){
  loginError.value=''

  try{
    let r=await axios.post(API+'/auth/login',loginData.value)

    token.value=r.data.access_token
    user.value=r.data.user

    localStorage.setItem('ti_token',token.value)
    localStorage.setItem('ti_user',JSON.stringify(user.value))

    await load()
  }catch(e){
    loginError.value=e.response?.data?.detail||'Falha no login.'
  }
}

function logout(){
  token.value=''
  user.value=null
  appointments.value=[]

  localStorage.removeItem('ti_token')
  localStorage.removeItem('ti_user')
}

async function load(){
  if(!token.value)return

  loading.value=true

  try{
    appointments.value=(await api.get('/appointments')).data

    if(isAdmin.value)
      users.value=(await api.get('/users')).data
  }catch(e){
    if(e.response?.status===401)logout()
  }finally{
    loading.value=false
  }
}

async function save(){
  let p={
    ...form.value,
    start:form.value.date+'T'+form.value.startTime+':00',
    end:form.value.date+'T'+form.value.endTime+':00'
  }

  try{
    if(editId.value)
      await api.put('/appointments/'+editId.value,p)
    else
      await api.post('/appointments',p)

    modal.value=false
    await load()
  }catch(e){
    alert(e.response?.data?.detail||'Erro ao salvar')
  }
}

function openNew(){
  editId.value=null
  form.value=blank()
  modal.value=true
}

function openEdit(a){
  editId.value=a.id

  let s=new Date(a.start)
  let e=new Date(a.end)

  form.value={
    title:a.title,
    type:a.type,
    requester:a.requester,
    department:a.department||'',
    location:a.location||'',
    technician:a.technician||'',
    date:s.toISOString().slice(0,10),
    startTime:s.toTimeString().slice(0,5),
    endTime:e.toTimeString().slice(0,5),
    priority:a.priority,
    status:a.status,
    description:a.description||'',
    notes:a.notes||''
  }

  modal.value=true
}

async function remove(a){
  if(!confirm('Excluir '+a.ticket_number+'?'))return

  try{
    await api.delete('/appointments/'+a.id)
    await load()
  }catch(e){
    alert(e.response?.data?.detail||'Erro')
  }
}

async function addUser(){
  try{
    await api.post('/users',newUser.value)

    newUser.value={
      name:'',
      username:'',
      password:'',
      role:'Técnico'
    }

    await load()
  }catch(e){
    alert(e.response?.data?.detail||'Erro')
  }
}

async function deactivate(u){
  if(!confirm('Desativar '+u.name+'?'))return

  try{
    await api.patch('/users/'+u.id+'/deactivate')
    await load()
  }catch(e){
    alert(e.response?.data?.detail||'Erro')
  }
}

async function changePassword(){
  try{
    await api.post('/auth/change-password',pw.value)

    passModal.value=false

    pw.value={
      current_password:'',
      new_password:''
    }

    alert('Senha alterada')
  }catch(e){
    alert(e.response?.data?.detail||'Erro')
  }
}

onMounted(load)
</script>

<template>

<div v-if="!user" class="login">

  <div class="card">

    <div class="loginBrand">TI Agenda</div>

    <h1>Suporte Técnico</h1>

    <p class="loginSubtitle">
      Gerenciamento de chamados e agendamentos de TI
    </p>

    <form @submit.prevent="signIn">

      <label>
        Usuário
        <input
          v-model="loginData.username"
          placeholder="Digite seu usuário"
          required
          autofocus
        >
      </label>

      <label>
        Senha
        <input
          v-model="loginData.password"
          type="password"
          placeholder="Digite sua senha"
          required
        >
      </label>

      <button class="primary wide">
        Entrar
      </button>

      <p v-if="loginError" class="error">
        {{loginError}}
      </p>

    </form>

  </div>

</div>


<div v-else class="app">

  <aside class="sidebar">

    <div class="brand">
      <div class="brandMark">TI</div>
      <div>
        <strong>TI Agenda</strong>
        <small>Gestão de TI</small>
      </div>
    </div>

    <nav>

      <button
        :class="{active:view==='lista'}"
        @click="view='lista'"
      >
        <span>☷</span>
        Lista
      </button>

      <button
        :class="{active:view==='calendario'}"
        @click="view='calendario'"
      >
        <span>▦</span>
        Calendário
      </button>

    </nav>

    <div class="stats">

      <div>
        <b>{{today}}</b>
        <span>Hoje</span>
      </div>

      <div>
        <b>{{openCount}}</b>
        <span>Abertos</span>
      </div>

    </div>

    <div class="userBox">

      <div class="userIdentity">
        <div class="avatar">
          {{user.name?.charAt(0)||'U'}}
        </div>

        <div>
          <b>{{user.name}}</b>
          <span>{{user.role}}</span>
        </div>
      </div>

      <button @click="passModal=true">
        Alterar senha
      </button>

      <button
        v-if="isAdmin"
        @click="userModal=true"
      >
        Usuários
      </button>

      <button @click="logout">
        Sair
      </button>

    </div>

  </aside>


  <main>

    <header>

      <div>
        <div class="pageTitle">
          <h1>
            {{view==='lista'?'Agendamentos':'Calendário'}}
          </h1>
        </div>

        <p class="pageSubtitle">
          {{view==='lista'
            ? 'Gerencie os atendimentos e compromissos da equipe de TI'
            : 'Visualize os agendamentos por data'
          }}
        </p>
      </div>

      <button
        class="primary newButton"
        @click="openNew"
      >
        + Novo agendamento
      </button>

    </header>


    <div v-if="loading" class="loading">
      Carregando...
    </div>


    <div
      v-else-if="view==='lista'"
      class="content"
    >

      <div class="filters">

        <div class="searchBox">
          <span>⌕</span>

          <input
            v-model="search"
            placeholder="Buscar por chamado, título, solicitante..."
          >
        </div>

        <select v-model="status">
          <option>Todos</option>
          <option>Agendado</option>
          <option>Em andamento</option>
          <option>Concluído</option>
          <option>Cancelado</option>
        </select>

      </div>


      <div class="list">

        <div
          v-for="a in filtered"
          :key="a.id"
          class="item"
          @click="openEdit(a)"
        >

          <div class="ticket">
            {{a.ticket_number}}
          </div>

          <div class="info">

            <b>{{a.title}}</b>

            <span>
              {{a.requester}}
              <template v-if="a.department">
                · {{a.department}}
              </template>
              <template v-if="a.technician">
                · {{a.technician}}
              </template>
              <template v-else>
                · Sem técnico
              </template>
            </span>

          </div>

          <div class="meta">

            <span
              class="status"
              :class="a.status.replaceAll(' ','-')"
            >
              {{a.status}}
            </span>

            <span class="dateInfo">
              {{new Date(a.start).toLocaleDateString('pt-BR')}}
              <b>
                {{new Date(a.start).toLocaleTimeString('pt-BR',{
                  hour:'2-digit',
                  minute:'2-digit'
                })}}
              </b>
            </span>

          </div>

          <button
            v-if="isAdmin"
            class="danger"
            @click.stop="remove(a)"
          >
            Excluir
          </button>

        </div>

        <div
          v-if="!filtered.length"
          class="empty"
        >
          <div class="emptyIcon">✓</div>
          <b>Nenhum agendamento encontrado</b>
          <span>Crie um novo agendamento para começar.</span>
        </div>

      </div>

    </div>


    <div v-else class="cal">

      <div class="calHead">

        <button
          @click="month=new Date(month.getFullYear(),month.getMonth()-1,1)"
        >
          ‹
        </button>

        <h2>{{monthLabel}}</h2>

        <button
          @click="month=new Date(month.getFullYear(),month.getMonth()+1,1)"
        >
          ›
        </button>

      </div>

      <div class="grid seven">

        <div
          v-for="d in ['Dom','Seg','Ter','Qua','Qui','Sex','Sáb']"
          class="dow"
        >
          {{d}}
        </div>

        <div
          v-for="(d,i) in days"
          :key="i"
          class="day"
          :class="{
            empty:!d,
            today:d&&d.toDateString()===new Date().toDateString()
          }"
        >

          <template v-if="d">

            <span class="num">
              {{d.getDate()}}
            </span>

            <div
              v-for="a in appointments.filter(
                x=>new Date(x.start).toDateString()===d.toDateString()
              )"
              :key="a.id"
              class="event"
              @click="openEdit(a)"
            >
              {{a.title}}
            </div>

          </template>

        </div>

      </div>

    </div>

  </main>


  <!-- NOVO / EDITAR AGENDAMENTO -->

  <div
    v-if="modal"
    class="overlay"
    @click.self="modal=false"
  >

    <div class="modal">

      <div class="modalHead">

        <div>
          <h2>
            {{editId?'Editar agendamento':'Novo agendamento'}}
          </h2>

          <span>
            Preencha as informações do atendimento
          </span>
        </div>

        <button @click="modal=false">
          ✕
        </button>

      </div>


      <form @submit.prevent="save">

        <label>
          Título
          <input
            v-model="form.title"
            placeholder="Ex.: Instalação de computador"
            required
          >
        </label>


        <div class="grid two">

          <label>
            Tipo
            <select v-model="form.type">
              <option>Suporte técnico</option>
              <option>Manutenção</option>
              <option>Instalação</option>
              <option>Outro</option>
            </select>
          </label>

          <label>
            Solicitante
            <input
              v-model="form.requester"
              placeholder="Nome do solicitante"
              required
            >
          </label>

        </div>


        <div class="grid two">

          <label>
            Departamento
            <input
              v-model="form.department"
              placeholder="Ex.: RH, Financeiro, Comercial"
            >
          </label>

          <label>
            Local
            <input
              v-model="form.location"
              placeholder="Ex.: Sala 01, ETE, ETA"
            >
          </label>

        </div>


        <div class="grid two">

          <label>
            Técnico responsável
            <select v-model="form.technician">

              <option value="">
                Não definido
              </option>

              <option
                v-for="u in users"
                :key="u.id"
              >
                {{u.name}}
              </option>

            </select>
          </label>

          <label>
            Prioridade
            <select v-model="form.priority">
              <option>Baixa</option>
              <option>Normal</option>
              <option>Alta</option>
              <option>Urgente</option>
            </select>
          </label>

        </div>


        <div class="sectionTitle">
          Data e horário
        </div>


        <div class="grid three">

          <label>
            Data
            <input
              type="date"
              v-model="form.date"
              required
            >
          </label>

          <label>
            Início
            <input
              type="time"
              v-model="form.startTime"
              required
            >
          </label>

          <label>
            Fim
            <input
              type="time"
              v-model="form.endTime"
              required
            >
          </label>

        </div>


        <label>
          Status
          <select v-model="form.status">
            <option>Agendado</option>
            <option>Em andamento</option>
            <option>Concluído</option>
            <option>Cancelado</option>
          </select>
        </label>


        <label>
          Descrição
          <textarea
            v-model="form.description"
            placeholder="Descreva o atendimento ou serviço solicitado..."
          ></textarea>
        </label>


        <label>
          Observações
          <textarea
            v-model="form.notes"
            placeholder="Informações adicionais..."
          ></textarea>
        </label>


        <div class="modalActions">

          <button
            type="button"
            @click="modal=false"
          >
            Cancelar
          </button>

          <button class="primary">
            {{editId?'Salvar alterações':'Criar agendamento'}}
          </button>

        </div>

      </form>

    </div>

  </div>


  <!-- USUÁRIOS -->

  <div
    v-if="userModal"
    class="overlay"
    @click.self="userModal=false"
  >

    <div class="modal small">

      <div class="modalHead">
        <div>
          <h2>Usuários</h2>
          <span>Gerencie os usuários do sistema</span>
        </div>

        <button @click="userModal=false">
          ✕
        </button>
      </div>

      <div
        v-for="u in users"
        :key="u.id"
        class="user"
      >

        <span>
          <b>{{u.name}}</b>
          <small>{{u.username}} · {{u.role}}</small>
        </span>

        <button
          v-if="u.id!==user.id"
          @click="deactivate(u)"
        >
          Desativar
        </button>

      </div>

      <div class="sectionTitle">
        Novo usuário
      </div>

      <form @submit.prevent="addUser">

        <label>
          Nome completo
          <input
            v-model="newUser.name"
            placeholder="Nome completo"
            required
          >
        </label>

        <label>
          Usuário de acesso
          <input
            v-model="newUser.username"
            placeholder="Usuário"
            required
          >
        </label>

        <label>
          Senha
          <input
            v-model="newUser.password"
            type="password"
            placeholder="Mínimo 8 caracteres"
            minlength="8"
            required
          >
        </label>

        <label>
          Perfil
          <select v-model="newUser.role">
            <option>Técnico</option>
            <option>Solicitante</option>
            <option>Administrador</option>
          </select>
        </label>

        <button class="primary wide">
          Cadastrar usuário
        </button>

      </form>

    </div>

  </div>


  <!-- ALTERAR SENHA -->

  <div
    v-if="passModal"
    class="overlay"
    @click.self="passModal=false"
  >

    <div class="modal small">

      <div class="modalHead">

        <div>
          <h2>Alterar senha</h2>
          <span>Atualize sua senha de acesso</span>
        </div>

        <button @click="passModal=false">
          ✕
        </button>

      </div>

      <form @submit.prevent="changePassword">

        <label>
          Senha atual
          <input
            type="password"
            v-model="pw.current_password"
            required
          >
        </label>

        <label>
          Nova senha
          <input
            type="password"
            v-model="pw.new_password"
            minlength="8"
            required
          >
        </label>

        <button class="primary wide">
          Salvar nova senha
        </button>

      </form>

    </div>

  </div>

</div>

</template>
