// Types for the canvas engine (mimo-fullbody-engine.js), which installs window.MimoFullBody.
export type MimoState = 'ready' | 'listening' | 'speaking' | 'thinking' | 'encourage' | 'success' | 'sleepy' | 'wrapup'
export interface MimoRenderer { render(t: number, state: MimoState, dt?: number, immediate?: boolean): unknown }
declare global {
  interface Window {
    MimoFullBody: { create(canvas: HTMLCanvasElement, options?: { background?: string; headScale?: [number, number] }): MimoRenderer }
  }
}
