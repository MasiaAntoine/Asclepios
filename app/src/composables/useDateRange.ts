import { computed, ref, type Ref } from 'vue'

export type DateRangePreset = 'all' | '1y' | '6m' | '3m' | '1m' | 'custom'

export interface DateRangeBounds {
  from: Date | null
  to: Date | null
}

export const DATE_RANGE_PRESETS: { id: DateRangePreset; label: string }[] = [
  { id: 'all', label: 'Tout' },
  { id: '1y', label: '1 an' },
  { id: '6m', label: '6 mois' },
  { id: '3m', label: '3 mois' },
  { id: '1m', label: '1 mois' },
  { id: 'custom', label: 'Perso' },
]

function startOfDay(d: Date): Date {
  const x = new Date(d)
  x.setHours(0, 0, 0, 0)
  return x
}

function endOfDay(d: Date): Date {
  const x = new Date(d)
  x.setHours(23, 59, 59, 999)
  return x
}

function monthsAgo(n: number): Date {
  const d = new Date()
  d.setMonth(d.getMonth() - n)
  return startOfDay(d)
}

function toInputValue(d: Date | null): string {
  if (!d) return ''
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function fromInputValue(s: string): Date | null {
  if (!s) return null
  const [y, m, d] = s.split('-').map(Number)
  if (!y || !m || !d) return null
  return startOfDay(new Date(y, m - 1, d))
}

export function useDateRange(anchorMax?: Ref<Date | null | undefined>) {
  const preset = ref<DateRangePreset>('all')
  const customFrom = ref('')
  const customTo = ref('')

  const bounds = computed((): DateRangeBounds => {
    const now = endOfDay(new Date())
    const maxDate = anchorMax?.value ? endOfDay(anchorMax.value) : now

    switch (preset.value) {
      case '1m':
        return { from: monthsAgo(1), to: maxDate }
      case '3m':
        return { from: monthsAgo(3), to: maxDate }
      case '6m':
        return { from: monthsAgo(6), to: maxDate }
      case '1y':
        return { from: monthsAgo(12), to: maxDate }
      case 'custom': {
        const from = fromInputValue(customFrom.value)
        const to = fromInputValue(customTo.value)
        return {
          from,
          to: to ? endOfDay(to) : null,
        }
      }
      case 'all':
      default:
        return { from: null, to: null }
    }
  })

  function inRange(date: Date): boolean {
    const { from, to } = bounds.value
    const t = date.getTime()
    if (from && t < from.getTime()) return false
    if (to && t > to.getTime()) return false
    return true
  }

  function setPreset(id: DateRangePreset) {
    preset.value = id
    if (id === 'custom' && !customFrom.value && !customTo.value) {
      // seed custom with last year → today for convenience
      customFrom.value = toInputValue(monthsAgo(12))
      customTo.value = toInputValue(new Date())
    }
  }

  return {
    preset,
    customFrom,
    customTo,
    bounds,
    inRange,
    setPreset,
    toInputValue,
    fromInputValue,
  }
}

export function filterByDateRange<T extends { dateObj: Date }>(
  items: T[],
  inRange: (d: Date) => boolean,
): T[] {
  return items.filter((i) => inRange(i.dateObj))
}
