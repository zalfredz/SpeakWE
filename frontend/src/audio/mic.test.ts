import { describe, expect, it } from 'vitest'
import { micErrorMessage } from './mic'

const err = (name: string) => Object.assign(new Error(name), { name })

describe('micErrorMessage', () => {
  it('explains a denied permission', () => expect(micErrorMessage(err('NotAllowedError'))).toMatch(/izin/i))
  it('explains a missing microphone', () => expect(micErrorMessage(err('NotFoundError'))).toMatch(/tidak ditemukan/i))
  it('explains a busy microphone', () => expect(micErrorMessage(err('NotReadableError'))).toMatch(/aplikasi lain/i))
  it('explains the HTTPS requirement', () => expect(micErrorMessage(err('SecurityError'))).toMatch(/HTTPS/))
  it('falls back to a generic message', () => expect(micErrorMessage(new Error('boom'))).toMatch(/mikrofon/i))
})
