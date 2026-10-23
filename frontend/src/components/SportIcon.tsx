import type { Sport } from '../lib/types'

/** Small hand-drawn sport glyphs (stroke icons, currentColor). */
export function SportIcon({ sport, className = 'h-5 w-5' }: { sport: Sport; className?: string }) {
  const p = { className, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.6, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, 'aria-hidden': true }
  if (sport === 'cricket')
    return (<svg {...p}><path d="M14.5 3.5l6 6-9 9a2 2 0 01-2.8 0l-3.2-3.2a2 2 0 010-2.8z" /><path d="M5 19l-2 2" /><circle cx="19" cy="18" r="2.2" /></svg>)
  if (sport === 'football')
    return (<svg {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7.5l3.8 2.8-1.4 4.4H9.6l-1.4-4.4z" /><path d="M12 7.5V3.2M15.8 10.3l4-1.3M14.4 14.7l2.5 3.5M9.6 14.7l-2.5 3.5M8.2 10.3l-4-1.3" /></svg>)
  return (<svg {...p}><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3v18" /><path d="M5.6 5.6c3.2 3.2 3.2 9.6 0 12.8M18.4 5.6c-3.2 3.2-3.2 9.6 0 12.8" /></svg>)
}

export const SPORT_ACCENT: Record<Sport, string> = { cricket: '#86C061', football: '#5CC8E8', basketball: '#F0A04B' }
