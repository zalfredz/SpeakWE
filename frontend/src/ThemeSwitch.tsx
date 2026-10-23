import { useState } from 'react'
import { currentTheme, saveTheme, type Theme } from './theme'

const Sun = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" aria-hidden="true">
    <circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
  </svg>
)
const Moon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" />
  </svg>
)

// role="switch": on = night mode. The visible label names the current mode.
export default function ThemeSwitch() {
  const [theme, setTheme] = useState<Theme>(currentTheme)
  const dark = theme === 'dark'
  const toggle = () => { const next: Theme = dark ? 'light' : 'dark'; saveTheme(next); setTheme(next) }
  return (
    <button type="button" role="switch" aria-checked={dark} aria-label="Mode malam" className="theme-switch" onClick={toggle}>
      <span className="track"><span className="thumb">{dark ? <Moon /> : <Sun />}</span></span>
    </button>
  )
}
