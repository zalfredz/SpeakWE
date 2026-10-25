import { describe, expect, it } from 'vitest'
import type { Step } from '../api'
import { buildQueue, partOver, silenceEnabled, silenceMsFor } from './runner'

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

describe('Part 1 time limit', () => {
  it('stops asking once the next 25 s answer would pass 5 minutes', () => {
    expect(partOver(274, 9, 25, 300, 8)).toBe(false)
    expect(partOver(275, 9, 25, 300, 8)).toBe(true)
  })
  it('always asks at least the minimum number of questions', () => {
    expect(partOver(299, 7, 25, 300, 8)).toBe(false)
  })
})

describe('Part 3', () => {
  it('waits 4 s of silence instead of 3 (abstract questions need thinking time)', () => {
    i = 0
    expect([silenceMsFor(step(1, 'question')), silenceMsFor(step(3, 'question'))]).toEqual([3000, 4000])
  })
  it('stops asking once the next 45 s answer would pass 5 minutes, but asks at least 4', () => {
    expect(partOver(255, 4, 45, 300, 4)).toBe(true)
    expect(partOver(254, 4, 45, 300, 4)).toBe(false)
    expect(partOver(290, 3, 45, 300, 4)).toBe(false)
  })
})
