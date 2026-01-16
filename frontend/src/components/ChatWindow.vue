<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useGameStore } from '@/stores/game'
import type { ChatMessage } from '@/types/game'

const gameStore = useGameStore()

const isOpen = ref(false)
const messageInput = ref('')
const chatMessagesRef = ref<HTMLElement | null>(null)
const isSubmitting = ref(false)
const isSmallScreen = ref(false)

const chatMessages = computed(() => gameStore.chatMessages)
const unreadCount = computed(() => gameStore.unreadChatCount)
const hasUnread = computed(() => unreadCount.value > 0)

// Track screen size for responsive behavior
const SMALL_SCREEN_BREAKPOINT = 640

function updateScreenSize() {
  isSmallScreen.value = window.innerWidth < SMALL_SCREEN_BREAKPOINT
}

onMounted(() => {
  updateScreenSize()
  window.addEventListener('resize', updateScreenSize)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateScreenSize)
})

function toggleChat() {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    gameStore.markChatAsRead()
    scrollToBottom()
  }
}

async function sendMessage() {
  const text = messageInput.value.trim()
  if (!text || isSubmitting.value) return

  isSubmitting.value = true
  try {
    await gameStore.sendChatMessage(text)
    messageInput.value = ''
    scrollToBottom()
  } catch (e) {
    console.error('Failed to send message:', e)
  } finally {
    isSubmitting.value = false
  }
}

function handleKeyPress(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (chatMessagesRef.value) {
      chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight
    }
  })
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function isOwnMessage(message: ChatMessage): boolean {
  return message.player_id === gameStore.playerId
}

// Watch for new messages: auto-open on large screens, just notify on small screens
watch(
  () => chatMessages.value.length,
  (newLength, oldLength) => {
    if (newLength > oldLength) {
      // New message arrived
      if (!isOpen.value && !isSmallScreen.value) {
        // Auto-open on large screens
        isOpen.value = true
      }
    }
    if (isOpen.value) {
      scrollToBottom()
      gameStore.markChatAsRead()
    }
  },
)

// Mark as read when opening
watch(isOpen, (open) => {
  if (open) {
    gameStore.markChatAsRead()
  }
})
</script>

<template>
  <div class="chat-container" :class="{ collapsed: !isOpen }">
    <!-- Chat Header -->
    <button class="chat-header" @click="toggleChat">
      <span class="chat-title">Chat</span>
      <!-- Show count badge on large screens, dot on small screens -->
      <span v-if="!isOpen && hasUnread && !isSmallScreen" class="unread-badge">{{ unreadCount }}</span>
      <span v-if="!isOpen && hasUnread && isSmallScreen" class="unread-dot"></span>
      <span class="toggle-icon">{{ isOpen ? '−' : '+' }}</span>
    </button>

    <!-- Chat Body -->
    <div v-show="isOpen" class="chat-body">
      <div ref="chatMessagesRef" class="chat-messages">
        <div v-if="chatMessages.length === 0" class="no-messages">
          No messages yet. Say hello!
        </div>
        <div
          v-for="message in chatMessages"
          :key="message.id"
          class="chat-message"
          :class="{ own: isOwnMessage(message) }"
        >
          <div class="message-header">
            <span class="message-author">{{ message.nickname }}</span>
            <span class="message-time">{{ formatTime(message.timestamp) }}</span>
          </div>
          <div class="message-text">{{ message.text }}</div>
        </div>
      </div>

      <!-- Input Area -->
      <div class="chat-input-area">
        <input
          v-model="messageInput"
          type="text"
          placeholder="Type a message..."
          class="chat-input"
          @keypress="handleKeyPress"
          :disabled="isSubmitting"
          maxlength="500"
        />
        <button
          class="send-btn"
          @click="sendMessage"
          :disabled="!messageInput.trim() || isSubmitting"
        >
          Send
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-container {
  position: fixed;
  bottom: 70px;
  right: 1rem;
  width: 320px;
  max-height: 400px;
  background: var(--scrap-white);
  box-shadow: var(--shadow-paper-hover);
  display: flex;
  flex-direction: column;
  z-index: 200;
  transform: rotate(0.5deg);
  transition: max-height 0.3s ease;
}

.chat-container.collapsed {
  max-height: 44px;
}

@media (max-width: 640px) {
  .chat-container {
    width: calc(100% - 2rem);
    right: 1rem;
    left: 1rem;
    bottom: 60px;
  }
}

/* ==========================================================================
   CHAT HEADER
   ========================================================================== */

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background: var(--ink-black);
  color: var(--scrap-white);
  border: none;
  cursor: pointer;
  font-family: var(--font-typewriter);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-size: 0.85rem;
}

.chat-header:hover {
  background: var(--ink-charcoal);
}

.chat-title {
  flex: 1;
  text-align: left;
}

.unread-badge {
  background: var(--accent-red);
  color: white;
  font-size: 0.7rem;
  padding: 0.15rem 0.4rem;
  margin-right: 0.5rem;
  min-width: 18px;
  text-align: center;
}

.unread-dot {
  width: 10px;
  height: 10px;
  background: var(--accent-red);
  border-radius: 50%;
  margin-right: 0.5rem;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.2);
    opacity: 0.8;
  }
}

.toggle-icon {
  font-size: 1.1rem;
  font-weight: 400;
}

/* ==========================================================================
   CHAT BODY
   ========================================================================== */

.chat-body {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  max-height: 356px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-height: 200px;
  max-height: 280px;
  background: var(--scrap-newsprint);
}

.no-messages {
  font-family: var(--font-typewriter);
  color: var(--ink-grey);
  font-style: italic;
  text-align: center;
  padding: 2rem 1rem;
}

/* ==========================================================================
   CHAT MESSAGES
   ========================================================================== */

.chat-message {
  padding: 0.5rem 0.75rem;
  background: var(--scrap-white);
  box-shadow: 1px 1px 2px rgba(0, 0, 0, 0.1);
  max-width: 90%;
  transform: rotate(-0.3deg);
}

.chat-message.own {
  align-self: flex-end;
  background: var(--scrap-cream);
  transform: rotate(0.3deg);
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.message-author {
  font-family: var(--font-typewriter);
  font-weight: 700;
  font-size: 0.75rem;
  color: var(--ink-black);
  text-transform: uppercase;
}

.chat-message.own .message-author {
  color: var(--accent-red);
}

.message-time {
  font-family: var(--font-typewriter);
  font-size: 0.65rem;
  color: var(--ink-grey);
}

.message-text {
  font-family: var(--font-typewriter);
  font-size: 0.85rem;
  word-break: break-word;
  color: var(--ink-black);
}

/* ==========================================================================
   CHAT INPUT
   ========================================================================== */

.chat-input-area {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem;
  background: var(--scrap-white);
  border-top: 1px solid var(--ink-charcoal);
}

.chat-input {
  flex: 1;
  padding: 0.5rem 0.75rem;
  border: 2px solid var(--ink-charcoal);
  font-family: var(--font-typewriter);
  font-size: 0.85rem;
  background: var(--scrap-newsprint);
}

.chat-input:focus {
  outline: none;
  border-color: var(--ink-black);
}

.chat-input::placeholder {
  color: var(--ink-grey);
}

.send-btn {
  padding: 0.5rem 1rem;
  background: var(--accent-red);
  color: white;
  border: none;
  cursor: pointer;
  font-family: var(--font-typewriter);
  font-weight: 700;
  text-transform: uppercase;
  font-size: 0.75rem;
}

.send-btn:hover:not(:disabled) {
  background: var(--accent-red-dark);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
