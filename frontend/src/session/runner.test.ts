import { describe, expect, it } from 'vitest'
import type { Step } from '../api'
import { buildQueue, silenceEnabled } from './runner'

let i = 0
const step = (part: number, kind: Step['kind'], text = kind): Step =>
  ({ index: i++, part, kind, text, item_id: null, max_answer_s: kind === 'long_turn' ? 120 : 60, prep_s: kind === 'prep' ? 60 : null })

function fullPlan(): Step[] {
  i = 0
  return [step(1, 'instruction'), step(1, 'question'), step(2, 'instruction'), step(2, 'prep'), step(2, 'instruction'),
          step(2, 'long_turn'), step(2, 'question'), step(3, 'instruction'), step(3, 'question'), step(3, 'instruction')]
}
const types = (q: ReturnType<typeof buildQueue>) => q.map((a) => (a.type === 'complete' ? 'complete' : `${a.type}:${a.step.index}`))

describe('session runner', () => {
  it('orders a full test: questions are spoken then answered, prep comes before the long turn', () => {
    expect(types(buildQueue(fullPlan(), new Set()))).toEqual([
      'speak:0', 'speak:1', 'answer:1', 'speak:2', 'prep:3', 'speak:4', 'answer:5',
      'speak:6', 'answer:6', 'speak:7', 'speak:8', 'answer:8', 'speak:9', 'complete'])
  })

  it('does not read the cue card aloud for the long turn', () => {
    const q = buildQueue(fullPlan(), new Set())
    expect(q.some((a) => a.type === 'speak' && a.step.kind === 'long_turn')).toBe(false)
  })

  it('resumes after the last answered step', () => {
    expect(types(buildQueue(fullPlan(), new Set([1, 5])))).toEqual(['speak:6', 'answer:6', 'speak:7', 'speak:8', 'answer:8', 'speak:9', 'complete'])
  })

  it('a fully answered plan only completes', () => {
    expect(types(buildQueue(fullPlan(), new Set([1, 5, 6, 8])))).toEqual(['complete'])
  })

  it('silence ends answers except the Part 2 long turn', () => {
    const plan = fullPlan()
    expect(silenceEnabled(plan[1])).toBe(true)
    expect(silenceEnabled(plan[5])).toBe(false)
  })
})
