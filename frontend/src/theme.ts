// Light / dark theme: follows the device until the learner picks one, then remembers the pick.
export type Theme = 'light' | 'dark'

const KEY = 'speakwe-theme'
const THEME_COLOR: Record<Theme, string> = { light: '#FBF8F4', dark: '#17141F' }

export function resolveTheme(saved: string | null, prefersDark: boolean): Theme {
  return saved === 'light' || saved === 'dark' ? saved : prefersDark ? 'dark' : 'light'
}

function readSaved(): string | null {
  try { return localStorage.getItem(KEY) } catch { return null }   // private mode / blocked storage
}

export function currentTheme(): Theme {
  return resolveTheme(readSaved(), matchMedia('(prefers-color-scheme: dark)').matches)
}

export function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', THEME_COLOR[theme])
}

export function saveTheme(theme: Theme) {
  try { localStorage.setItem(KEY, theme) } catch { /* the choice just won't persist */ }
  applyTheme(theme)
}
