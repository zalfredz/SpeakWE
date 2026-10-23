import { describe, expect, it } from 'vitest'
import { createSilenceDetector, thresholdFromNoise } from './silence'

const LOUD = 0.2, QUIET = 0.001

// feed `level` every 50 ms from `from` to `to` ms; return the events that fired
function feed(d: ReturnType<typeof createSilenceDetector>, level: number, from: number, to: number) {
  const events: string[] = []
  for (let t = from; t <= to; t += 50) {
    const e = d.push(level, t)
    if (e !== 'none') events.push(`${e}@${t}`)
  }
  return events
}

describe('silence detector', () => {
  it('never ends on initial silence before the user speaks', () => {
    const d = createSilenceDetector({ threshold: 0.02, enabled: true })
    expect(feed(d, QUIET, 0, 20000)).toEqual([])
  })

  it('a 2.9 s thinking pause does not end the answer; 3.0 s does', () => {
    const d = createSilenceDetector({ threshold: 0.02, enabled: true })
    expect(feed(d, LOUD, 0, 1000)).toEqual(['speech_started@300'])
    expect(feed(d, QUIET, 1050, 3900)).toEqual([])         // 2.85 s of quiet
    expect(feed(d, LOUD, 3950, 5000)).toEqual([])          // speaking again resets the clock
    expect(feed(d, QUIET, 5050, 8100)).toEqual(['silence_end@8050'])
  })

  it('a blip shorter than 300 ms is not speech', () => {
    const d = createSilenceDetector({ threshold: 0.02, enabled: true })
    expect(feed(d, LOUD, 0, 200)).toEqual([])
    expect(feed(d, QUIET, 250, 6000)).toEqual([])
  })

  it('emits silence_end only once', () => {
    const d = createSilenceDetector({ threshold: 0.02, enabled: true })
    feed(d, LOUD, 0, 500)
    expect(feed(d, QUIET, 550, 12000)).toHaveLength(1)
  })

  it('disabled (Part 2 long turn) never ends on silence', () => {
    const d = createSilenceDetector({ threshold: 0.02, enabled: false })
    expect(feed(d, LOUD, 0, 1000)).toEqual(['speech_started@300'])
    expect(feed(d, QUIET, 1050, 30000)).toEqual([])
  })

  it('threshold is capped so speech during calibration cannot make speech undetectable', () => {
    expect(thresholdFromNoise(0.1)).toBe(0.05)
  })

  it('threshold is three times the noise floor, never below 0.015', () => {
    expect(thresholdFromNoise(0.001)).toBe(0.015)
    expect(thresholdFromNoise(0.01)).toBeCloseTo(0.03)
  })
})
