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
import { buildQueue, isAnswerStep, silenceEnabled } from '../session/runner'

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
      const detector = createSilenceDetector({ threshold: micSession.threshold, enabled: silenceEnabled(step) })
      await new Promise<void>((done) => {
        const maxMs = (step.max_answer_s ?? 60) * 1000
        const t0 = performance.now()
        const timer = setInterval(() => {
          const now = performance.now()
          if (aborted || detector.push(mic.level(), now) === 'silence_end' || now - t0 >= maxMs) finish()
        }, 50)
        function finish() { clearInterval(timer); tapRef.current = null; done() }
        tapRef.current = finish
      })
      const { blob, durationMs } = await rec.stop(); guard()
      setLongTurnCard(null)
      setMimo('thinking')
      await retrying(() => uploadAnswer(id, step.index, blob, clampDuration(durationMs, step.max_answer_s ?? 60)))
    }

    async function run() {
      const answered = new Set(session!.turns.filter((t) => t.answered_at).map((t) => t.index))
      for (const action of buildQueue(session!.plan, answered)) {
        guard()
        if (action.type === 'speak') {
          if (action.step.kind === 'question') void begin(action.step.index).catch(() => undefined)
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
    return () => { aborted = true; cancelSpeech(); tapRef.current?.(); prepDoneRef.current?.(); retryRef.current?.() }
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
            <textarea rows={4} placeholder="Tulis poin-poin singkat…" value={notes} onChange={(e) => setNotes(e.target.value)}
              style={{ borderRadius: 14, border: '1px solid var(--field-border)', background: 'var(--surface)', color: 'var(--ink)', padding: 12, fontSize: 15, lineHeight: 1.5, resize: 'none' }} />
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
  const answering = mimo === 'listening'
  return (
    <div className="screen">
      <header style={{ display: 'flex', justifyContent: 'flex-end', padding: 16 }}>
        <button type="button" className="icon-btn" aria-label="Akhiri sesi" onClick={endSession}><IconClose /></button>
      </header>
      {card && (
        <aside aria-label="Cue card" lang="en" className="card" style={{ margin: '0 24px', padding: '12px 14px', fontSize: 14, lineHeight: 1.45, color: 'var(--body)' }}>
          <strong style={{ color: 'var(--ink)' }}>{card.title}</strong> {card.bullets.join(' · ')} · {card.closing.replace(/^and /, '')}
          {notes.trim() && <p lang="id" style={{ margin: '8px 0 0', whiteSpace: 'pre-line', color: 'var(--muted)' }}>Catatanmu: {notes}</p>}
        </aside>
      )}
      <main style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {needMic ? (
          <button type="button" className="btn" onClick={enableMic}>Aktifkan mikrofon untuk lanjut</button>
        ) : (
          <Mimo state={mimo} width={340}
            label={{ speaking: 'Mimo sedang berbicara', listening: 'Mimo mendengarkan jawabanmu', thinking: 'Mimo memproses', ready: 'Mimo menunggu', encourage: 'Mimo menyemangati', success: 'Sesi selesai' }[mimo]}
            onTap={answering ? () => tapRef.current?.() : undefined} tapLabel="Ketuk untuk mengakhiri jawaban" />
        )}
      </main>
      <footer style={{ minHeight: 150, padding: '0 24px 40px', display: 'flex', alignItems: 'flex-end', justifyContent: 'center' }}>
        {netError ? (
          <div role="alert" style={{ display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'center' }}>
            <p className="error" style={{ margin: 0 }}>Koneksi ke server terputus. Jawabanmu masih aman; periksa koneksi, lalu coba lagi.</p>
            <button type="button" className="btn-secondary" onClick={() => retryRef.current?.()}>Coba lagi</button>
          </div>
        ) : caption ? (
          <p className="caption" role="status" aria-live="polite" lang="en">{caption}</p>
        ) : null}
      </footer>
      <span className="sr-only" aria-live="polite">{answering ? 'Merekam jawaban. Diam 3 detik atau ketuk Mimo untuk selesai.' : ''}</span>
      {session && !session.plan.some(isAnswerStep) && <p className="error">Rencana sesi kosong.</p>}
    </div>
  )
}
