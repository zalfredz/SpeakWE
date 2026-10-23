import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { Mode } from '../api'
import { IconBack, IconInfo } from '../icons'

const OPTIONS: { id: Mode; title: string; duration: string; desc: string }[] = [
  { id: 'full', title: 'Full test', duration: '± 14 menit', desc: 'Part 1 → Part 2 → Part 3 berurutan, seperti tes asli.' },
  { id: 'part1', title: 'Part 1', duration: '± 5 menit', desc: 'Pertanyaan tentang dirimu dan topik sehari-hari.' },
  { id: 'part2', title: 'Part 2', duration: '± 4 menit', desc: 'Cue card: 1 menit persiapan, bicara sampai 2 menit.' },
  { id: 'part3', title: 'Part 3', duration: '± 5 menit', desc: 'Diskusi lebih dalam dan abstrak.' },
]

export default function Choose() {
  const [mode, setMode] = useState<Mode>('full')
  return (
    <div className="screen">
      <header className="topbar">
        <Link to="/" className="back" aria-label="Kembali ke beranda"><IconBack /></Link>
        <h1>IELTS Speaking</h1>
      </header>
      <main className="content">
        <p className="muted" style={{ margin: 0, fontSize: 15, lineHeight: 1.5 }}>Pilih bagian yang mau kamu latih. Topik diacak dari bank soal SpeakWE.</p>
        <fieldset style={{ border: 0, margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <legend className="sr-only">Jenis latihan</legend>
          {OPTIONS.map((o) => (
            <label key={o.id} className="card" style={{ display: 'flex', gap: 12, alignItems: 'flex-start', cursor: 'pointer', border: `2px solid ${mode === o.id ? 'var(--lilac)' : 'var(--line)'}` }}>
              <input type="radio" name="mode" value={o.id} checked={mode === o.id} onChange={() => setMode(o.id)}
                style={{ width: 20, height: 20, margin: '2px 0 0', accentColor: 'var(--lilac)' }} />
              <span style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 4 }}>
                <span style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                  <strong style={{ fontSize: 16 }}>{o.title}</strong>
                  <span className="muted" style={{ fontSize: 13, whiteSpace: 'nowrap' }}>{o.duration}</span>
                </span>
                <span className="muted" style={{ fontSize: 14, lineHeight: 1.45 }}>{o.desc}</span>
              </span>
            </label>
          ))}
        </fieldset>
        <div className="info"><IconInfo /><span>Hasilnya estimasi latihan SpeakWE, bukan nilai resmi IELTS.</span></div>
        <Link to={`/mic?mode=${mode}`} className="btn" style={{ marginTop: 'auto' }}>Lanjut ke cek mikrofon</Link>
      </main>
    </div>
  )
}
