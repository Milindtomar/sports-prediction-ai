import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { EmptyState, ErrorState, Segmented } from '../components/ui'
import { ApiError, api } from '../lib/api'
import { cn, pct, pp } from '../lib/format'
import Landing from '../pages/Landing'

afterEach(() => { vi.restoreAllMocks() })

describe('format helpers', () => {
  it('formats probabilities and signed percentage points', () => {
    expect(pct(0.456)).toBe('46%')
    expect(pct(0.456, 1)).toBe('45.6%')
    expect(pp(3.14)).toBe('+3.1 pp')
    expect(pp(-2)).toBe('−2.0 pp')
    expect(cn('a', false, null, 'b')).toBe('a b')
  })
})

describe('shared UI states', () => {
  it('ErrorState shows the message and retries', () => {
    const retry = vi.fn()
    render(<ErrorState error={new Error('Backend unreachable')} onRetry={retry} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Backend unreachable')
    fireEvent.click(screen.getByRole('button', { name: /retry/i }))
    expect(retry).toHaveBeenCalledOnce()
  })
  it('EmptyState explains what to do', () => {
    render(<EmptyState title="No data yet" hint="Run the study first" />)
    expect(screen.getByText('No data yet')).toBeInTheDocument()
    expect(screen.getByText('Run the study first')).toBeInTheDocument()
  })
  it('Segmented marks the selected tab and reports changes', () => {
    const on = vi.fn()
    render(<Segmented label="View" value="a" onChange={on} options={[{ value: 'a', label: 'A' }, { value: 'b', label: 'B' }]} />)
    expect(screen.getByRole('tab', { name: 'A' })).toHaveAttribute('aria-selected', 'true')
    fireEvent.click(screen.getByRole('tab', { name: 'B' }))
    expect(on).toHaveBeenCalledWith('b')
  })
})

describe('Landing live what-if', () => {
  const analysis = { state: { target: 150, runs: 90 }, headline: { label: 'Team X', prob: 0.4 }, scoreboard: { status: 'Chase', teams: [{ name: 'X', score: '90/3' }] } }
  it('degrades gracefully when the API is down', async () => {
    vi.spyOn(api, 'defaultState').mockRejectedValue(new ApiError(0, 'network', 'down'))
    vi.spyOn(api, 'meta').mockRejectedValue(new ApiError(0, 'network', 'down'))
    render(<MemoryRouter><Landing /></MemoryRouter>)
    expect(await screen.findByText(/needs the API running/i)).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
  })
  it('re-runs the simulation endpoint when an event is chosen', async () => {
    vi.spyOn(api, 'defaultState').mockResolvedValue({})
    vi.spyOn(api, 'meta').mockResolvedValue({ events: [{ id: 'six', label: 'SIX' }] } as any)
    vi.spyOn(api, 'predict').mockResolvedValue(analysis as any)
    const sim = vi.spyOn(api, 'simulate').mockResolvedValue({ focus_class: 1, applied: [{ label: 'SIX' }], deltas: { 1: { before: 0.4, after: 0.47, delta_pp: 7, label: 'Team X' } } } as any)
    render(<MemoryRouter><Landing /></MemoryRouter>)
    fireEvent.click(await screen.findByRole('button', { name: 'SIX' }))
    await waitFor(() => expect(sim).toHaveBeenCalled())
    expect(await screen.findByText('47%')).toBeInTheDocument()
  })
})
