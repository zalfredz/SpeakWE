import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { getSession, type CompleteResult, type Session } from '../api'
import { IconBack } from '../icons'
import { formatDuration } from '../session/retry'
import AssessmentSection from './Assessment'
import { isAnswerStep } from '../session/runner'

const MODE_LABEL: Record<string, string> = { full: 'Full test', part1: 'Part 1', part2: 'Part 2', part3: 'Part 3' }

// Session facts, then the evaluator report (polled until the worker finishes).
export default function Result() {
  const { id = '' } = useParams()
  const fromRoom = useLocation().state as CompleteResult | null
  const [session, setSession] = useState<Session | null>(fromRoom?.session ?? null)
  const [failed, setFailed] = useState(false)
  useEffect(() => { if (!session) getSession(id).then(setSession).catch(() => setFailed(true)) }, [id, session])

  if (!session) {
    return <div className="screen"><main className="content">
      {failed ? <><p className="error" role="alert">Hasil sesi belum bisa dimuat.</p><Link to="/" className="btn">Kembali ke beranda</Link></>
              : <p className="muted">Memuat hasil…</p>}
    </main></div>
  }

  const totalMs = session.turns.reduce((sum, t) => sum + (t.duration_ms ?? 0), 0)
  const answers = session.turns.filter((t) => t.answered_at).length
  const parts = [...new Set(session.plan.filter(isAnswerStep).map((s) => s.part))]
  const date = new Date(session.completed_at ?? session.created_at).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' })
  const checkin = fromRoom?.checkin

  return (
    <div className="screen">
      <header className="topbar">
        <Link to="/" className="back" aria-label="Kembali ke beranda"><IconBack /></Link>
        <div><h1>{session.status === 'completed' ? 'Sesi selesai' : 'Sesi berakhir'}</h1><span className="muted" style={{ fontSize: 13 }}>{MODE_LABEL[session.mode]} · {date}</span></div>
      </header>
      <main className="content">
        <section className="card" aria-label="Ringkasan sesi">
          <dl style={{ margin: 0, display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 8, textAlign: 'center' }}>
            <div><dt className="muted" style={{ fontSize: 13 }}>Jawaban</dt><dd style={{ margin: 0, fontSize: 24, fontWeight: 700 }}>{answers}</dd></div>
            <div><dt className="muted" style={{ fontSize: 13 }}>Waktu bicara</dt><dd style={{ margin: 0, fontSize: 24, fontWeight: 700 }}>{formatDuration(totalMs)}</dd></div>
            <div><dt className="muted" style={{ fontSize: 13 }}>Part</dt><dd style={{ margin: 0, fontSize: 24, fontWeight: 700 }}>{parts.join(', ')}</dd></div>
          </dl>
        </section>

        {fromRoom && (
          <section className="card" aria-label="Check-in">
            <strong style={{ fontSize: 15 }}>Check-in hari ini</strong>
            <p className="muted" style={{ margin: '4px 0 0', fontSize: 14, lineHeight: 1.5 }}>
              {checkin ? 'Check-in hari ini tercatat.' : 'Belum tercatat: butuh minimal 60 detik bicara dalam satu sesi.'}
            </p>
          </section>
        )}

        {session.status === 'completed' && <AssessmentSection sessionId={session.id} plan={session.plan} />}

        <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <Link to="/choose" className="btn">Latihan lagi</Link>
          <Link to="/" className="btn-secondary" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', textDecoration: 'none' }}>Kembali ke beranda</Link>
        </div>
      </main>
    </div>
  )
}
