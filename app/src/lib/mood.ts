import type { EmotionId } from '@/lib/emotions'

export type MoodSlotId = 'matin' | 'midi' | 'apres-midi' | 'soir'

export const MOOD_SLOTS: {
  id: MoodSlotId
  hour: number
  minute: number
  label: string
  prompt: string
}[] = [
  { id: 'matin', hour: 8, minute: 30, label: 'Matin', prompt: 'ce matin' },
  { id: 'midi', hour: 12, minute: 30, label: 'Midi', prompt: 'en ce moment' },
  { id: 'apres-midi', hour: 16, minute: 30, label: 'Après-midi', prompt: 'cet après-midi' },
  { id: 'soir', hour: 20, minute: 30, label: 'Soir', prompt: 'ce soir' },
]

/** Pas de nouvelle demande si une note a déjà été posée récemment. */
export const MIN_MOOD_GAP_MINUTES = 120

const DATE_ONLY = /^(\d{4})-(\d{2})-(\d{2})$/

export function todayIso(now = new Date()): string {
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

export function parseIsoDate(iso: string): Date | null {
  const m = iso.match(DATE_ONLY)
  if (!m) return null
  const date = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
  return Number.isNaN(date.getTime()) ? null : date
}

/** Anciennes lignes `YYYY-MM-DD` → 20:00 locale ; sinon ISO datetime. */
export function parseMoodAt(raw: string): Date | null {
  const value = raw.trim()
  if (!value) return null
  const day = parseIsoDate(value)
  if (day) {
    day.setHours(20, 30, 0, 0)
    return day
  }
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

export function toIsoWithOffset(date: Date): string {
  const pad = (n: number) => String(Math.trunc(n)).padStart(2, '0')
  const y = date.getFullYear()
  const m = pad(date.getMonth() + 1)
  const d = pad(date.getDate())
  const h = pad(date.getHours())
  const min = pad(date.getMinutes())
  const offset = -date.getTimezoneOffset()
  const sign = offset >= 0 ? '+' : '-'
  const oh = pad(Math.floor(Math.abs(offset) / 60))
  const om = pad(Math.abs(offset) % 60)
  return `${y}-${m}-${d}T${h}:${min}${sign}${oh}:${om}`
}

export function toDatetimeLocalValue(date: Date): string {
  const p = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${p(date.getMonth() + 1)}-${p(date.getDate())}T${p(date.getHours())}:${p(date.getMinutes())}`
}

export function fromDatetimeLocalValue(value: string): Date | null {
  if (!value) return null
  const date = new Date(value)
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

export function formatMoodDateTime(date: Date): string {
  return date.toLocaleString('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatMoodTime(date: Date): string {
  return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
}

export function slotAt(now = new Date()): MoodSlotId | null {
  const minutes = now.getHours() * 60 + now.getMinutes()
  let current: MoodSlotId | null = null
  for (const slot of MOOD_SLOTS) {
    if (minutes >= slot.hour * 60 + slot.minute) current = slot.id
    else break
  }
  return current
}

export function slotMeta(id: MoodSlotId | null) {
  if (!id) return null
  return MOOD_SLOTS.find((s) => s.id === id) ?? null
}

export function slotStart(slotId: MoodSlotId, day = new Date()): Date {
  const slot = MOOD_SLOTS.find((s) => s.id === slotId) ?? MOOD_SLOTS[0]
  const date = new Date(day)
  date.setHours(slot.hour, slot.minute, 0, 0)
  return date
}

export function nextSlot(now = new Date()): { id: MoodSlotId; at: Date } | null {
  const minutes = now.getHours() * 60 + now.getMinutes()
  for (const slot of MOOD_SLOTS) {
    if (minutes < slot.hour * 60 + slot.minute) {
      return { id: slot.id, at: slotStart(slot.id, now) }
    }
  }
  return null
}

export function isMoodSlotId(value: string): value is MoodSlotId {
  return MOOD_SLOTS.some((s) => s.id === value)
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
