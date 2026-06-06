// vite.config.js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Cấu hình xuất ra object chuẩn của Vite giúp biên dịch JSX (React)
export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173, // Ép cứng port chạy cố định cho bạn dễ quản lý
    }
})