import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ApiError, createSession, setState, type Mode } from '../api'
import { listMics, micErrorMessage, openMic, startRecording, type Mic } from '../audio/mic'
import { micSession } from '../audio/micSession'
import { unlockSpeech } from '../audio/speak'
import { thresholdFromNoise } from '../audio/silence'
import { IconBack, IconCheck } from '../icons'

const MODES: Mode[] = ['full', 'part1', 'part2', 'part3']
const BARS = 10

export default function MicCheck() {
  const [params] = useSearchParams()
  const mode = (MODES.includes(params.get('mode') as Mode) ? params.get('mode') : 'full') as Mode
  const navigate = useNavigate()
  const [mic, setMic] = useState<Mic | null>(null)
  const [error, setError] = useState('')
  const [level, setLevel] = useState(0)
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([])
  const [deviceId, setDeviceId] = useState('')
  const [testUrl, setTestUrl] = useState('')
  const [recording, setRecording] = useState(false)
  const [starting, setStarting] = useState(false)
  const [calibrating, setCalibrating] = useState(false)
  const [consent, setConsent] = useState(false)
  const [browser, setBrowser] = useState<'chrome' | 'safari'>(/^((?!chrome|android).)*safari/i.test(navigator.userAgent) ? 'safari' : 'chrome')
  const noise = useRef<number[]>([])
  const handedOver = useRef(false)

  // live level meter + noise floor from the first second after permission
  useEffect(() => {
    if (!mic) return
    noise.current = []
    setCalibrating(true)
    const started = performance.now()
    const id = setInterval(() => {
      const l = mic.level()
      setLevel(l)
      if (performance.now() - started < 1000) noise.current.push(l)
      else setCalibrating(false)
    }, 50)
    return () => clearInterval(id)
  }, [mic])

  // release the mic if the user leaves without starting the test
  useEffect(() => () => { if (!handedOver.current) micSession.mic?.close() }, [])

  async function allow(id = deviceId) {
    setError('')
    try {
      micSession.mic?.close()
      micSession.mic = null
      setMic(null)
      const m = await openMic(id || undefined)
      micSession.mic = m
      setMic(m)
      setDevices(await listMics())
    } catch (e) {
      setError(micErrorMessage(e))
    }
  }

  async function testRecord() {
    if (!mic) return
    setRecording(true)
    const rec = startRecording(mic.stream)
    await new Promise((r) => setTimeout(r, 5000))
    const { blob } = await rec.stop()
    setRecording(false)
    setTestUrl(URL.createObjectURL(blob))
  }

  async function start() {
    unlockSpeech()
    setStarting(true)
    setError('')
    try {
      // 20th percentile: robust even if the learner spoke during part of the calibration second
      const sorted = [...noise.current].sort((a, b) => a - b)
      micSession.threshold = thresholdFromNoise(sorted[Math.floor(sorted.length * 0.2)] ?? 0.005)
      const s = await createSession(mode, consent)
      await setState(s.id, 'mic_check')
      await setState(s.id, 'active')
      handedOver.current = true
      navigate(`/room/${s.id}`)
    } catch (e) {
      setStarting(false)
      setError(e instanceof ApiError && e.code === 'bank_too_small'
        ? 'Bank soal belum siap. Approve topik Part 1 dan cue card di halaman admin dulu.'
        : 'Sesi belum bisa dibuat. Pastikan server SpeakWE berjalan, lalu coba lagi.')
    }
  }

  const lit = Math.min(BARS, Math.round(level * 60))
  return (
    <div className="screen">
      <header className="topbar">
        <Link to="/choose" className="back" aria-label="Kembali"><IconBack /></Link>
        <h1>Cek mikrofon</h1>
      </header>
      <main className="content">
        <ol style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <li className="card" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ flex: 1 }}>
              <strong style={{ display: 'block', fontSize: 15 }}>1. Izin mikrofon</strong>
              <span style={{ fontSize: 14, color: mic ? 'var(--ok-ink)' : 'var(--muted)' }}>{mic ? 'Diizinkan' : 'Belum diizinkan'}</span>
            </span>
            {mic
              ? <span style={{ width: 32, height: 32, borderRadius: 999, background: 'var(--ok-soft)', color: 'var(--ok-ink)', display: 'grid', placeItems: 'center' }}><IconCheck /></span>
              : <button type="button" className="btn-secondary" onClick={() => allow()}>Izinkan</button>}
          </li>

          <li className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12, opacity: mic ? 1 : 0.55 }}>
            <span style={{ display: 'flex', justifyContent: 'space-between' }}>
              <strong style={{ fontSize: 15 }}>2. Suara masuk</strong>
              <span className="muted" style={{ fontSize: 13 }} aria-live="polite">{!mic ? '—' : calibrating ? 'Diam sebentar…' : 'Bicara sekarang'}</span>
            </span>
            <span role="meter" aria-label="Level suara mikrofon" aria-valuemin={0} aria-valuemax={BARS} aria-valuenow={lit}
              style={{ display: 'flex', alignItems: 'flex-end', gap: 5, height: 40 }}>
              {Array.from({ length: BARS }, (_, i) => (
                <span key={i} style={{ flex: 1, height: `${20 + i * 8}%`, borderRadius: 4, background: i < lit ? 'var(--lilac)' : 'var(--meter-off)', transition: 'background .1s' }} />
              ))}
            </span>
            {devices.length > 1 && (
              <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 13 }} className="muted">
                Mikrofon
                <select value={deviceId} onChange={(e) => { setDeviceId(e.target.value); void allow(e.target.value) }}
                  style={{ minHeight: 44, borderRadius: 12, border: '1px solid var(--field-border)', background: 'var(--ground)', padding: '0 12px', fontSize: 15, color: 'var(--ink)' }}>
                  {devices.map((d, i) => <option key={d.deviceId} value={d.deviceId}>{d.label || `Mikrofon ${i + 1}`}</option>)}
                </select>
              </label>
            )}
          </li>

          <li className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10, opacity: mic ? 1 : 0.55 }}>
            <strong style={{ fontSize: 15 }}>3. Tes rekam 5 detik</strong>
            <span className="muted" style={{ fontSize: 14, lineHeight: 1.45 }}>Ucapkan: “Hello, my name is …” lalu dengarkan hasilnya.</span>
            <span style={{ display: 'flex', gap: 8 }}>
              <button type="button" className="btn-secondary" style={{ flex: 1, color: 'var(--accent-text)', borderColor: 'var(--lilac)', fontWeight: 700 }}
                disabled={!mic || recording} onClick={testRecord}>{recording ? 'Merekam…' : 'Rekam tes'}</button>
            </span>
            {testUrl && <audio controls src={testUrl} style={{ width: '100%' }} aria-label="Hasil rekaman tes" />}
          </li>
        </ol>

        {error && <p className="error" role="alert" style={{ margin: 0 }}>{error}</p>}

        <section aria-label="Bantuan mikrofon" className="info" style={{ flexDirection: 'column', gap: 10 }}>
          <strong>Mikrofon tidak terdeteksi?</strong>
          <span role="tablist" aria-label="Pilih browser" style={{ display: 'flex', gap: 6 }}>
            {(['chrome', 'safari'] as const).map((b) => (
              <button key={b} type="button" role="tab" aria-selected={browser === b} onClick={() => setBrowser(b)}
                style={{ minHeight: 36, padding: '0 14px', borderRadius: 999, fontWeight: 700, cursor: 'pointer',
                  border: `1px solid ${browser === b ? 'var(--lilac)' : 'var(--chip-border)'}`, background: browser === b ? 'var(--lilac)' : 'var(--surface)', color: browser === b ? 'var(--on-accent)' : 'var(--lilac-ink)' }}>
                {b === 'chrome' ? 'Chrome' : 'Safari'}
              </button>
            ))}
          </span>
          <span style={{ fontSize: 13, lineHeight: 1.5 }}>
            {browser === 'chrome'
              ? 'Klik ikon di kiri alamat situs → Mikrofon → Izinkan, lalu muat ulang halaman.'
              : 'iPhone: Pengaturan → Safari → Mikrofon → Izinkan. Mac: Safari → Pengaturan → Situs Web → Mikrofon.'}
          </span>
        </section>

        <label style={{ display: 'flex', alignItems: 'flex-start', gap: 10, fontSize: 14, lineHeight: 1.45, marginTop: 'auto', cursor: 'pointer' }}>
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} style={{ width: 20, height: 20, marginTop: 1, accentColor: 'var(--lilac)', flexShrink: 0 }} />
          <span>Boleh pakai rekaman dan hasil sesi ini untuk melatih penilai SpeakWE. <span className="muted">Opsional, tidak memengaruhi nilaimu.</span></span>
        </label>

        <button type="button" className="btn" disabled={!mic || starting || calibrating} onClick={start}>
          {starting ? 'Menyiapkan sesi…' : 'Mikrofon oke, mulai tes'}
        </button>
      </main>
    </div>
  )
}
