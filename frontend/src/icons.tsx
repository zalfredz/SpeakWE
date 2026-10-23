// Inline stroke icons (decorative unless the parent labels them).
const base = {
  width: 22, height: 22, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2,
  strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, 'aria-hidden': true,
}

export const IconBack = () => <svg {...base}><path d="M15 18l-6-6 6-6" /></svg>
export const IconClose = () => <svg {...base} width={18} height={18} strokeWidth={2.2}><path d="M6 6l12 12M18 6L6 18" /></svg>
export const IconMic = () => <svg {...base} width={20} height={20}><rect x="9" y="2" width="6" height="12" rx="3" /><path d="M5 10a7 7 0 0 0 14 0M12 17v4" /></svg>
export const IconHome = () => <svg {...base}><path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" /></svg>
export const IconClock = () => <svg {...base}><path d="M12 8v4l3 2" /><circle cx="12" cy="12" r="9" /></svg>
export const IconGear = () => <svg {...base}><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1" /></svg>
export const IconCalendar = () => <svg {...base}><rect x="3" y="4" width="18" height="17" rx="3" /><path d="M3 9h18M8 2v4M16 2v4" /></svg>
export const IconCheck = () => <svg {...base} width={18} height={18} strokeWidth={2.5}><path d="M5 12l5 5 9-10" /></svg>
export const IconInfo = () => <svg {...base} width={18} height={18}><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></svg>
export const IconFlame = () => <svg {...base} width={16} height={16}><path d="M12 3c1 3 4 5 4 9a4 4 0 0 1-8 0c0-2 1-3 2-4 0 2 1 3 2 3 0-3-1-5 0-8z" /></svg>
