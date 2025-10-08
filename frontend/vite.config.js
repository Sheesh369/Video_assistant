// import { defineConfig } from 'vite'
// import react from '@vitejs/plugin-react'

// // https://vite.dev/config/
// export default defineConfig({
//   plugins: [react()],
// })
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/heygen': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/get-token': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/send-prompt': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
