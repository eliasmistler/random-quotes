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
  max-width: 480px;
  margin: 0 auto;
  padding: 1rem;
  text-align: center;
  animation: fadeInUp 0.4s var(--animation-smooth);
}

@media (min-width: 640px) {
  .home {
    padding: 2rem;
    max-width: 520px;
  }
}

@media (min-width: 1024px) {
  .home {
    padding: 3rem 2rem;
    max-width: 560px;
  }
}

h1 {
  font-size: clamp(1.75rem, 5vw, 2.75rem);
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.subtitle {
  font-family: var(--font-mono);
  opacity: 0.7;
  margin-bottom: 2rem;
  font-style: italic;
  font-size: clamp(0.9rem, 2.5vw, 1rem);
}

@media (min-width: 640px) {
  .subtitle {
    margin-bottom: 3rem;
  }
}

.game-forms {
  background: var(--color-background-soft);
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

@media (min-width: 640px) {
  .game-forms {
    padding: 2rem;
  }
}

@media (min-width: 1024px) {
  .game-forms {
    padding: 2.5rem;
  }
}

.form-section {
  margin-bottom: 1.5rem;
}

.form-section label {
  display: block;
  margin-bottom: 0.5rem;
  text-align: left;
  text-transform: uppercase;
  font-size: 0.85rem;
  letter-spacing: 0.05em;
}

.form-section input {
  width: 100%;
  padding: 1rem;
  font-size: 1rem;
  border: 2px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-background);
  color: var(--color-text);
  transition: border-color var(--transition-normal), box-shadow var(--transition-normal);
}

.form-section input:focus {
  border-color: #4caf50;
  box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.2);
}

.error-message {
  font-family: var(--font-mono);
  background: #ffebee;
  color: #c62828;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-size: 0.9rem;
  animation: fadeInUp 0.3s var(--animation-smooth);
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
  background: linear-gradient(135deg, #4caf50 0%, #43a047 100%);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.create-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #43a047 0%, #388e3c 100%);
  box-shadow: 0 6px 16px rgba(76, 175, 80, 0.4);
  transform: translateY(-1px);
}

.create-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}

.divider {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin: 0.5rem 0;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--color-border);
}

.divider span {
  font-family: var(--font-mono);
  opacity: 0.6;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.join-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

@media (min-width: 480px) {
  .join-section {
    flex-direction: row;
    gap: 0.5rem;
  }
}

.invite-input {
  flex: 1;
  padding: 1rem;
  font-size: 1.1rem;
  border: 2px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-background);
  color: var(--color-text);
  text-transform: uppercase;
  text-align: center;
  letter-spacing: 0.2em;
  transition: border-color var(--transition-normal), box-shadow var(--transition-normal);
}

.invite-input:focus {
  border-color: var(--color-text);
  box-shadow: 0 0 0 3px rgba(128, 128, 128, 0.2);
}

.invite-input::placeholder {
  letter-spacing: normal;
  font-weight: normal;
  text-transform: none;
}

.join-btn {
  padding: 1rem 1.5rem;
  font-size: 1rem;
  background: var(--color-text);
  color: var(--color-background);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  white-space: nowrap;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

@media (max-width: 479px) {
  .join-btn {
    width: 100%;
  }
}

.join-btn:hover:not(:disabled) {
  opacity: 0.85;
  transform: translateY(-1px);
}

.join-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
