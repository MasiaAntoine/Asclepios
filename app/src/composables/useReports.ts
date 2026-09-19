import { ref } from 'vue'
import { dataUrl, fetchJson, fetchText } from '@/lib/dataClient'
import { VAULT, rapportFile } from '@/lib/vault'

export interface ReportMeta {
  id: string
  file: string
  title: string
  date: string
  excerpt: string
  tags: string[]
}

export interface Report extends ReportMeta {
  content: string
}

interface IndexEntry {
  id: string
  file: string
}

function isNoiseLine(line: string): boolean {
  const t = line.trim()
  if (!t) return true
  if (t.startsWith('#')) return true
  if (t.startsWith('|')) return true
  if (/^[-*|_\s]+$/.test(t)) return true
  if (t === '---' || t === '***') return true
  return false
}

function stripMarkdown(text: string): string {
  return text
    .replace(/^>\s?/, '')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/[*_`>#]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function extractThemes(lines: string[]): string[] {
  for (const line of lines) {
    const match = line.match(/\|\s*\*\*Thèmes?\*\*\s*\|\s*(.+?)\s*\|?\s*$/i)
    if (match) {
      return match[1]
        .split(/[,;/]/)
        .map((t) => t.replace(/[*_]/g, '').trim())
        .filter((t) => t.length > 1)
    }
  }
  return []
}

function parseMeta(id: string, file: string, content: string): ReportMeta {
  const lines = content.split('\n')
  const titleLine = lines.find((l) => l.startsWith('# '))
  const title = titleLine ? titleLine.replace(/^#\s+/, '').trim() : id
  const dateMatch = id.match(/^(\d{4}-\d{2}-\d{2})/)
  const date = dateMatch ? dateMatch[1] : ''
  const proseLine = lines.find((l) => !isNoiseLine(l))
  const excerpt = proseLine ? stripMarkdown(proseLine).slice(0, 200) : ''
  return {
    id,
    file,
    title,
    date,
    excerpt,
    tags: extractThemes(lines),
  }
}

const reports = ref<ReportMeta[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const contentCache = new Map<string, string>()
let loaded = false
let loadPromise: Promise<void> | null = null
let loadGeneration = 0

async function loadIndex(force = false) {
  if (!force && loaded) return
  if (!force && loadPromise) return loadPromise

  loaded = false
  loading.value = true
  error.value = null
  const generation = ++loadGeneration

  const run = (async () => {
    const index = await fetchJson<IndexEntry[]>(VAULT.rapportsIndex)
    const metas: ReportMeta[] = []
    await Promise.all(
      index.map(async (entry) => {
        const content = await fetchText(rapportFile(entry.file))
        contentCache.set(entry.id, content)
        metas.push(parseMeta(entry.id, entry.file, content))
      }),
    )
    if (generation !== loadGeneration) return
    reports.value = metas.sort((a, b) => b.date.localeCompare(a.date))
    loaded = true
  })()

  loadPromise = run
  try {
    await run
  } catch (e) {
    if (generation === loadGeneration) {
      error.value = e instanceof Error ? e.message : 'Erreur de chargement'
      reports.value = []
      loaded = false
    }
  } finally {
    if (loadPromise === run) {
      loadPromise = null
      loading.value = false
    }
  }
}

async function fetchReportFile(id: string): Promise<Report | undefined> {
  const file = `${id}.md`
  try {
    const content = await fetchText(rapportFile(file))
    const meta = parseMeta(id, file, content)
    contentCache.set(id, content)
    if (!reports.value.some((r) => r.id === id)) {
      reports.value = [...reports.value, meta].sort((a, b) => b.date.localeCompare(a.date))
    }
    return { ...meta, content }
  } catch {
    return undefined
  }
}

export function useReports() {
  if (!loaded && !loading.value) {
    void loadIndex()
  }

  async function getReport(id: string): Promise<Report | undefined> {
    const normalized = id.replace(/\.md$/i, '')
    if (!loaded) await loadIndex()
    let meta = reports.value.find((r) => r.id === normalized)
    if (!meta) {
      await loadIndex(true)
      meta = reports.value.find((r) => r.id === normalized)
    }
    if (!meta) return fetchReportFile(normalized)
    let content = contentCache.get(normalized)
    if (!content) {
      content = await fetchText(rapportFile(meta.file))
      contentCache.set(normalized, content)
    }
    return { ...meta, content }
  }

  function getReportSync(id: string): Report | undefined {
    const normalized = id.replace(/\.md$/i, '')
    const meta = reports.value.find((r) => r.id === normalized)
    const content = contentCache.get(normalized)
    if (!meta || content == null) return undefined
    return { ...meta, content }
  }

  return {
    reports,
    loading,
    error,
    loadIndex,
    getReport,
    getReportSync,
    reload: () => {
      contentCache.clear()
      return loadIndex(true)
    },
  }
}

export function reportPath(id: string): string {
  return dataUrl(rapportFile(`${id.replace(/\.md$/i, '')}.md`))
}
