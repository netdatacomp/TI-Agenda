import {defineConfig} from 'vite'
import vue from '@vitejs/plugin-vue'

// base './' faz os arquivos carregarem corretamente em https://usuario.github.io/TI-Agenda/
export default defineConfig({base:'./',plugins:[vue()]})
