import { ref } from 'vue'
import { dataUrl, fetchJson, fetchText } from '@/lib/dataClient'

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

async function loadIndex() {
  if (loaded) return
  loading.value = true
  error.value = null
  try {
    const index = await fetchJson<IndexEntry[]>('rapports/index.json')
    const metas: ReportMeta[] = []
    await Promise.all(
      index.map(async (entry) => {
        const content = await fetchText(`rapports/${entry.file}`)
        contentCache.set(entry.id, content)
        metas.push(parseMeta(entry.id, entry.file, content))
      }),
    )
    reports.value = metas.sort((a, b) => b.date.localeCompare(a.date))
    loaded = true
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erreur de chargement'
    reports.value = []
  } finally {
    loading.value = false
  }
}

export function useReports() {
  if (!loaded && !loading.value) {
    void loadIndex()
  }

  async function getReport(id: string): Promise<Report | undefined> {
    const normalized = id.replace(/\.md$/i, '')
    if (!loaded) await loadIndex()
    const meta = reports.value.find((r) => r.id === normalized)
    if (!meta) return undefined
    let content = contentCache.get(normalized)
    if (!content) {
      content = await fetchText(`rapports/${meta.file}`)
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
      loaded = false
      contentCache.clear()
      return loadIndex()
    },
  }
}

export function reportPath(id: string): string {
  return dataUrl(`rapports/${id.replace(/\.md$/i, '')}.md`)
}
