// Types and helpers for the evaluator report (prompt doc ielts-eval-v2 §4 schema).
export type CriterionKey = 'fc' | 'lr' | 'gra' | 'p'

export interface Evidence {
  type: 'strength' | 'limitation'
  turn_id: string
  segment_id: string
  start_ms: number
  end_ms: number
  quote: string
  observation_id: string
  heard_as?: string
}

export interface Criterion {
  band: number | null
  descriptor_fit_id?: string
  evidence: Evidence[]
  why_not_higher_id?: string
  why_not_lower_id?: string
}

export interface Report {
  status?: string
  criteria: Record<CriterionKey, Criterion>
  feedback?: {
    summary_id: string
    priorities: { criterion: CriterionKey; title_id: string; explanation_id: string; evidence_segment_ids: string[]; drill_id: string }[]
    upgrade_opportunities: { segment_id: string; original: string; kind: string; intended_meaning_en: string; grammar_fix?: string; note_id?: string }[]
  }
}

const LABELS: [CriterionKey, string][] = [
  ['fc', 'Fluency & Coherence'], ['lr', 'Lexical Resource'], ['gra', 'Grammatical Range & Accuracy'], ['p', 'Pronunciation'],
]

export const formatMs = (ms: number) => {
  const s = Math.floor(ms / 1000)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

export const bandsFromReport = (report: Pick<Report, 'criteria'>) =>
  LABELS.map(([key, label]) => ({ key, label, band: report.criteria[key]?.band ?? null }))

const norm = (id: string) => id.replace(/^seg /, '')

// The evidence a priority points at: prefer a limitation of that criterion in one of the cited segments.
export function evidenceFor(report: Pick<Report, 'criteria'>, criterion: CriterionKey, segmentIds: string[]) {
  const ids = new Set(segmentIds.map(norm))
  const all = Object.values(report.criteria).flatMap((c) => c.evidence ?? [])
  const pick = (report.criteria[criterion]?.evidence ?? []).find((e) => e.type === 'limitation' && ids.has(norm(e.segment_id)))
    ?? all.find((e) => ids.has(norm(e.segment_id)))
  // the segment id (t{turn}-{n}) is validated on the server; turn_id from the model is not trusted for playback
  return pick ? { ...pick, turnIndex: Number(norm(pick.segment_id).split('-')[0].replace(/^t/, '')) } : null
}

// 1-based position among the answer steps (questions and the Part 2 long turn)
export const answerNumber = (plan: { index: number; kind: string }[], stepIndex: number) =>
  plan.filter((s) => s.kind === 'question' || s.kind === 'long_turn').findIndex((s) => s.index === stepIndex) + 1
