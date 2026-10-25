import { useEffect, useRef, useState } from 'react'
import { getReport, reassess, turnAudioUrl, type ReportResponse } from '../api'
import { IconInfo } from '../icons'
import type { Step } from '../api'
import { answerNumber, bandsFromReport, evidenceFor, formatMs, type Report } from '../report'

const POLL_MS = 3000

// Plays the quoted moment of one answer: from start_ms to end_ms.
function PlayClip({ sessionId, turnIndex, startMs, endMs }: { sessionId: string; turnIndex: number; startMs: number; endMs: number }) {
  const audio = useRef<HTMLAudioElement | null>(null)
  const url = useRef<string | null>(null)
  useEffect(() => () => { audio.current?.pause(); if (url.current) URL.revokeObjectURL(url.current) }, [])
  async function play() {
    audio.current?.pause()
    // the server re-encodes to mp3 (seekable); a blob URL lets the browser seek without HTTP Range support
    if (!url.current) url.current = URL.createObjectURL(await (await fetch(turnAudioUrl(sessionId, turnIndex))).blob())
    const a = new Audio(url.current)
    audio.current = a
    a.addEventListener('loadedmetadata', () => { a.currentTime = startMs / 1000 }, { once: true })
    a.addEventListener('timeupdate', () => { if (a.currentTime * 1000 >= endMs) a.pause() })
    void a.play()
  }
  return (
    <button type="button" onClick={play} aria-label={`Putar jawaban di menit ${formatMs(startMs)}`}
      style={{ width: 44, height: 44, borderRadius: 999, border: 0, background: 'var(--lilac-soft)', color: 'var(--accent-text)', display: 'grid', placeItems: 'center', flexShrink: 0, cursor: 'pointer' }}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M8 5v14l11-7z" /></svg>
    </button>
  )
}

function ReportView({ sessionId, plan, scope, overall, report, provenance }: { sessionId: string; plan: Step[]; scope: string; overall: number | null; report: Report; provenance: Record<string, unknown> }) {
  const partOnly = scope.match(/^part(\d)_only$/)?.[1]
  const bands = bandsFromReport(report)
  const fb = report.feedback
  return (
    <>
      <section className="card" aria-label="Estimasi skor" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 8 }}>
          <div>
            <div className="muted" style={{ fontSize: 13 }}>{overall !== null ? 'Estimasi overall' : partOnly ? `Estimasi terbatas Part ${partOnly}` : 'Estimasi per kriteria'}</div>
            {overall !== null && <div style={{ fontSize: 44, lineHeight: 1, fontWeight: 700 }}>{overall.toFixed(1)}</div>}
          </div>
          <span style={{ padding: '6px 10px', borderRadius: 999, background: 'var(--lilac-soft)', color: 'var(--lilac-ink)', fontSize: 12, fontWeight: 700 }}>Bukan nilai resmi IELTS</span>
        </div>
        <dl style={{ margin: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
          {bands.map((b) => (
            <div key={b.key}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14 }}>
                <dt>{b.label}</dt><dd style={{ margin: 0, fontWeight: 700 }}>{b.band ?? '—'}</dd>
              </div>
              <div aria-hidden="true" style={{ height: 8, borderRadius: 999, background: 'var(--lilac-soft)', overflow: 'hidden', marginTop: 6 }}>
                <div style={{ height: '100%', width: `${((b.band ?? 0) / 9) * 100}%`, background: 'var(--lilac)', borderRadius: 999 }} />
              </div>
            </div>
          ))}
        </dl>
        {overall === null && <p className="muted" style={{ margin: 0, fontSize: 13 }}>Overall hanya dihitung untuk full test dengan keempat kriteria terisi.</p>}
        {overall !== null && provenance.calibration !== 'none' && <p className="muted" style={{ margin: 0, fontSize: 13 }}>Overall sudah dikalibrasi dengan nilai examiner asli. Nilai per kriteria masih penilaian AI dan cenderung lebih rendah untuk band tinggi.</p>}
      </section>

      {fb?.summary_id && (
        <section aria-label="Ringkasan">
          <h2 style={{ margin: '0 0 6px', fontSize: 16 }}>Ringkasan</h2>
          <p style={{ margin: 0, fontSize: 15, lineHeight: 1.55, color: 'var(--body)' }}>{fb.summary_id}</p>
        </section>
      )}

      {!!fb?.priorities?.length && (
        <section aria-label="Prioritas perbaikan" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <h2 style={{ margin: 0, fontSize: 16 }}>Prioritas perbaikan</h2>
          {fb.priorities.map((p, i) => {
            const ev = evidenceFor(report, p.criterion, p.evidence_segment_ids)
            return (
              <article key={i} className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ width: 26, height: 26, borderRadius: 999, background: i === 0 ? 'var(--lilac)' : 'var(--lilac-soft)', color: i === 0 ? 'var(--on-accent)' : 'var(--lilac-ink)', fontSize: 13, fontWeight: 700, display: 'grid', placeItems: 'center', flexShrink: 0 }}>{i + 1}</span>
                  <strong style={{ fontSize: 15 }}>{p.title_id}</strong>
                </div>
                <p style={{ margin: 0, fontSize: 14, lineHeight: 1.5, color: 'var(--body)' }}>{p.explanation_id}</p>
                {ev && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', borderRadius: 12, background: 'var(--ground)' }}>
                    <PlayClip sessionId={sessionId} turnIndex={ev.turnIndex} startMs={ev.start_ms} endMs={ev.end_ms} />
                    <span style={{ fontSize: 14, lineHeight: 1.45 }}>
                      <span className="muted" style={{ display: 'block', fontSize: 12 }}>Jawaban {answerNumber(plan, ev.turnIndex)} · {formatMs(ev.start_ms)}</span>
                      <q lang="en">{ev.quote.replace(/\[\?\]/g, '')}</q>{/* [?] marks are ASR hints for the evaluator, not for learners */}
                    </span>
                  </div>
                )}
                <p style={{ margin: 0, fontSize: 14, lineHeight: 1.5 }}><strong>Latihan:</strong> {p.drill_id}</p>
              </article>
            )
          })}
        </section>
      )}

      {!!fb?.upgrade_opportunities?.length && (
        <section aria-label="Yang bisa diperbaiki" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <h2 style={{ margin: 0, fontSize: 16 }}>Yang bisa diperbaiki</h2>
          {fb.upgrade_opportunities.map((u, i) => (
            <div key={i} className="card" lang="en" style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span className="muted" style={{ fontSize: 14, textDecoration: u.grammar_fix ? 'line-through' : 'none' }}>{u.original}</span>
              {u.grammar_fix
                ? <span style={{ fontSize: 15, fontWeight: 700 }}>{u.grammar_fix}</span>
                : <span lang="id" style={{ fontSize: 14 }}>Maksudnya: <span lang="en">{u.intended_meaning_en}</span></span>}
              {u.note_id && <span lang="id" className="muted" style={{ fontSize: 13 }}>{u.note_id}</span>}
            </div>
          ))}
        </section>
      )}

      <section aria-label="Penjelasan per kriteria" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <h2 style={{ margin: 0, fontSize: 16 }}>Kenapa bukan band lebih tinggi?</h2>
        {bands.filter((b) => b.band !== null).map((b) => (
          <details key={b.key} className="card">
            <summary style={{ cursor: 'pointer', fontWeight: 700, fontSize: 15 }}>{b.label} · {b.band}</summary>
            <p style={{ margin: '8px 0 0', fontSize: 14, lineHeight: 1.5, color: 'var(--body)' }}>{report.criteria[b.key].why_not_higher_id}</p>
          </details>
        ))}
      </section>

      <p className="muted" style={{ margin: 0, fontSize: 12 }}>
        Estimasi latihan SpeakWE · {String(provenance.model)} · {String(provenance.prompt_version)} · rubrik IELTS publik
      </p>
    </>
  )
}

export default function AssessmentSection({ sessionId, plan }: { sessionId: string; plan: Step[] }) {
  const [data, setData] = useState<ReportResponse | null>(null)
  const [unavailable, setUnavailable] = useState(false)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    let live = true, failures = 0
    let timer: ReturnType<typeof setTimeout>
    const load = () => getReport(sessionId)
      .then((r) => {
        if (!live) return
        failures = 0
        setData(r)
        if (r.job.status === 'queued' || r.job.status === 'processing') timer = setTimeout(load, POLL_MS)
      })
      .catch(() => {
        if (!live) return
        if (++failures >= 5) setUnavailable(true)
        else timer = setTimeout(load, POLL_MS * failures)
      })
    void load()
    return () => { live = false; clearTimeout(timer) }
  }, [sessionId, tick])

  async function retry() {
    await reassess(sessionId).catch(() => undefined)
    setData(null)
    setTick((t) => t + 1)
  }

  if (unavailable) return <div className="info"><IconInfo /><span>Penilaian belum tersedia untuk sesi ini.</span></div>
  if (!data || data.job.status === 'queued' || data.job.status === 'processing') {
    return (
      <div className="info" role="status" aria-live="polite"><IconInfo />
        <span>{data?.job.status === 'processing' ? 'Mimo sedang menilai jawabanmu… biasanya 1–2 menit.' : 'Penilaian sedang disiapkan. Pastikan worker penilaian berjalan.'}</span>
      </div>
    )
  }
  if (data.job.status === 'failed') {
    return (
      <div role="alert" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <p className="error" style={{ margin: 0 }}>Penilaian gagal ({data.job.error_code || 'error'}). Rekamanmu tetap tersimpan.</p>
        <button type="button" className="btn-secondary" onClick={retry}>Coba nilai ulang</button>
      </div>
    )
  }
  const a = data.assessment
  if (!a || a.status === 'insufficient_evidence' || !a.report) {
    return <div className="info"><IconInfo /><span>Bukti belum cukup untuk memberi estimasi: butuh minimal 60 detik bicara per Part (dan 3 jawaban untuk Part 1 dan 3). Coba sesi yang lebih panjang.</span></div>
  }
  return (
    <>
      {a.status === 'partial' && <div className="info"><IconInfo /><span>Sebagian Part belum cukup bukti, jadi estimasi ini hanya dari Part yang cukup.</span></div>}
      <ReportView sessionId={sessionId} plan={plan} scope={a.scope} overall={a.overall} report={a.report} provenance={a.provenance} />
    </>
  )
}
