<script setup lang="ts">
import { RouterView } from 'vue-router'
import { onMounted } from 'vue'
import ThemeToggle from '@/components/ThemeToggle.vue'
import { useThemeStore } from '@/stores/theme'

// Initialize theme store on app load
const themeStore = useThemeStore()

onMounted(() => {
  // Ensure theme is applied on mount
  document.documentElement.setAttribute('data-theme', themeStore.theme)
})
</script>

<template>
  <div class="app-container">
    <header class="app-header">
      <ThemeToggle />
    </header>
    <RouterView />
  </div>
</template>

<style scoped>
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  position: fixed;
  top: 0.75rem;
  right: 0.75rem;
  z-index: 1000;
}

@media (min-width: 640px) {
  .app-header {
    top: 1rem;
    right: 1rem;
  }
}
</style>
