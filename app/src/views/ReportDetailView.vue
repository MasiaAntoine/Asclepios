<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { marked, type Tokens } from 'marked'
import { useReports } from '@/composables/useReports'
import { ArrowLeft, Calendar, FileText, List, Tag } from '@lucide/vue'
import PdfButton from '@/components/PdfButton.vue'

interface TocItem {
  id: string
  text: string
  level: number
}

const route = useRoute()
const router = useRouter()
const { getReport, getReportSync, loading: reportsLoading } = useReports()

const reportId = computed(() => {
  const raw = route.params.slug as string
  return raw.replace(/\.md$/i, '')
})

const report = ref<Awaited<ReturnType<typeof getReport>>>(undefined)
const reportLoading = ref(false)

async function loadReport(id: string) {
  reportLoading.value = true
  try {
    report.value = getReportSync(id) ?? (await getReport(id))
  } finally {
    reportLoading.value = false
  }
}

watch(
  reportId,
  (id) => {
    void loadReport(id)
  },
  { immediate: true },
)

// Redirect /rapports/foo.md → /rapports/foo
watch(
  () => route.params.slug as string,
  (raw) => {
    if (raw && /\.md$/i.test(raw)) {
      router.replace({
        name: 'report-detail',
        params: { slug: raw.replace(/\.md$/i, '') },
        hash: route.hash,
        query: route.query,
      })
    }
  },
  { immediate: true },
)

const articleRef = ref<HTMLElement | null>(null)
const scrollContainerRef = ref<HTMLElement | null>(null)
const activeId = ref('')

function slugify(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
}

function extractPlainText(token: Tokens.Generic | string): string {
  if (typeof token === 'string') return token
  if ('text' in token && typeof token.text === 'string' && !('tokens' in token)) {
    return token.text
  }
  if ('tokens' in token && Array.isArray(token.tokens)) {
    return token.tokens.map((t) => extractPlainText(t)).join('')
  }
  if ('text' in token && typeof token.text === 'string') return token.text
  return ''
}

const parsed = computed(() => {
  if (!report.value) return { html: '', headings: [] as TocItem[] }

  const headings: TocItem[] = []
  const usedIds = new Set<string>()

  const renderer = new marked.Renderer()

  renderer.heading = ({ tokens, depth }: Tokens.Heading) => {
    const text = extractPlainText({ tokens } as Tokens.Generic)
    let id = slugify(text) || `section-${headings.length + 1}`
    let n = 1
    while (usedIds.has(id)) {
      id = `${slugify(text)}-${n++}`
    }
    usedIds.add(id)
    // Skip the main H1 title in TOC (already in page header)
    if (depth >= 2) {
      headings.push({ id, text, level: depth })
    }
    const inner = marked.Parser.parseInline(tokens)
    return `<h${depth} id="${id}"><a href="#${id}" class="heading-anchor" aria-hidden="true"></a>${inner}</h${depth}>`
  }

  renderer.link = ({ href, title, tokens }: Tokens.Link) => {
    const text = marked.Parser.parseInline(tokens)
    const titleAttr = title ? ` title="${title}"` : ''

    // Relative links to other rapport .md files → in-app routes
    if (href && /\.md$/i.test(href) && !/^https?:\/\//i.test(href)) {
      const targetSlug = href.split('/').pop()!.replace(/\.md$/i, '')
      return `<a href="/rapports/${targetSlug}"${titleAttr} class="report-link">${text}</a>`
    }

    const external = href && /^https?:\/\//i.test(href)
    const rel = external ? ' rel="noopener noreferrer" target="_blank"' : ''
    return `<a href="${href ?? '#'}"${titleAttr}${rel}>${text}</a>`
  }

  const html = (marked.parse(report.value.content, { renderer, gfm: true }) as string)
    .replace(/<table>/g, '<div class="table-wrap"><table>')
    .replace(/<\/table>/g, '</table></div>')
  return { html, headings }
})

const renderedContent = computed(() => parsed.value.html)
const toc = computed(() => parsed.value.headings)

function formatDate(dateStr: string) {
  if (!dateStr) return ''
  const [year, month, day] = dateStr.split('-')
  const months = [
    'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
    'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre',
  ]
  return `${parseInt(day)} ${months[parseInt(month) - 1]} ${year}`
}

function scrollToId(id: string, updateHash = true) {
  const el = articleRef.value?.querySelector(`#${CSS.escape(id)}`) as HTMLElement | null
  const container = scrollContainerRef.value
  if (!el || !container) return

  const containerTop = container.getBoundingClientRect().top
  const elTop = el.getBoundingClientRect().top
  const offset = elTop - containerTop + container.scrollTop - 24

  container.scrollTo({ top: offset, behavior: 'smooth' })
  activeId.value = id

  if (updateHash) {
    router.replace({ hash: `#${id}`, query: route.query })
  }
}

function onTocClick(e: Event, id: string) {
  e.preventDefault()
  scrollToId(id)
}

function onArticleClick(e: MouseEvent) {
  const target = (e.target as HTMLElement).closest('a')
  if (!target) return

  const href = target.getAttribute('href')
  if (!href) return

  // Internal report links → SPA navigation
  const reportMatch = href.match(/^\/rapports\/([^/#?]+)(?:[?#]|$)/)
  if (reportMatch) {
    e.preventDefault()
    const targetSlug = reportMatch[1].replace(/\.md$/i, '')
    router.push({ name: 'report-detail', params: { slug: targetSlug } })
    scrollContainerRef.value?.scrollTo({ top: 0 })
    return
  }

  // In-page heading anchors
  if (href.startsWith('#')) {
    e.preventDefault()
    scrollToId(href.slice(1))
  }
}

function updateActiveFromScroll() {
  if (!articleRef.value || !scrollContainerRef.value || toc.value.length === 0) return

  const container = scrollContainerRef.value
  const containerTop = container.getBoundingClientRect().top
  const threshold = 80

  let current = toc.value[0]?.id ?? ''
  for (const item of toc.value) {
    const el = articleRef.value.querySelector(`#${CSS.escape(item.id)}`) as HTMLElement | null
    if (!el) continue
    const top = el.getBoundingClientRect().top - containerTop
    if (top <= threshold) current = item.id
  }
  activeId.value = current
}

function onScroll() {
  updateActiveFromScroll()
}

async function scrollToHashIfPresent() {
  await nextTick()
  const hash = route.hash?.replace(/^#/, '')
  if (hash) {
    // Small delay so layout is settled
    requestAnimationFrame(() => scrollToId(hash, false))
  } else if (toc.value.length) {
    activeId.value = toc.value[0].id
  }
}

watch(reportId, () => {
  activeId.value = ''
  scrollToHashIfPresent()
})

watch(
  () => route.hash,
  (hash) => {
    const id = hash?.replace(/^#/, '')
    if (id && id !== activeId.value) scrollToId(id, false)
  },
)

onMounted(() => {
  scrollContainerRef.value?.addEventListener('scroll', onScroll, { passive: true })
  scrollToHashIfPresent()
})

onUnmounted(() => {
  scrollContainerRef.value?.removeEventListener('scroll', onScroll)
})
</script>

<template>
  <div class="flex h-full flex-col overflow-hidden">
    <!-- Header -->
    <div class="border-b border-[var(--border)] bg-[var(--card)] px-8 py-5">
      <div class="flex items-center gap-4">
        <button
          @click="router.push('/rapports')"
          class="flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--border)] text-[var(--muted-foreground)] transition hover:bg-[var(--accent)] hover:text-[var(--foreground)]"
        >
          <ArrowLeft :size="16" />
        </button>
        <div class="min-w-0 flex-1">
          <h1 class="truncate text-lg font-bold text-[var(--foreground)]">
            {{ report?.title ?? reportId }}
          </h1>
          <div v-if="report" class="mt-0.5 flex flex-wrap items-center gap-3">
            <span class="flex items-center gap-1 text-xs text-[var(--muted-foreground)]">
              <Calendar :size="12" />
              {{ formatDate(report.date) }}
            </span>
            <PdfButton
              :pdf-url="`/data/pdf-generes/rapport/${reportId}.pdf`"
              :generate-endpoint="`/pdf/generate/report/${reportId}`"
              label="Rapport PDF"
              :auto-generate="true"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div
      v-if="(reportLoading || reportsLoading) && !report"
      class="flex flex-1 items-center justify-center text-sm text-[var(--muted-foreground)]"
    >
      Chargement…
    </div>

    <!-- Not found -->
    <div v-else-if="!report" class="flex flex-1 flex-col items-center justify-center gap-4 text-center">
      <div class="rounded-full bg-[var(--muted)] p-5">
        <FileText :size="32" class="text-[var(--muted-foreground)]" />
      </div>
      <p class="text-base font-medium">Rapport introuvable</p>
      <button
        @click="router.push('/rapports')"
        class="rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-foreground)] transition hover:opacity-90"
      >
        Retour aux rapports
      </button>
    </div>

    <!-- Content + TOC -->
    <div v-else ref="scrollContainerRef" class="flex-1 overflow-y-auto">
      <div class="mx-auto flex max-w-6xl gap-10 px-8 py-8">
        <!-- Article -->
        <div class="min-w-0 flex-1">
          <div v-if="report.tags.length" class="mb-6 flex flex-wrap gap-2">
            <span
              v-for="tag in report.tags"
              :key="tag"
              class="flex items-center gap-1 rounded-full bg-[var(--secondary)] px-3 py-1 text-xs font-medium capitalize text-[var(--secondary-foreground)]"
            >
              <Tag :size="10" />
              {{ tag }}
            </span>
          </div>

          <article ref="articleRef" class="prose" v-html="renderedContent" @click="onArticleClick" />
        </div>

        <!-- Sommaire -->
        <aside
          v-if="toc.length"
          class="hidden w-56 shrink-0 xl:block"
        >
          <nav class="sticky top-0 max-h-[calc(100vh-6rem)] overflow-y-auto py-1">
            <div class="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
              <List :size="13" />
              Sommaire
            </div>
            <ul class="space-y-0.5 border-l border-[var(--border)]">
              <li v-for="item in toc" :key="item.id">
                <a
                  :href="`#${item.id}`"
                  @click="onTocClick($event, item.id)"
                  :class="[
                    'block border-l-2 py-1.5 text-[13px] leading-snug transition-colors -ml-px',
                    item.level >= 3 ? 'pl-5' : 'pl-3',
                    activeId === item.id
                      ? 'border-[var(--primary)] font-medium text-[var(--primary)]'
                      : 'border-transparent text-[var(--muted-foreground)] hover:border-[var(--border)] hover:text-[var(--foreground)]',
                  ]"
                >
                  {{ item.text }}
                </a>
              </li>
            </ul>
          </nav>
        </aside>
      </div>
    </div>
  </div>
</template>
