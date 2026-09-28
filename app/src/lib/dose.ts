/** Dosage comprimé × quantité prescrite (ex. 1,5 × 25 µg → 37,5 µg). */

const UNIT_ALIASES: Record<string, string> = {
  ug: 'µg',
  mcg: 'µg',
  microgramme: 'µg',
  microgrammes: 'µg',
  milligramme: 'mg',
  milligrammes: 'mg',
}

const FRACTIONS: Record<string, number> = {
  '½': 0.5,
  '1/2': 0.5,
  '¼': 0.25,
  '1/4': 0.25,
  '¾': 0.75,
  '3/4': 0.75,
}

const STRENGTH_RE =
  /(\d+(?:[.,]\d+)?)\s*(µg|ug|mcg|microgrammes?|mg|milligrammes?|g|ml|ui)\b/i

const QTY_RE =
  /(\d+[.,]\d+|\d+|½|¼|¾|1\/2|1\/4|3\/4)\s*(?:cp|compr(?:imé|ime)s?|gélules?|gelules?)?\b/gi

export interface DoseStrength {
  value: number
  unit: string
}

export function parseStrength(raw: string | null | undefined): DoseStrength | null {
  if (!raw) return null
  const m = raw.match(STRENGTH_RE)
  if (!m) return null
  const value = parseFloat(m[1].replace(',', '.'))
  if (Number.isNaN(value)) return null
  const key = m[2].toLowerCase()
  const unit = UNIT_ALIASES[key] ?? (key.startsWith('micro') ? 'µg' : key)
  return { value, unit }
}

function parseQtyToken(token: string): number | null {
  if (token in FRACTIONS) return FRACTIONS[token]
  const n = parseFloat(token.replace(',', '.'))
  return Number.isNaN(n) ? null : n
}

/** Nombre de comprimés / gélules dans une posologie (« 1.5 le matin », « 1,5 comprimé »). */
export function parseTabletQty(posology: string | null | undefined): number | null {
  if (!posology) return null
  const text = posology.replace(/\s+/g, ' ').trim()
  QTY_RE.lastIndex = 0
  let match: RegExpExecArray | null
  while ((match = QTY_RE.exec(text))) {
    const rest = text.slice(match.index + match[0].length).trim()
    if (/^(fois|mois|semaines?|jours?)\b/i.test(rest)) continue
    const qty = parseQtyToken(match[1])
    if (qty == null || qty <= 0) continue
    const before = text.slice(0, match.index)
    // Évite de reprendre le dosage du nom commercial (« 25 microgrammes »).
    if (STRENGTH_RE.test(match[0]) || /microgrammes?\s*$/i.test(before)) continue
    const unitAfter = rest.match(/^(µg|ug|mcg|microgrammes?|mg|milligrammes?|g|ml|ui)\b/i)
    if (unitAfter) continue
    return qty
  }
  return null
}

export function formatDose(value: number, unit: string): string {
  const rounded = Math.round(value * 1000) / 1000
  const formatted = Number.isInteger(rounded)
    ? String(rounded)
    : rounded.toLocaleString('fr-FR', { maximumFractionDigits: 3, minimumFractionDigits: 0 })
  return `${formatted} ${unit}`
}

export interface EffectiveDose {
  label: string
  strength: DoseStrength | null
  quantity: number | null
  multiplied: boolean
}

export function resolveEffectiveDose(
  dose: string | null | undefined,
  posology: string | null | undefined,
): EffectiveDose {
  const strength = parseStrength(dose)
  const quantity = parseTabletQty(posology)
  if (!strength) {
    return { label: (dose || '').trim(), strength: null, quantity, multiplied: false }
  }
  if (quantity == null || quantity === 1) {
    return {
      label: formatDose(strength.value, strength.unit),
      strength,
      quantity,
      multiplied: false,
    }
  }
  return {
    label: formatDose(strength.value * quantity, strength.unit),
    strength,
    quantity,
    multiplied: true,
  }
}

export function formatQty(qty: number): string {
  const rounded = Math.round(qty * 1000) / 1000
  if (Number.isInteger(rounded)) return String(rounded)
  return rounded.toLocaleString('fr-FR', { maximumFractionDigits: 3, minimumFractionDigits: 0 })
}
