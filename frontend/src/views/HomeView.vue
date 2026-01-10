<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '@/stores/game'

const router = useRouter()
const gameStore = useGameStore()

const nickname = ref('')
const inviteCode = ref('')
const isCreating = ref(false)
const isJoining = ref(false)

async function handleCreateGame() {
  if (!nickname.value.trim()) return

  isCreating.value = true
  try {
    await gameStore.createGame(nickname.value.trim())
    router.push('/lobby')
  } catch (e) {
    console.error('Failed to create game:', e)
  } finally {
    isCreating.value = false
  }
}

async function handleJoinGame() {
  if (!nickname.value.trim() || !inviteCode.value.trim()) return

  isJoining.value = true
  try {
    await gameStore.joinGame(inviteCode.value.trim(), nickname.value.trim())
    router.push('/lobby')
  } catch (e) {
    console.error('Failed to join game:', e)
  } finally {
    isJoining.value = false
  }
}
</script>

<template>
  <main class="home">
    <h1>Ransom Notes</h1>
    <p class="subtitle">A party game of questionable answers</p>

    <div class="game-forms">
      <div class="form-section">
        <label for="nickname">Your Nickname</label>
        <input
          id="nickname"
          v-model="nickname"
          type="text"
          placeholder="Enter your nickname"
          maxlength="20"
        />
      </div>

      <div v-if="gameStore.error" class="error-message">
        {{ gameStore.error }}
      </div>

      <div class="actions">
        <button
          @click="handleCreateGame"
          :disabled="!nickname.trim() || isCreating || isJoining"
          class="create-btn"
        >
          {{ isCreating ? 'Creating...' : 'Create New Game' }}
        </button>

        <div class="divider">
          <span>or</span>
        </div>

        <div class="join-section">
          <input
            v-model="inviteCode"
            type="text"
            placeholder="Enter invite code"
            maxlength="6"
            class="invite-input"
          />
          <button
            @click="handleJoinGame"
            :disabled="!nickname.trim() || !inviteCode.trim() || isCreating || isJoining"
            class="join-btn"
          >
            {{ isJoining ? 'Joining...' : 'Join Game' }}
          </button>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.home {
  max-width: 400px;
  margin: 0 auto;
  padding: 2rem;
  text-align: center;
}

h1 {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
}

.subtitle {
  opacity: 0.7;
  margin-bottom: 3rem;
}

.game-forms {
  background: var(--color-background-soft);
  padding: 2rem;
  border-radius: 8px;
}

.form-section {
  margin-bottom: 1.5rem;
}

.form-section label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.form-section input {
  width: 100%;
  padding: 0.75rem;
  font-size: 1rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: var(--color-background);
  color: var(--color-text);
}

.error-message {
  background: #ffebee;
  color: #c62828;
  padding: 0.75rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.create-btn {
  width: 100%;
  padding: 1rem;
  font-size: 1.1rem;
  background: #4caf50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.create-btn:hover:not(:disabled) {
  background: #43a047;
}

.create-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.divider {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--color-border);
}

.divider span {
  opacity: 0.7;
}

.join-section {
  display: flex;
  gap: 0.5rem;
}

.invite-input {
  flex: 1;
  padding: 0.75rem;
  font-size: 1rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: var(--color-background);
  color: var(--color-text);
  text-transform: uppercase;
}

.join-btn {
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
  background: var(--color-text);
  color: var(--color-background);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  white-space: nowrap;
}

.join-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.join-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
