# Quick Reference Guide

## TypeScript Cheat Sheet

### Types
```typescript
// Primitives
const name: string = "Alice"
const age: number = 25
const isActive: boolean = true

// Arrays
const names: string[] = ["Alice", "Bob"]
const scores: Array<number> = [1, 2, 3]

// Objects (inline)
const player: { name: string; score: number } = { name: "Alice", score: 10 }

// Union types
let value: string | number = "hello"
value = 42  // Also valid

// Literal types
let phase: 'lobby' | 'playing' | 'done' = 'lobby'

// Optional
let optional?: string  // Can be string or undefined
```

### Interfaces
```typescript
interface Player {
  id: string
  name: string
  score?: number  // Optional property
}

// Using it
const player: Player = { id: "1", name: "Alice" }
```

### Type Aliases
```typescript
type ID = string
type Phase = 'lobby' | 'playing' | 'done'
type Callback = (arg: string) => void
```

### Functions
```typescript
// Named function
function add(a: number, b: number): number {
  return a + b
}

// Arrow function
const multiply = (a: number, b: number): number => a * b

// Async function
async function fetchData(): Promise<string> {
  return "data"
}

// Optional parameters
function greet(name: string, title?: string): string {
  return title ? `${title} ${name}` : name
}
```

### Generics
```typescript
// Generic function
function identity<T>(value: T): T {
  return value
}

// Generic interface
interface Response<T> {
  data: T
  status: number
}

// Using it
const response: Response<Player> = {
  data: { id: "1", name: "Alice" },
  status: 200
}
```

### Type Guards
```typescript
// typeof guard
if (typeof value === 'string') {
  console.log(value.toUpperCase())  // TypeScript knows it's a string
}

// Custom type guard
function isPlayer(obj: unknown): obj is Player {
  return typeof obj === 'object' && obj !== null && 'id' in obj
}
```

### Utility Types
```typescript
// Partial - makes all properties optional
type PartialPlayer = Partial<Player>

// Required - makes all properties required
type RequiredPlayer = Required<Player>

// Pick - select specific properties
type PlayerBasic = Pick<Player, 'id' | 'name'>

// Omit - exclude specific properties
type PlayerNoScore = Omit<Player, 'score'>
```

---

## Vue 3 Cheat Sheet

### Composition API Basics
```typescript
import { ref, computed, watch, onMounted } from 'vue'

// Reactive values
const count = ref(0)
const name = ref("Alice")

// Computed (derived state)
const doubled = computed(() => count.value * 2)

// Watch (react to changes)
watch(count, (newVal, oldVal) => {
  console.log(`Count changed from ${oldVal} to ${newVal}`)
})

// Lifecycle hooks
onMounted(() => {
  console.log('Component mounted')
})
```

### Template Syntax
```vue
<template>
  <!-- Interpolation -->
  {{ message }}

  <!-- Attribute binding -->
  <div :id="dynamicId" :class="{ active: isActive }">

  <!-- Event handling -->
  <button @click="handleClick">Click</button>
  <input @input="handleInput" @keyup.enter="submit">

  <!-- Two-way binding -->
  <input v-model="message">

  <!-- Conditional rendering -->
  <div v-if="isVisible">Visible</div>
  <div v-else-if="isPartial">Partial</div>
  <div v-else>Hidden</div>

  <!-- Show/hide (with CSS) -->
  <div v-show="isVisible">Toggle visibility</div>

  <!-- List rendering -->
  <div v-for="item in items" :key="item.id">
    {{ item.name }}
  </div>

  <!-- List with index -->
  <div v-for="(item, index) in items" :key="item.id">
    {{ index }}: {{ item.name }}
  </div>
</template>
```

### Component Communication

#### Props (Parent → Child)
```vue
<!-- Child component -->
<script setup lang="ts">
const props = defineProps<{
  message: string
  count?: number
}>()

// Or with defaults
const props = withDefaults(defineProps<{
  message: string
  count?: number
}>(), {
  count: 0
})
</script>

<!-- Parent component -->
<template>
  <ChildComponent message="Hello" :count="5" />
</template>
```

#### Emits (Child → Parent)
```vue
<!-- Child component -->
<script setup lang="ts">
const emit = defineEmits<{
  update: [value: string]
  delete: []
}>()

function handleClick() {
  emit('update', 'new value')
}
</script>

<!-- Parent component -->
<template>
  <ChildComponent
    @update="handleUpdate"
    @delete="handleDelete"
  />
</template>
```

### Reactivity

#### ref vs reactive
```typescript
// ref - for any value
const count = ref(0)
count.value++  // Need .value in script

const user = ref({ name: "Alice" })
user.value.name = "Bob"  // Still need .value

// reactive - for objects
const state = reactive({ count: 0 })
state.count++  // No .value needed

// In templates, .value is automatic:
<template>{{ count }}</template>  <!-- No .value needed -->
```

#### Computed vs Methods
```typescript
// Computed (cached, only recalculates when dependencies change)
const doubled = computed(() => count.value * 2)

// Method (runs every time it's called)
function getDoubled() {
  return count.value * 2
}

// Use computed for derived state, methods for actions
```

### Lifecycle Hooks
```typescript
import {
  onBeforeMount,
  onMounted,
  onBeforeUpdate,
  onUpdated,
  onBeforeUnmount,
  onUnmounted
} from 'vue'

onBeforeMount(() => console.log('Before mount'))
onMounted(() => console.log('Mounted'))
onBeforeUpdate(() => console.log('Before update'))
onUpdated(() => console.log('Updated'))
onBeforeUnmount(() => console.log('Before unmount'))
onUnmounted(() => console.log('Unmounted'))
```

---

## Pinia Cheat Sheet

### Store Definition
```typescript
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export const useGameStore = defineStore('game', () => {
  // State
  const count = ref(0)
  const name = ref("Alice")

  // Getters (computed)
  const doubled = computed(() => count.value * 2)

  // Actions
  function increment() {
    count.value++
  }

  async function fetchData() {
    const data = await api.fetch()
    name.value = data.name
  }

  // Return what's exposed
  return {
    count,
    name,
    doubled,
    increment,
    fetchData
  }
})
```

### Using Stores
```typescript
import { useGameStore } from '@/stores/game'

// In component
const gameStore = useGameStore()

// Access state
console.log(gameStore.count)

// Access getters
console.log(gameStore.doubled)

// Call actions
gameStore.increment()
await gameStore.fetchData()

// Destructure (loses reactivity)
const { count, name } = gameStore  // ❌ Not reactive

// Use storeToRefs for reactive destructuring
import { storeToRefs } from 'pinia'
const { count, name } = storeToRefs(gameStore)  // ✅ Reactive
```

---

## Vue Router Cheat Sheet

### Route Definition
```typescript
const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView
    },
    {
      path: '/game/:id',  // Dynamic parameter
      name: 'game',
      component: GameView,
      props: true  // Pass params as props
    },
    {
      path: '/about',
      name: 'about',
      component: () => import('./views/About.vue')  // Lazy load
    }
  ]
})
```

### Navigation
```typescript
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

// Programmatic navigation
router.push('/about')
router.push({ name: 'game', params: { id: '123' } })
router.push({ path: '/game', query: { player: 'Alice' } })
router.back()
router.forward()

// Access current route
console.log(route.path)      // '/game/123'
console.log(route.params.id) // '123'
console.log(route.query)     // { player: 'Alice' }
```

### Route Guards
```typescript
// Global guard
router.beforeEach((to, from, next) => {
  if (to.meta.requiresAuth && !isAuthenticated) {
    next({ name: 'login' })
  } else {
    next()
  }
})

// Per-route guard
{
  path: '/admin',
  component: AdminView,
  beforeEnter: (to, from, next) => {
    if (isAdmin) {
      next()
    } else {
      next('/')
    }
  }
}
```

---

## Common Patterns

### Async Data Loading
```typescript
const data = ref(null)
const isLoading = ref(false)
const error = ref(null)

async function loadData() {
  isLoading.value = true
  error.value = null

  try {
    const response = await fetch('/api/data')
    data.value = await response.json()
  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  loadData()
})
```

### Form Handling
```vue
<script setup lang="ts">
const form = ref({
  name: '',
  email: '',
  age: 0
})

const errors = ref<Record<string, string>>({})

function validate() {
  errors.value = {}

  if (!form.value.name) {
    errors.value.name = 'Name is required'
  }

  if (!form.value.email.includes('@')) {
    errors.value.email = 'Invalid email'
  }

  return Object.keys(errors.value).length === 0
}

async function submit() {
  if (!validate()) return

  try {
    await api.submit(form.value)
    // Success
  } catch (e) {
    // Error
  }
}
</script>

<template>
  <form @submit.prevent="submit">
    <input v-model="form.name" />
    <span v-if="errors.name">{{ errors.name }}</span>

    <input v-model="form.email" type="email" />
    <span v-if="errors.email">{{ errors.email }}</span>

    <button type="submit">Submit</button>
  </form>
</template>
```

### Debounced Search
```typescript
import { ref, watch } from 'vue'

const searchQuery = ref('')
const searchResults = ref([])
let timeout: number | null = null

watch(searchQuery, (newQuery) => {
  // Clear previous timeout
  if (timeout) clearTimeout(timeout)

  // Set new timeout
  timeout = window.setTimeout(async () => {
    if (newQuery) {
      searchResults.value = await api.search(newQuery)
    } else {
      searchResults.value = []
    }
  }, 300)  // 300ms debounce
})
```

### Polling
```typescript
const data = ref(null)
let intervalId: number | null = null

function startPolling() {
  intervalId = window.setInterval(async () => {
    data.value = await api.fetch()
  }, 5000)  // Every 5 seconds
}

function stopPolling() {
  if (intervalId) {
    clearInterval(intervalId)
    intervalId = null
  }
}

onMounted(() => startPolling())
onUnmounted(() => stopPolling())
```

---

## Debugging Tips

### Vue DevTools
1. Install browser extension
2. Open DevTools → Vue tab
3. Inspect components, state, events

### TypeScript Errors
```typescript
// Hover over error in IDE to see details
// Cmd/Ctrl + Click on type to see definition
// Use type assertions when you know better:
const element = document.getElementById('app') as HTMLDivElement
```

### Console Logging
```typescript
// In computed/watch
const doubled = computed(() => {
  console.log('Computing doubled')
  return count.value * 2
})

watch(count, (newVal) => {
  console.log('Count changed:', newVal)
})
```

### Common Issues

**Forgot .value:**
```typescript
const count = ref(0)
count++  // ❌ Wrong
count.value++  // ✅ Correct
```

**Lost reactivity:**
```typescript
const { count } = useGameStore()  // ❌ Not reactive
const gameStore = useGameStore()  // ✅ Keep reference
```

**Mutation vs replacement:**
```typescript
// Mutation (reactive)
players.value.push(newPlayer)  // ✅

// Replacement (also reactive)
players.value = [...players.value, newPlayer]  // ✅
```

---

## Keyboard Shortcuts (VSCode/PyCharm)

- `Cmd/Ctrl + Click` - Go to definition
- `F12` - Go to definition
- `Shift + F12` - Find all references
- `F2` - Rename symbol
- `Cmd/Ctrl + .` - Quick fix
- `Cmd/Ctrl + Space` - Trigger autocomplete
