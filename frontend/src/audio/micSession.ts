// The mic opened on the mic-check screen is reused by the practice room (no second permission prompt).
import type { Mic } from './mic'

export const micSession: { mic: Mic | null; threshold: number } = { mic: null, threshold: 0.02 }
