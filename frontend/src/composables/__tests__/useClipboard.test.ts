import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { useClipboard } from '../useClipboard'

describe('useClipboard', () => {
  let originalClipboard: Clipboard | undefined
  let originalIsSecureContext: boolean

  beforeEach(() => {
    vi.useFakeTimers()
    originalClipboard = navigator.clipboard
    originalIsSecureContext = window.isSecureContext
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
    // Restore original values
    Object.defineProperty(navigator, 'clipboard', {
      value: originalClipboard,
      writable: true,
      configurable: true,
    })
    Object.defineProperty(window, 'isSecureContext', {
      value: originalIsSecureContext,
      writable: true,
      configurable: true,
    })
  })

  describe('initial state', () => {
    it('has correct initial values', () => {
      const { copied, error } = useClipboard()

      expect(copied.value).toBe(false)
      expect(error.value).toBeNull()
    })
  })

  describe('copyToClipboard with modern API', () => {
    it('copies text using clipboard API in secure context', async () => {
      const writeTextMock = vi.fn().mockResolvedValue(undefined)
      Object.defineProperty(navigator, 'clipboard', {
        value: { writeText: writeTextMock },
        writable: true,
        configurable: true,
      })
      Object.defineProperty(window, 'isSecureContext', {
        value: true,
        writable: true,
        configurable: true,
      })

      const { copied, copyToClipboard } = useClipboard()

      const result = await copyToClipboard('test text')

      expect(result).toBe(true)
      expect(writeTextMock).toHaveBeenCalledWith('test text')
      expect(copied.value).toBe(true)
    })

    it('resets copied state after timeout', async () => {
      const writeTextMock = vi.fn().mockResolvedValue(undefined)
      Object.defineProperty(navigator, 'clipboard', {
        value: { writeText: writeTextMock },
        writable: true,
        configurable: true,
      })
      Object.defineProperty(window, 'isSecureContext', {
        value: true,
        writable: true,
        configurable: true,
      })

      const { copied, copyToClipboard } = useClipboard()

      await copyToClipboard('test text')
      expect(copied.value).toBe(true)

      vi.advanceTimersByTime(2000)
      expect(copied.value).toBe(false)
    })
  })

  describe('copyToClipboard with fallback', () => {
    beforeEach(() => {
      // Simulate non-secure context
      Object.defineProperty(window, 'isSecureContext', {
        value: false,
        writable: true,
        configurable: true,
      })
    })

    it('uses execCommand fallback in non-secure context', async () => {
      const execCommandMock = vi.fn().mockReturnValue(true)
      document.execCommand = execCommandMock

      const { copied, copyToClipboard } = useClipboard()

      const result = await copyToClipboard('test text')

      expect(result).toBe(true)
      expect(execCommandMock).toHaveBeenCalledWith('copy')
      expect(copied.value).toBe(true)
    })

    it('returns false when execCommand fails', async () => {
      const execCommandMock = vi.fn().mockReturnValue(false)
      document.execCommand = execCommandMock

      const { copied, error, copyToClipboard } = useClipboard()

      const result = await copyToClipboard('test text')

      expect(result).toBe(false)
      expect(copied.value).toBe(false)
      expect(error.value).toBe('Copy failed')
    })

    it('handles execCommand throwing an error', async () => {
      document.execCommand = vi.fn().mockImplementation(() => {
        throw new Error('Not supported')
      })

      const { copied, error, copyToClipboard } = useClipboard()

      const result = await copyToClipboard('test text')

      expect(result).toBe(false)
      expect(copied.value).toBe(false)
      expect(error.value).toBe('Copy not supported')
    })
  })

  describe('clipboard API fallback', () => {
    it('falls back to execCommand when clipboard API fails', async () => {
      const writeTextMock = vi.fn().mockRejectedValue(new Error('Permission denied'))
      Object.defineProperty(navigator, 'clipboard', {
        value: { writeText: writeTextMock },
        writable: true,
        configurable: true,
      })
      Object.defineProperty(window, 'isSecureContext', {
        value: true,
        writable: true,
        configurable: true,
      })

      const execCommandMock = vi.fn().mockReturnValue(true)
      document.execCommand = execCommandMock

      const { copied, copyToClipboard } = useClipboard()

      const result = await copyToClipboard('test text')

      expect(result).toBe(true)
      expect(writeTextMock).toHaveBeenCalled()
      expect(execCommandMock).toHaveBeenCalledWith('copy')
      expect(copied.value).toBe(true)
    })
  })
})
