import { describe, expect, it } from 'vitest'
import { answerNumber, bandsFromReport, evidenceFor, formatMs, type Report } from './report'

const report: Pick<Report, 'criteria'> = {
  criteria: {
    fc: { band: 6, evidence: [{ type: 'strength', turn_id: 't1', segment_id: 't1-1', start_ms: 0, end_ms: 4000, quote: 'good', observation_id: 'o' },
                              { type: 'limitation', turn_id: 't3', segment_id: 't3-2', start_ms: 65000, end_ms: 70000, quote: 'I- I go', observation_id: 'o' }] },
    lr: { band: 7, evidence: [] }, gra: { band: null, evidence: [] }, p: { band: 6, evidence: [] },
  },
}

describe('report helpers', () => {
  it('formats milliseconds as m:ss', () => {
    expect(formatMs(65000)).toBe('1:05')
    expect(formatMs(0)).toBe('0:00')
  })

  it('lists the four criteria in IELTS order with labels and nullable bands', () => {
    expect(bandsFromReport(report)).toEqual([
      { key: 'fc', label: 'Fluency & Coherence', band: 6 },
      { key: 'lr', label: 'Lexical Resource', band: 7 },
      { key: 'gra', label: 'Grammatical Range & Accuracy', band: null },
      { key: 'p', label: 'Pronunciation', band: 6 },
    ])
  })

  it('picks the limitation evidence for a priority, with the turn index for audio playback', () => {
    expect(evidenceFor(report, 'fc', ['t3-2'])).toMatchObject({ quote: 'I- I go', turnIndex: 3, start_ms: 65000 })
    expect(evidenceFor(report, 'lr', ['t9-9'])).toBeNull()
  })
})

describe('report robustness', () => {
  it('takes the turn index from the segment id, so a missing turn_id cannot crash the page', () => {
    const r = { criteria: { ...report.criteria, fc: { band: 6, evidence: [{ type: 'limitation', segment_id: 't5-1', start_ms: 1000, end_ms: 2000, quote: 'x', observation_id: 'o' } as never] } } }
    expect(evidenceFor(r, 'fc', ['t5-1'])).toMatchObject({ turnIndex: 5 })
  })

  it('numbers answers by their position among answer steps, not by plan index', () => {
    const plan = [{ index: 0, kind: 'instruction' }, { index: 1, kind: 'question' }, { index: 2, kind: 'question' },
                  { index: 3, kind: 'instruction' }, { index: 4, kind: 'long_turn' }]
    expect(answerNumber(plan, 4)).toBe(3)
    expect(answerNumber(plan, 1)).toBe(1)
  })
})
