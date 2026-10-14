import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// One JS chunk and one CSS file; scripts/publish.mjs inlines both into ../index.html.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    cssCodeSplit: false,
    assetsInlineLimit: 100_000_000,
    modulePreload: false,
    chunkSizeWarningLimit: 4000,
    rollupOptions: { output: { codeSplitting: false } },
  },
})
