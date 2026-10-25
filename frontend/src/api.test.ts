import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, completeSession, createSession, uploadAnswer } from './api'

function stubFetch(status: number, body: unknown) {
  const fn = vi.fn(async () => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }))
  vi.stubGlobal('fetch', fn)
  return fn
}

afterEach(() => { vi.unstubAllGlobals() })

describe('api', () => {
  it('creates a session with a JSON body', async () => {
    const fn = stubFetch(201, { id: 's1', mode: 'full', status: 'created', plan: [], turns: [] })
    const s = await createSession('full')
    expect(s.id).toBe('s1')
    const [url, init] = fn.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('/api/sessions')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual({ mode: 'full', training_consent: false })
  })

  it('uploads an answer as multipart with audio and duration_ms', async () => {
    const fn = stubFetch(201, { index: 1, duration_ms: 1500 })
    await uploadAnswer('s1', 1, new Blob(['x'], { type: 'audio/webm;codecs=opus' }), 1500)
    const [url, init] = fn.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('/api/sessions/s1/turns/1/answer')
    const form = init.body as FormData
    expect(form.get('duration_ms')).toBe('1500')
    expect((form.get('audio') as File).name).toBe('answer.webm')
  })

  it('turns backend errors into ApiError with status and code', async () => {
    stubFetch(409, { error: 'unanswered_turns', detail: 'Unanswered steps: 2' })
    const err = await completeSession('s1').catch((e) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err.status).toBe(409)
    expect(err.code).toBe('unanswered_turns')
  })
})
