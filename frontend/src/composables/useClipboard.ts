import { ref } from 'vue'

export function useClipboard() {
  const copied = ref(false)
  const error = ref<string | null>(null)

  async function copyToClipboard(text: string): Promise<boolean> {
    error.value = null

    // Try the modern Clipboard API first
    if (navigator.clipboard && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(text)
        copied.value = true
        setTimeout(() => (copied.value = false), 2000)
        return true
      } catch {
        // Fall through to fallback
      }
    }

    // Fallback for non-secure contexts (HTTP)
    try {
      const textArea = document.createElement('textarea')
      textArea.value = text
      textArea.style.position = 'fixed'
      textArea.style.left = '-9999px'
      textArea.style.top = '-9999px'
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()

      const successful = document.execCommand('copy')
      document.body.removeChild(textArea)

      if (successful) {
        copied.value = true
        setTimeout(() => (copied.value = false), 2000)
        return true
      } else {
        error.value = 'Copy failed'
        return false
      }
    } catch {
      error.value = 'Copy not supported'
      return false
    }
  }

  return {
    copied,
    error,
    copyToClipboard,
  }
}
