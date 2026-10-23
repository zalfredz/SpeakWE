import { ApiError } from '../api'

// Network errors and 5xx are transient; any 4xx is the server rejecting the request, so retrying won't help.
const transient = (e: unknown) => !(e instanceof ApiError) || e.status >= 500

// Retry once automatically, then keep retrying each time the learner asks (waitForUser resolves).
// Used for begin / upload / complete so a network blip never loses an answer or a finished session.
export async function withRetry<T>(fn: () => Promise<T>, waitForUser: () => Promise<void>): Promise<T> {
  for (let attempt = 0; ; attempt++) {
    try {
      return await fn()
    } catch (e) {
      if (!transient(e)) throw e
      if (attempt > 0) await waitForUser()
    }
  }
}

// The answer loop checks the limit every 50 ms; a throttled tab or sleeping device can overshoot,
// and the server rejects anything past max + 2 s.
export const clampDuration = (durationMs: number, maxAnswerS: number) => Math.min(durationMs, maxAnswerS * 1000)

export function formatDuration(ms: number) {
  const s = Math.round(ms / 1000)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}
