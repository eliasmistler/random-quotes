<script setup lang="ts">
import { useThemeStore, type ThemeMode } from '@/stores/theme'

const themeStore = useThemeStore()

function selectTheme(mode: ThemeMode) {
  themeStore.setTheme(mode)
}
</script>

<template>
  <div class="theme-toggle">
    <button
      class="theme-btn"
      :class="{ active: themeStore.theme === 'system' }"
      @click="selectTheme('system')"
      title="Use system theme"
    >
      <span class="icon">◐</span>
      <span class="label">Auto</span>
    </button>
    <button
      class="theme-btn"
      :class="{ active: themeStore.theme === 'light' }"
      @click="selectTheme('light')"
      title="Light theme"
    >
      <span class="icon">☀</span>
      <span class="label">Light</span>
    </button>
    <button
      class="theme-btn"
      :class="{ active: themeStore.theme === 'dark' }"
      @click="selectTheme('dark')"
      title="Dark theme"
    >
      <span class="icon">☾</span>
      <span class="label">Dark</span>
    </button>
  </div>
</template>

<style scoped>
.theme-toggle {
  display: flex;
  gap: 0.25rem;
  padding: 0.25rem;
  background: var(--color-background-soft);
  border-radius: 6px;
  border: 1px solid var(--color-border);
}

.theme-btn {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.4rem 0.6rem;
  background: transparent;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: var(--color-text);
  opacity: 0.6;
  transition: all 0.2s ease;
  font-size: 0.8rem;
}

.theme-btn:hover {
  opacity: 0.9;
  background: var(--color-background-mute);
}

.theme-btn.active {
  opacity: 1;
  background: var(--color-background);
  box-shadow: 0 1px 3px var(--tile-shadow);
}

.icon {
  font-size: 1rem;
  line-height: 1;
}

.label {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

/* Hide labels on small screens */
@media (max-width: 480px) {
  .label {
    display: none;
  }

  .theme-btn {
    padding: 0.5rem;
  }

  .icon {
    font-size: 1.1rem;
  }
}
</style>
