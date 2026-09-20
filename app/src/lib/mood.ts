import type { EmotionId } from '@/lib/emotions'

export function todayIso(now = new Date()): string {
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

export function parseIsoDate(iso: string): Date | null {
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (!m) return null
  const date = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatMoodDate(iso: string): string {
  const date = parseIsoDate(iso)
  if (!date) return iso
  return date.toLocaleDateString('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  })
}

export function moodLabel(score: number): string {
  const labels = [
    'Au plus bas',
    'Très mal',
    'Mal',
    'Plutôt mal',
    'Moyen −',
    'Moyen',
    'Correct',
    'Bien',
    'Très bien',
    'Excellent',
    'Super bien',
  ]
  return labels[score] ?? ''
}

export function moodColor(score: number): string {
  const stops = [
    '#D4524A',
    '#DC6A45',
    '#E07A3D',
    '#E49A3A',
    '#E8B923',
    '#C4B43A',
    '#8FBA5C',
    '#5AAD78',
    '#3D9B6E',
    '#2BB89A',
    '#1FA888',
  ]
  return stops[Math.min(10, Math.max(0, score))] ?? '#2BB89A'
}

export function moodOwl(score: number): EmotionId {
  if (score <= 1) return 'tristesse'
  if (score <= 3) return 'anxiete'
  if (score <= 5) return 'fatigue'
  if (score <= 6) return 'calme'
  if (score <= 8) return 'soulagement'
  if (score === 9) return 'espoir'
  return 'joie'
}
