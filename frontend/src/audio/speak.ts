// Mimo's voice. shortcut: browser speechSynthesis until B3 pre-generated OpenAI audio;
// voice quality depends on the device. Callers only rely on speak()/cancelSpeech().

let preferred: SpeechSynthesisVoice | null = null

function pickVoice(): SpeechSynthesisVoice | null {
  const voices = speechSynthesis.getVoices()
  return voices.find((v) => v.lang === 'en-GB') ?? voices.find((v) => v.lang.startsWith('en')) ?? null
}

export function speak(text: string): Promise<void> {
  if (typeof speechSynthesis === 'undefined') return new Promise((r) => setTimeout(r, text.length * 60))
  return new Promise((resolve) => {
    preferred ??= pickVoice()
    const u = new SpeechSynthesisUtterance(text)
    u.lang = 'en-GB'
    u.rate = 0.95
    if (preferred) u.voice = preferred
    // Some browsers never fire onend for a cancelled or blocked utterance; cap the wait.
    const timer = setTimeout(resolve, 2000 + text.length * 120)
    u.onend = u.onerror = () => { clearTimeout(timer); resolve() }
    speechSynthesis.speak(u)
  })
}

// Call synchronously inside a click handler: iOS Safari blocks later speak() calls otherwise.
export function unlockSpeech() {
  if (typeof speechSynthesis !== 'undefined') speechSynthesis.speak(new SpeechSynthesisUtterance(''))
}

export function cancelSpeech() {
  if (typeof speechSynthesis !== 'undefined') speechSynthesis.cancel()
}
