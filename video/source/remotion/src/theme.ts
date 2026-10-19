// Bluefin video: the app's own palette (deep-space panels, neon blue, a light shell) and type.
export const C = {
  bg0: '#050914',
  bg1: '#0A1022',
  panel: '#0E1324',
  panel2: '#161C30',
  rim: 'rgba(77,163,255,0.28)',
  grid: 'rgba(77,163,255,0.08)',
  text: '#E8EEFF',
  muted: '#8E9AC0',
  dim: '#5A6378',
  neon: '#4DA3FF',
  blue: '#007AFF',
  blue2: '#1F7BEA',
  shell: '#EEF0F4',
  ink: '#1D1D1F',
  green: '#3DDC97',
  red: '#FF5C5C',
  amber: '#FFC24D',
  purple: '#C792EA',
  white: '#FFFFFF',
};

export const STEP = {
  sense: { n: 1, label: 'SENSE', color: C.neon },
  plan: { n: 2, label: 'PLAN', color: C.amber },
  act: { n: 3, label: 'ACT', color: C.green },
  prove: { n: 4, label: 'PROVE', color: C.purple },
} as const;

export const F = {
  sans: "'Inter', 'Segoe UI', Arial, sans-serif",
  serif: "'Instrument Serif', Georgia, serif",
  bn: "'Noto Sans Bengali', 'Nirmala UI', sans-serif",
};

export const W = 1920;
export const H = 1080;
