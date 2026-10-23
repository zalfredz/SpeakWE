// @vitest-environment jsdom
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, describe, expect, it } from 'vitest'
import Mimo from './Mimo'

;(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true
window.matchMedia = (() => ({ matches: false })) as unknown as typeof window.matchMedia
window.MimoFullBody = { create: () => ({ render: () => undefined }) }

let host: HTMLDivElement
afterEach(() => host?.remove())

describe('Mimo', () => {
  it('keeps the same canvas when it becomes tappable, so the engine keeps drawing to the visible node', () => {
    host = document.body.appendChild(document.createElement('div'))
    const root = createRoot(host)
    act(() => root.render(<Mimo state="speaking" width={300} label="Mimo" />))
    const before = host.querySelector('canvas')
    act(() => root.render(<Mimo state="listening" width={300} label="Mimo" onTap={() => undefined} />))
    expect(host.querySelector('canvas')).toBe(before)
    act(() => root.unmount())
  })
})
