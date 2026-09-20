export const EMOTION_IDS = [
  'joie',
  'tristesse',
  'anxiete',
  'colere',
  'calme',
  'espoir',
  'fatigue',
  'soulagement',
] as const

export type EmotionId = (typeof EMOTION_IDS)[number]

export interface EmotionDef {
  id: EmotionId
  label: string
  color: string
}

export const EMOTIONS: EmotionDef[] = [
  { id: 'joie', label: 'Joie', color: '#E8B923' },
  { id: 'tristesse', label: 'Tristesse', color: '#5B8EC8' },
  { id: 'anxiete', label: 'Anxiété', color: '#E07A3D' },
  { id: 'colere', label: 'Colère', color: '#D4524A' },
  { id: 'calme', label: 'Calme', color: '#2BB89A' },
  { id: 'espoir', label: 'Espoir', color: '#3D9B6E' },
  { id: 'fatigue', label: 'Fatigue', color: '#8B7BB5' },
  { id: 'soulagement', label: 'Soulagement', color: '#4CA89A' },
]

const BY_ID = Object.fromEntries(EMOTIONS.map((e) => [e.id, e])) as Record<
  EmotionId,
  EmotionDef
>

export function isEmotionId(value: string): value is EmotionId {
  return (EMOTION_IDS as readonly string[]).includes(value)
}

export function emotionDef(id: string): EmotionDef | undefined {
  return isEmotionId(id) ? BY_ID[id] : undefined
}

export function normalizeEmotionIds(ids: string[] | undefined | null): EmotionId[] {
  const seen = new Set<EmotionId>()
  const out: EmotionId[] = []
  for (const raw of ids ?? []) {
    if (isEmotionId(raw) && !seen.has(raw)) {
      seen.add(raw)
      out.push(raw)
    }
  }
  return out
}
