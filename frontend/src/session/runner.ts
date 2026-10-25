// Pure session runner: turns the server plan into the ordered actions the practice room performs.
import type { Step } from '../api'

export type Action =
  | { type: 'speak'; step: Step }     // Mimo says step.text, caption visible
  | { type: 'prep'; step: Step }      // Part 2 preparation screen
  | { type: 'answer'; step: Step }    // record the learner's answer
  | { type: 'complete' }

const ANSWER_KINDS: Step['kind'][] = ['question', 'long_turn']

export const isAnswerStep = (s: Step) => ANSWER_KINDS.includes(s.kind)

// Part 2's long turn must never be cut short by a thinking pause (spec §6.3).
export const silenceEnabled = (s: Step) => s.kind !== 'long_turn'

export function buildQueue(plan: Step[], answered: Set<number>): Action[] {
  const answerSteps = plan.filter(isAnswerStep)
  if (answerSteps.length && answerSteps.every((s) => answered.has(s.index))) return [{ type: 'complete' }]
  const lastAnswered = Math.max(-1, ...answered)
  const actions: Action[] = []
  for (const step of plan) {
    if (step.index <= lastAnswered) continue
    if (step.kind === 'instruction') actions.push({ type: 'speak', step })
    else if (step.kind === 'question') actions.push({ type: 'speak', step }, { type: 'answer', step })
    else if (step.kind === 'prep') actions.push({ type: 'prep', step })
    else actions.push({ type: 'answer', step })   // long_turn: the card is on screen, not read aloud
  }
  actions.push({ type: 'complete' })
  return actions
}

// Part 3 questions are abstract: allow a longer thinking pause before the answer counts as finished.
export const silenceMsFor = (s: Step) => (s.part === 3 ? 4000 : 3000)

// Mimo starts looking sleepy this long before a time-boxed part's limit, a gentle "time is nearly up".
export const SLEEPY_BEFORE_S = 30

// Part 2 long turn: ending before a minute gets one "tell me more"; a wrap-up gesture shows near the 2-minute stop.
export const LONG_TURN_MIN_S = 60
export const WRAP_UP_BEFORE_S = 15
export const TELL_ME_MORE = 'Can you tell me a little more?'

// Ask no further question in a time-boxed part once its answer could run past the limit (mirrors backend flow.time_skipped).
export function partOver(elapsedS: number, answered: number, nextMaxAnswerS: number, limitS: number, minQuestions: number) {
  return answered >= minQuestions && elapsedS >= limitS - nextMaxAnswerS
}
