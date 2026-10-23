import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getCheckins, type Checkins } from '../api'
import { micSession } from '../audio/micSession'
import { IconCalendar, IconClock, IconFlame, IconGear, IconHome, IconMic } from '../icons'
import Mimo from '../mimo/Mimo'
import ThemeSwitch from '../ThemeSwitch'

export default function Home() {
  const [checkins, setCheckins] = useState<Checkins | null>(null)
  const [offline, setOffline] = useState(false)
  useEffect(() => { getCheckins().then(setCheckins).catch(() => setOffline(true)) }, [])
  useEffect(() => { micSession.mic?.close(); micSession.mic = null }, [])
  const doneToday = !!checkins && checkins.dates.includes(checkins.today)

  return (
    <div className="screen">
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 20px 8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div aria-hidden="true" style={{ width: 32, height: 32, borderRadius: 10, background: 'var(--lilac)', color: 'var(--on-accent)', display: 'grid', placeItems: 'center', fontWeight: 700 }}>S</div>
          <span style={{ fontSize: 18, fontWeight: 700 }}>SpeakWE</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {checkins && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px', borderRadius: 999, background: 'var(--peach-soft)', color: 'var(--peach-ink)', fontSize: 14, fontWeight: 500 }}>
              <IconFlame /><span>{checkins.streak} hari</span>
            </div>
          )}
          <ThemeSwitch />
        </div>
      </header>

      <main className="content">
        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <Mimo state="ready" width={300} label="Mimo, maskot axolotl SpeakWE, melambaikan tangan" />
        </div>
        <div style={{ textAlign: 'center' }}>
          <h1 style={{ margin: '0 0 6px', fontSize: 26, letterSpacing: '-0.02em' }}>Hai, aku Mimo!</h1>
          <p className="muted" style={{ margin: 0, fontSize: 16, lineHeight: 1.5 }}>Yuk latihan speaking hari ini. Satu sesi selesai sudah cukup untuk check-in.</p>
        </div>

        <section className="card" aria-label="Check-in hari ini" style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ width: 44, height: 44, borderRadius: 14, background: 'var(--lilac-soft)', color: 'var(--accent-text)', display: 'grid', placeItems: 'center', flexShrink: 0 }}><IconCalendar /></div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700 }}>Check-in hari ini</div>
            <div className="muted" style={{ fontSize: 14 }}>
              {offline ? 'Server belum tersambung.' : !checkins ? 'Memuat…' : doneToday ? 'Sudah tercatat. Mantap!' : 'Belum. Selesaikan 1 sesi latihan.'}
            </div>
          </div>
        </section>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 'auto' }}>
          <Link to="/choose" className="btn"><IconMic />Mulai IELTS Speaking</Link>
          <button type="button" className="btn-secondary" disabled>Daily Conversation · segera hadir</button>
        </div>
      </main>

      <nav className="bottom-nav" aria-label="Navigasi utama">
        <Link to="/" aria-current="page"><IconHome />Beranda</Link>
        <span aria-disabled="true"><IconClock />Riwayat · segera</span>
        <span aria-disabled="true"><IconGear />Pengaturan · segera</span>
      </nav>
    </div>
  )
}
