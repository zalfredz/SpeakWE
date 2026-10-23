import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api'
import { clampDuration, formatDuration, withRetry } from './retry'

const netErr = () => new TypeError('Failed to fetch')

describe('withRetry', () => {
  it('retries once on a network error without asking the user', async () => {
    const fn = vi.fn().mockRejectedValueOnce(netErr()).mockResolvedValueOnce('ok')
    const wait = vi.fn()
    await expect(withRetry(fn, wait)).resolves.toBe('ok')
    expect(fn).toHaveBeenCalledTimes(2)
    expect(wait).not.toHaveBeenCalled()
  })

  it('after the automatic retry fails, waits for the user and then succeeds (upload_failed keeps the answer)', async () => {
    const fn = vi.fn().mockRejectedValueOnce(netErr()).mockRejectedValueOnce(new ApiError(503, 'http_error', '')).mockResolvedValueOnce('ok')
    const wait = vi.fn().mockResolvedValue(undefined)
    await expect(withRetry(fn, wait)).resolves.toBe('ok')
    expect(wait).toHaveBeenCalledTimes(1)
    expect(fn).toHaveBeenCalledTimes(3)
  })

  it('a 4xx answer from the server is not retried', async () => {
    const fn = vi.fn().mockRejectedValue(new ApiError(409, 'not_active', ''))
    const wait = vi.fn()
    await expect(withRetry(fn, wait)).rejects.toMatchObject({ code: 'not_active' })
    expect(fn).toHaveBeenCalledTimes(1)
    expect(wait).not.toHaveBeenCalled()
  })
})

describe('durations', () => {
  it('clamps a recording to the step limit so a delayed timer cannot cause over_limit', () => {
    expect(clampDuration(63500, 60)).toBe(60000)
    expect(clampDuration(12000, 60)).toBe(12000)
  })

  it('formats milliseconds as m:ss with rounding to whole seconds', () => {
    expect(formatDuration(59600)).toBe('1:00')
    expect(formatDuration(125400)).toBe('2:05')
    expect(formatDuration(0)).toBe('0:00')
  })
})
