import { formatNotifyAt } from '@/lib/sport'

export const POIDS_WEEKDAYS = [
  { value: 0, label: 'Lundi' },
  { value: 1, label: 'Mardi' },
  { value: 2, label: 'Mercredi' },
  { value: 3, label: 'Jeudi' },
  { value: 4, label: 'Vendredi' },
  { value: 5, label: 'Samedi' },
  { value: 6, label: 'Dimanche' },
] as const

export function formatPoidsNotify(
  weekday: number | null | undefined,
  at: string | null | undefined,
): string {
  const time = formatNotifyAt(at)
  if (!time) return ''
  const day =
    weekday != null && weekday >= 0 && weekday < POIDS_WEEKDAYS.length
      ? POIDS_WEEKDAYS[weekday].label.toLowerCase()
      : ''
  return day ? `${day} ${time}` : time
}
