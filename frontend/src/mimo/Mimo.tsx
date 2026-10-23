import { useEffect, useRef } from 'react'
import './mimo-fullbody-engine.js'
import type { MimoState } from './engine'

interface Props {
  state: MimoState
  width: number
  label: string
  onTap?: () => void
  tapLabel?: string
}

// Canvas wrapper around the Mimo engine. The engine eases between states itself,
// so this only feeds it time and the latest state.
export default function Mimo({ state, width, label, onTap, tapLabel }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const stateRef = useRef(state)
  stateRef.current = state

  useEffect(() => {
    const canvas = canvasRef.current!
    // no background: the canvas stays transparent so Mimo sits on the light or dark page ground
    const renderer = window.MimoFullBody.create(canvas)
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches
    let frame = 0, last: number | null = null, clock = 0, drawn: MimoState | null = null
    const tick = (now: number) => {
      frame = requestAnimationFrame(tick)
      const s = stateRef.current
      if (reduce) {
        if (drawn !== s) { renderer.render(0, s, 0, true); drawn = s }
        return
      }
      const dt = last === null ? 0 : Math.min(Math.max((now - last) / 1000, 0), 0.05)
      last = now
      clock += dt
      renderer.render(clock, s, dt, drawn === null)
      drawn = s
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [])

  // Always the same wrapper element: swapping canvas ↔ button would remount the canvas
  // while the engine keeps drawing to the old, detached one (Mimo would go blank).
  return (
    <div role={onTap ? 'button' : 'img'} tabIndex={onTap ? 0 : undefined} className={onTap ? 'mimo-btn' : undefined}
      aria-label={onTap ? `${label}. ${tapLabel ?? ''}`.trim() : label}
      onClick={onTap}
      onKeyDown={onTap ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onTap() } } : undefined}>
      <canvas ref={canvasRef} width={1200} height={1000} className="mimo-canvas" aria-hidden="true"
        style={{ width, height: (width * 5) / 6 }} />
    </div>
  )
}
