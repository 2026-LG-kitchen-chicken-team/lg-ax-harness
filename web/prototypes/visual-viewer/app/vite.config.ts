import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { jinhaReport } from './scripts/jinha-report.mjs'

// One JS chunk and one CSS file; scripts/publish.mjs inlines both into ../index.html.
export default defineConfig({
  plugins: [react(), tailwindcss(), jinhaReport()],
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    cssCodeSplit: false,
    assetsInlineLimit: 100_000_000,
    modulePreload: false,
    rollupOptions: { output: { inlineDynamicImports: true } },
  },
})
