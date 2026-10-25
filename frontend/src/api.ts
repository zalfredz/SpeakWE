// Typed client for the Django IELTS API (backend/ielts/views.py).

export type Mode = 'part1' | 'part2' | 'part3' | 'full'
export type StepKind = 'instruction' | 'question' | 'prep' | 'long_turn'

export interface Step {
  index: number
  part: number
  kind: StepKind
  text: string
  item_id: string | null
  max_answer_s: number | null
  prep_s: number | null
}

export interface Turn {
  index: number
  begun_at: string | null
  answered_at: string | null
  duration_ms: number | null
  mime: string
}

export interface Session {
  id: string
  mode: Mode
  status: string
  plan: Step[]
  turns: Turn[]
  created_at: string
  started_at: string | null
  completed_at: string | null
  part_limits: Record<string, { limit_s: number; min_questions: number }>   // time-boxed parts (1 and 3), keyed by part
}

export interface CompleteResult {
  session: Session
  checkin: { local_date: string; created: boolean } | null
  assessment: { version: string; status: string }
}

export interface Checkins {
  dates: string[]
  streak: number
  today: string
}

export class ApiError extends Error {
  constructor(public status: number, public code: string, detail: string) {
    super(detail || code)
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new ApiError(res.status, body.error ?? 'http_error', body.detail ?? '')
  return body as T
}

const postJson = <T>(url: string, body: unknown = {}) =>
  request<T>(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export const createSession = (mode: Mode, trainingConsent = false) =>
  postJson<Session>('/api/sessions', { mode, training_consent: trainingConsent })
export const getSession = (id: string) => request<Session>(`/api/sessions/${id}`)
export const setState = (id: string, to: string) => postJson<Session>(`/api/sessions/${id}/state`, { to })
export const beginTurn = (id: string, index: number) => postJson<{ index: number; begun_at: string }>(`/api/sessions/${id}/turns/${index}/begin`)
export const completeSession = (id: string) => postJson<CompleteResult>(`/api/sessions/${id}/complete`)
export const getCheckins = () => request<Checkins>('/api/checkins')

const EXT: Record<string, string> = { 'audio/webm': 'webm', 'audio/mp4': 'm4a', 'audio/ogg': 'ogg', 'audio/mpeg': 'mp3', 'audio/wav': 'wav' }

export function uploadAnswer(id: string, index: number, blob: Blob, durationMs: number) {
  const form = new FormData()
  form.append('audio', blob, `answer.${EXT[blob.type.split(';')[0]] ?? 'webm'}`)
  form.append('duration_ms', String(Math.round(durationMs)))
  return request<Turn>(`/api/sessions/${id}/turns/${index}/answer`, { method: 'POST', body: form })
}

export interface ReportResponse {
  job: { status: 'queued' | 'processing' | 'ready' | 'partial' | 'failed'; error_code: string }
  assessment: { status: string; scope: string; overall: number | null; report: import('./report').Report | null;
                provenance: Record<string, unknown> } | null
}

export const getReport = (id: string) => request<ReportResponse>(`/api/sessions/${id}/report`)
export const reassess = (id: string) => postJson<{ status: string }>(`/api/sessions/${id}/assess`)
export const turnAudioUrl = (id: string, index: number) => `/api/sessions/${id}/turns/${index}/audio`
