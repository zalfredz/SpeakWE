// Pure end-of-answer detector (spec §6.3): an answer ends after `silenceMs` of quiet,
// counted only once the learner has actually started speaking.

export type SilenceEvent = 'none' | 'speech_started' | 'silence_end'

export interface SilenceOptions {
  threshold: number
  enabled: boolean      // false for the Part 2 long turn: silence never ends it
  startMs?: number      // continuous sound needed to count as speech
  silenceMs?: number
}

export function createSilenceDetector({ threshold, enabled, startMs = 300, silenceMs = 3000 }: SilenceOptions) {
  let aboveSince: number | null = null
  let belowSince: number | null = null
  let started = false
  let ended = false

  return {
    push(level: number, nowMs: number): SilenceEvent {
      const loud = level >= threshold
      if (!started) {
        if (!loud) { aboveSince = null; return 'none' }
        aboveSince ??= nowMs
        if (nowMs - aboveSince < startMs) return 'none'
        started = true
        return 'speech_started'
      }
      if (ended) return 'none'
      if (loud) { belowSince = null; return 'none' }
      belowSince ??= nowMs
      if (enabled && nowMs - belowSince >= silenceMs) { ended = true; return 'silence_end' }
      return 'none'
    },
  }
}

// Capped: if the learner talked during calibration, 3× their voice would make speech undetectable.
export const thresholdFromNoise = (noiseRms: number) => Math.min(0.05, Math.max(0.015, noiseRms * 3))
