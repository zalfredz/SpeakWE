import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { beginTurn, completeSession, getSession, setState, uploadAnswer, type Session, type Step } from '../api'
import { micErrorMessage, openMic, startRecording } from '../audio/mic'
import { micSession } from '../audio/micSession'
import { createSilenceDetector } from '../audio/silence'
import { cancelSpeech, speak, unlockSpeech } from '../audio/speak'
import { IconClose } from '../icons'
import type { MimoState } from '../mimo/engine'
import Mimo from '../mimo/Mimo'
import { clampDuration, withRetry } from '../session/retry'
import { buildQueue, isAnswerStep, LONG_TURN_MIN_S, partOver, silenceEnabled, silenceMsFor, SLEEPY_BEFORE_S, TELL_ME_MORE, WRAP_UP_BEFORE_S } from '../session/runner'

class Aborted extends Error {}

function cueCard(text: string) {
  const [title, , ...rest] = text.split('\n')   // "title\nYou should say:\nbullets…\nclosing"
  return { title, bullets: rest.slice(0, -1), closing: rest[rest.length - 1] }
}

export default function Room() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const [session, setSession] = useState<Session | null>(null)
  const [mimo, setMimo] = useState<MimoState>('ready')
  const [sleepy, setSleepy] = useState(false)   // a time-boxed part is nearly out of time
  const [caption, setCaption] = useState<string | null>(null)
  const [longTurnCard, setLongTurnCard] = useState<string | null>(null)
  const [prep, setPrep] = useState<{ step: Step; left: number } | null>(null)
  const [needMic, setNeedMic] = useState(!micSession.mic)
  const [netError, setNetError] = useState(false)
  const [notes, setNotes] = useState('')
  const [fatal, setFatal] = useState('')
  const tapRef = useRef<(() => void) | null>(null)       // ends the current answer
  const prepDoneRef = useRef<(() => void) | null>(null)
  const retryRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    getSession(id).then((s) => {
      if (s.status === 'completed') navigate(`/result/${id}`, { replace: true })
      else if (s.status !== 'active') setFatal('Sesi ini sudah berakhir. Mulai sesi baru dari beranda.')
      else setSession(s)
    }).catch(() => setFatal('Sesi tidak ditemukan.'))
  }, [id, navigate])

  // the session loop; restarts cleanly under React StrictMode because every await checks `aborted`
  useEffect(() => {
    if (!session || needMic) return
    let aborted = false
    const guard = () => { if (aborted) throw new Aborted() }
    const mic = micSession.mic!
    // one automatic retry, then a "Coba lagi" button; never skip an answer or lose a finished session
    const waitForUser = async () => {
      setNetError(true)
      await new Promise<void>((r) => { retryRef.current = r }); guard()
      setNetError(false)
    }
    const retrying = <T,>(fn: () => Promise<T>) => withRetry(fn, waitForUser)
    // begin is requested while Mimo is still asking, so recording can start the moment she stops
    const begun = new Map<number, Promise<unknown>>()
    const begin = (index: number) => { if (!begun.has(index)) begun.set(index, retrying(() => beginTurn(id, index))); return begun.get(index)! }

    async function answer(step: Step) {
      await begin(step.index); guard()
      const rec = startRecording(mic.stream)
      setMimo('listening')
      if (step.kind === 'long_turn') setLongTurnCard(step.text)
      const detector = createSilenceDetector({ threshold: micSession.threshold, enabled: silenceEnabled(step), silenceMs: silenceMsFor(step) })
      await new Promise<void>((done) => {
        const maxMs = (step.max_answer_s ?? 60) * 1000
        const t0 = performance.now()
        let prompted = false, prompting = false
        const timer = setInterval(() => {
          if (prompting) return
          const now = performance.now()
          if (step.kind === 'long_turn' && now - t0 >= maxMs - WRAP_UP_BEFORE_S * 1000) setMimo('wrapup')
          if (aborted || detector.push(mic.level(), now) === 'silence_end' || now - t0 >= maxMs) finish()
        }, 50)
        function finish() { clearInterval(timer); tapRef.current = null; done() }
        tapRef.current = () => {
          // like an examiner: a long turn stopped before one minute gets a single "tell me more"
          if (aborted || prompted || step.kind !== 'long_turn' || performance.now() - t0 >= LONG_TURN_MIN_S * 1000) return finish()
          prompted = prompting = true
          rec.pause(); setMimo('encourage'); setCaption(TELL_ME_MORE)
          speak(TELL_ME_MORE).finally(() => {
            setCaption(null); prompting = false
            if (!aborted) { rec.resume(); setMimo('listening') }
          })
        }
      })
      const { blob, durationMs } = await rec.stop(); guard()
      setLongTurnCard(null)
      setMimo('thinking')
      await retrying(() => uploadAnswer(id, step.index, blob, clampDuration(durationMs, step.max_answer_s ?? 60)))
    }

    // time-boxed parts (1 and 3): each clock starts when the part's first question is asked;
    // a reload resumes it from the server's begun_at
    const { plan, turns, part_limits: limits } = session!
    const timed = (s: Step) => s.kind === 'question' && String(s.part) in limits
    const clocks = new Map<number, { start: number | null; answered: number; cut: boolean }>()
    const clock = (part: number) => {
      if (!clocks.has(part)) {
        const mine = turns.filter((t) => plan[t.index].part === part && plan[t.index].kind === 'question')
        const begun = mine.filter((t) => t.begun_at).map((t) => Date.parse(t.begun_at!))
        clocks.set(part, { start: begun.length ? Math.min(...begun) : null, answered: mine.filter((t) => t.answered_at).length, cut: false })
      }
      return clocks.get(part)!
    }
    const elapsed = (part: number) => { const c = clock(part); return c.start === null ? 0 : (Date.now() - c.start) / 1000 }
    let timedPart: number | null = null   // the time-boxed part running now; drives the sleepy look
    const sleepyTimer = setInterval(() => setSleepy(timedPart !== null && !clock(timedPart).cut && clock(timedPart).start !== null
      && elapsed(timedPart) >= limits[timedPart].limit_s - SLEEPY_BEFORE_S), 1000)

    async function run() {
      const answered = new Set(turns.filter((t) => t.answered_at).map((t) => t.index))
      for (const action of buildQueue(plan, answered)) {
        guard()
        if (action.type !== 'complete' && timed(action.step)) {
          const part = action.step.part, c = clock(part), { limit_s, min_questions } = limits[part]
          timedPart = part
          // decided before asking, so a question is never asked and then dropped
          if (action.type === 'speak' && partOver(elapsed(part), c.answered, action.step.max_answer_s ?? 25, limit_s, min_questions)) c.cut = true
          if (c.cut) { setSleepy(false); continue }
        } else timedPart = null
        if (action.type === 'speak') {
          if (action.step.kind === 'question') {
            if (timed(action.step) && clock(action.step.part).start === null) clock(action.step.part).start = Date.now()
            void begin(action.step.index).catch(() => undefined)
          }
          setMimo('speaking'); setCaption(action.step.text)
          await speak(action.step.text); guard()
          setCaption(null); setMimo('ready')
        } else if (action.type === 'prep') {
          await new Promise<void>((done) => {
            let left = action.step.prep_s ?? 60
            setPrep({ step: action.step, left })
            const timer = setInterval(() => { left -= 1; if (aborted || left <= 0) finish(); else setPrep({ step: action.step, left }) }, 1000)
            function finish() { clearInterval(timer); prepDoneRef.current = null; setPrep(null); done() }
            prepDoneRef.current = finish
          })
          guard()
        } else if (action.type === 'answer') {
          await answer(action.step)
          if (timed(action.step)) clock(action.step.part).answered += 1
          setMimo('ready')
        } else {
          setMimo('success')
          const result = await retrying(() => completeSession(id)); guard()
          micSession.mic?.close(); micSession.mic = null   // the recording indicator must not stay on
          navigate(`/result/${id}`, { replace: true, state: result })
        }
      }
    }

    run().catch((e) => { if (!(e instanceof Aborted)) setFatal('Terjadi kendala saat menjalankan sesi. Coba mulai lagi dari beranda.') })
    return () => { aborted = true; clearInterval(sleepyTimer); cancelSpeech(); tapRef.current?.(); prepDoneRef.current?.(); retryRef.current?.() }
  }, [session, needMic, id, navigate])

  async function enableMic() {
    unlockSpeech()
    try { micSession.mic = await openMic(); setNeedMic(false) } catch (e) { setFatal(micErrorMessage(e)) }
  }

  async function endSession() {
    if (!window.confirm('Akhiri sesi ini? Jawaban yang sudah terekam tetap tersimpan, tapi sesi tidak dihitung selesai.')) return
    cancelSpeech()
    await setState(id, 'abandoned').catch(() => undefined)
    micSession.mic?.close(); micSession.mic = null
    navigate('/', { replace: true })
  }

  if (fatal) {
    return (
      <div className="screen"><main className="content" style={{ justifyContent: 'center' }}>
        <p className="error" role="alert">{fatal}</p>
        <button type="button" className="btn" onClick={() => navigate('/')}>Kembali ke beranda</button>
      </main></div>
    )
  }

  if (prep) {
    const card = cueCard(prep.step.text)
    return (
      <div className="screen">
        <header className="topbar" style={{ justifyContent: 'space-between', padding: '16px 20px 8px' }}>
          <strong style={{ fontSize: 15 }}>Part 2 · Waktu persiapan</strong>
          <button type="button" className="icon-btn" aria-label="Akhiri sesi" onClick={endSession}><IconClose /></button>
        </header>
        <main className="content" style={{ gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <Mimo state="thinking" width={96} label="Mimo sedang berpikir" />
            <div>
              <div className="muted" style={{ fontSize: 13 }}>Sisa waktu persiapan</div>
              <div style={{ fontSize: 32, fontWeight: 700, fontVariantNumeric: 'tabular-nums' }} role="timer" aria-live="off">
                {Math.floor(prep.left / 60)}:{String(prep.left % 60).padStart(2, '0')}
              </div>
            </div>
          </div>
          <article className="card" aria-label="Cue card" lang="en" style={{ display: 'flex', flexDirection: 'column', gap: 10, borderRadius: 20, padding: 20 }}>
            <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--accent-text)' }}>Cue card</span>
            <h1 style={{ margin: 0, fontSize: 20, lineHeight: 1.35 }}>{card.title}</h1>
            <span className="muted" style={{ fontSize: 15 }}>You should say:</span>
            <ul style={{ margin: 0, paddingLeft: 20, fontSize: 15, lineHeight: 1.5 }}>{card.bullets.map((b) => <li key={b}>{b}</li>)}</ul>
            <span style={{ fontSize: 15 }}>{card.closing}</span>
          </article>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 14, fontWeight: 500 }}>
            Catatan (opsional, tidak dinilai)
            {/* 16px stops iOS zooming in on focus; scrolling keeps the field above the phone keyboard */}
            <textarea rows={4} placeholder="Tulis poin-poin singkat…" value={notes} onChange={(e) => setNotes(e.target.value)}
              onFocus={(e) => { const el = e.currentTarget; setTimeout(() => el.scrollIntoView({ block: 'center', behavior: 'smooth' }), 300) }}
              style={{ borderRadius: 14, border: '1px solid var(--field-border)', background: 'var(--surface)', color: 'var(--ink)', padding: 12, fontSize: 16, lineHeight: 1.5, resize: 'none' }} />
          </label>
          <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
            <span className="muted" style={{ textAlign: 'center', fontSize: 14 }}>Setelah persiapan, kamu bicara sampai 2 menit.</span>
            <button type="button" className="btn" onClick={() => prepDoneRef.current?.()}>Siap, mulai bicara</button>
          </div>
        </main>
      </div>
    )
  }

  const card = longTurnCard ? cueCard(longTurnCard) : null
  const answering = mimo === 'listening' || mimo === 'wrapup'
  return (
    <div className="screen">
      <header style={{ display: 'flex', justifyContent: 'flex-end', padding: 16 }}>
        <button type="button" className="icon-btn" aria-label="Akhiri sesi" onClick={endSession}><IconClose /></button>
      </header>
      {card && (
        // stays on screen for the whole long turn; Mimo shrinks so card + notes fit a 360 px phone without scrolling the page
        <aside aria-label="Cue card" className="card" style={{ margin: '0 16px', display: 'flex', flexDirection: 'column', gap: 8, fontSize: 16, lineHeight: 1.45, color: 'var(--body)' }}>
          <div lang="en">
            <span style={{ display: 'block', fontSize: 12, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--accent-text)' }}>Cue card</span>
            <strong style={{ display: 'block', color: 'var(--ink)', fontSize: 17 }}>{card.title}</strong>
            <ul style={{ margin: '6px 0 0', paddingLeft: 20 }}>{card.bullets.map((b) => <li key={b}>{b}</li>)}</ul>
            <span>{card.closing}</span>
          </div>
          {notes.trim() && (
            <div style={{ borderTop: '1px solid var(--line)', paddingTop: 8 }}>
              <span className="muted" style={{ fontSize: 13, fontWeight: 600 }}>Catatanmu</span>
              <p style={{ margin: '2px 0 0', whiteSpace: 'pre-line', color: 'var(--ink)', maxHeight: '24svh', overflowY: 'auto' }}>{notes}</p>
            </div>
          )}
        </aside>
      )}
      <main style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {needMic ? (
          <button type="button" className="btn" onClick={enableMic}>Aktifkan mikrofon untuk lanjut</button>
        ) : (
          <Mimo state={sleepy && (mimo === 'listening' || mimo === 'ready') ? 'sleepy' : mimo} width={card ? 220 : 340}
            label={sleepy && answering ? 'Mimo mendengarkan, waktu bagian ini hampir habis' : { speaking: 'Mimo sedang berbicara', listening: 'Mimo mendengarkan jawabanmu', thinking: 'Mimo memproses', ready: 'Mimo menunggu', encourage: 'Mimo menyemangati', success: 'Sesi selesai', sleepy: 'Waktu bagian ini hampir habis', wrapup: 'Mimo mendengarkan, waktu bicara hampir habis' }[mimo]}
            onTap={answering ? () => tapRef.current?.() : undefined} tapLabel="Ketuk untuk mengakhiri jawaban" />
        )}
      </main>
      <footer style={{ minHeight: card ? 0 : 150, padding: card ? '0 24px 16px' : '0 24px 40px', display: 'flex', alignItems: 'flex-end', justifyContent: 'center' }}>
        {netError ? (
          <div role="alert" style={{ display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'center' }}>
            <p className="error" style={{ margin: 0 }}>Koneksi ke server terputus. Jawabanmu masih aman; periksa koneksi, lalu coba lagi.</p>
            <button type="button" className="btn-secondary" onClick={() => retryRef.current?.()}>Coba lagi</button>
          </div>
        ) : caption ? (
          <p className="caption" role="status" aria-live="polite" lang="en">{caption}</p>
        ) : null}
      </footer>
      <span className="sr-only" aria-live="polite">{answering ? 'Merekam jawaban. Ketuk Mimo kalau sudah selesai.' : ''}</span>
      {session && !session.plan.some(isAnswerStep) && <p className="error">Rencana sesi kosong.</p>}
    </div>
  )
}
