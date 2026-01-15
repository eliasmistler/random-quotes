import { ref, watch } from 'vue'
import { defineStore } from 'pinia'

export type ThemeMode = 'system' | 'light' | 'dark'

const STORAGE_KEY = 'ransom-notes-theme'

export const useThemeStore = defineStore('theme', () => {
  const theme = ref<ThemeMode>(getStoredTheme())

  function getStoredTheme(): ThemeMode {
    if (typeof window === 'undefined') return 'system'
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'light' || stored === 'dark' || stored === 'system') {
      return stored
    }
    return 'system'
  }

  function setTheme(newTheme: ThemeMode) {
    theme.value = newTheme
    localStorage.setItem(STORAGE_KEY, newTheme)
    applyTheme(newTheme)
  }

  function applyTheme(mode: ThemeMode) {
    const root = document.documentElement
    root.setAttribute('data-theme', mode)
  }

  function cycleTheme() {
    const modes: ThemeMode[] = ['system', 'light', 'dark']
    const currentIndex = modes.indexOf(theme.value)
    const nextIndex = (currentIndex + 1) % modes.length
    setTheme(modes[nextIndex])
  }

  // Initialize theme on store creation
  if (typeof window !== 'undefined') {
    applyTheme(theme.value)
  }

  // Watch for changes
  watch(theme, (newTheme) => {
    applyTheme(newTheme)
  })

  return {
    theme,
    setTheme,
    cycleTheme,
  }
})
