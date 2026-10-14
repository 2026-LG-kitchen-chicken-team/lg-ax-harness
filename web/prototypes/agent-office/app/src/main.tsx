import { createRoot } from 'react-dom/client'
import './index.css'
import { App } from './App'

// No StrictMode: its double mount drops the first drei <Html> label (the main desk's name tag).
createRoot(document.getElementById('root') as HTMLElement).render(<App />)
