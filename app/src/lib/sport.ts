export interface SportExercise {
  id: string
  name: string
  sets: number
  reps: number | null
  seconds: number | null
  note: string
}

export interface SportCatalogItem {
  name: string
  sets: number
  reps?: number
  seconds?: number
}

export const EXERCISE_CATALOG: SportCatalogItem[] = [
  { name: 'Pompes', sets: 3, reps: 10 },
  { name: 'Squats', sets: 3, reps: 15 },
  { name: 'Gainage', sets: 3, seconds: 30 },
  { name: 'Fentes', sets: 3, reps: 12 },
  { name: 'Pont fessier', sets: 3, reps: 12 },
  { name: 'Dips', sets: 3, reps: 8 },
  { name: 'Tractions', sets: 3, reps: 5 },
  { name: 'Burpees', sets: 3, reps: 8 },
  { name: 'Mountain climbers', sets: 3, reps: 20 },
  { name: 'Jumping jacks', sets: 3, reps: 30 },
  { name: 'Crunchs', sets: 3, reps: 15 },
  { name: 'Planche latérale', sets: 3, seconds: 20 },
  { name: 'Mollets', sets: 3, reps: 20 },
]

export function formatPrescription(exo: {
  sets: number
  reps?: number | null
  seconds?: number | null
}): string {
  if (exo.seconds) return `${exo.sets} × ${exo.seconds} s`
  if (exo.reps) return `${exo.sets} × ${exo.reps}`
  return `${exo.sets} série${exo.sets > 1 ? 's' : ''}`
}

export function formatNotifyAt(value: string | null | undefined): string {
  const raw = (value || '').trim()
  if (!raw) return ''
  const [h, m] = raw.split(':')
  if (!h || !m) return raw
  return `${h}h${m}`
}

export function isNotifyAt(value: string): boolean {
  return /^([01]\d|2[0-3]):[0-5]\d$/.test(value.trim())
}
