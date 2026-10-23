// Microphone access, live level, and per-answer recording. Works in Chrome and Safari:
// both need a user gesture to start, Safari records audio/mp4 while Chrome records webm/opus.

const MIME_PREFERENCE = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/webm']

export function pickMime(): string {
  if (typeof MediaRecorder === 'undefined') return ''
  return MIME_PREFERENCE.find((m) => MediaRecorder.isTypeSupported(m)) ?? ''
}

export function micErrorMessage(err: unknown): string {
  const name = (err as { name?: string })?.name
  switch (name) {
    case 'NotAllowedError':
      return 'Izin mikrofon ditolak. Izinkan mikrofon untuk situs ini, lalu coba lagi.'
    case 'NotFoundError':
    case 'OverconstrainedError':
      return 'Mikrofon tidak ditemukan. Sambungkan mikrofon atau headset, lalu coba lagi.'
    case 'NotReadableError':
      return 'Mikrofon sedang dipakai aplikasi lain. Tutup aplikasi tersebut, lalu coba lagi.'
    case 'SecurityError':
      return 'Mikrofon hanya bisa dipakai lewat HTTPS atau localhost.'
    default:
      return 'Mikrofon belum bisa dipakai. Muat ulang halaman, lalu coba lagi.'
  }
}

export interface Mic {
  stream: MediaStream
  level(): number            // RMS of the latest audio frame, 0..1
  close(): void
}

type WebkitWindow = Window & { webkitAudioContext?: typeof AudioContext }

// Must be called from a click/tap handler (Safari only resumes AudioContext inside a gesture).
export async function openMic(deviceId?: string): Promise<Mic> {
  if (!navigator.mediaDevices?.getUserMedia) throw Object.assign(new Error('insecure'), { name: 'SecurityError' })
  // Safari only unlocks audio inside the gesture itself, so the context is created and resumed
  // before the first await (getUserMedia ends the synchronous part of the click handler).
  const Ctx = window.AudioContext ?? (window as WebkitWindow).webkitAudioContext!
  const ctx = new Ctx()
  void ctx.resume()
  let stream: MediaStream
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: deviceId ? { deviceId: { exact: deviceId } } : true })
  } catch (e) {
    void ctx.close()
    throw e
  }
  const analyser = ctx.createAnalyser()
  analyser.fftSize = 1024
  ctx.createMediaStreamSource(stream).connect(analyser)
  const buf = new Float32Array(analyser.fftSize)
  return {
    stream,
    level() {
      analyser.getFloatTimeDomainData(buf)
      let sum = 0
      for (const v of buf) sum += v * v
      return Math.sqrt(sum / buf.length)
    },
    close() {
      stream.getTracks().forEach((t) => t.stop())
      void ctx.close()
    },
  }
}

export interface Recording {
  stop(): Promise<{ blob: Blob; durationMs: number }>
}

export function startRecording(stream: MediaStream): Recording {
  const mime = pickMime()
  const rec = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined)
  const chunks: Blob[] = []
  rec.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data) }
  const started = performance.now()
  rec.start()
  return {
    stop: () => new Promise((resolve) => {
      const durationMs = performance.now() - started
      rec.onstop = () => resolve({ blob: new Blob(chunks, { type: rec.mimeType || mime || 'audio/webm' }), durationMs })
      rec.state === 'inactive' ? rec.onstop(new Event('stop')) : rec.stop()
    }),
  }
}

export async function listMics(): Promise<MediaDeviceInfo[]> {
  // labels are only filled in after permission was granted
  return (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === 'audioinput')
}
