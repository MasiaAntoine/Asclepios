<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { marked } from 'marked'
import {
  Loader,
  MessageSquare,
  Plus,
  Send,
  Sparkles,
  Trash2,
  UserRound,
} from '@lucide/vue'
import logoIconUrl from '@/assets/logo-icon.png'
import { useProfile } from '@/composables/useProfile'

interface ChatMsg {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at?: string
}

interface ConversationMeta {
  id: string
  title: string
  created_at: string | null
  updated_at: string | null
  message_count: number
  preview: string
}

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || '/api'
const WELCOME =
  "Bonjour — je suis **Asclepios**. Je connais ton dossier médical.\n\nPose-moi une question, par exemple :\n- *Comment a évolué mon poids ?*\n- *Résume ma posologie actuelle*\n- *Prépare un brief pour mon prochain RDV*"

const { photoUrl } = useProfile()
const userPhotoFailed = ref(false)

const conversations = ref<ConversationMeta[]>([])
const activeId = ref<string | null>(null)
const messages = ref<ChatMsg[]>([{ id: 'welcome', role: 'assistant', content: WELCOME }])
const listLoading = ref(true)
const input = ref('')
const running = ref(false)
const statusLine = ref('')
const error = ref<string | null>(null)
const listEl = ref<HTMLElement | null>(null)
let abortController: AbortController | null = null

const canSend = computed(() => !running.value && input.value.trim().length > 0)
const activeTitle = computed(() => {
  if (!activeId.value) return 'Nouvelle conversation'
  return conversations.value.find((c) => c.id === activeId.value)?.title ?? 'Conversation'
})

function renderMd(text: string): string {
  return marked.parse(text, { gfm: true, breaks: true }) as string
}

async function scrollToBottom() {
  await nextTick()
  if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
}

watch(
  () => messages.value.map((m) => m.content).join('\0'),
  () => {
    void scrollToBottom()
  },
)

async function loadConversations() {
  listLoading.value = true
  try {
    const res = await fetch(`${API_BASE}/chats`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = (await res.json()) as { conversations: ConversationMeta[] }
    conversations.value = data.conversations ?? []
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Impossible de charger les conversations'
  } finally {
    listLoading.value = false
  }
}

async function openConversation(id: string) {
  if (running.value || id === activeId.value) return
  error.value = null
  try {
    const res = await fetch(`${API_BASE}/chats/${id}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = (await res.json()) as { id: string; messages: ChatMsg[] }
    activeId.value = data.id
    const msgs = (data.messages ?? []).filter((m) => m.role === 'user' || m.role === 'assistant')
    messages.value = msgs.length
      ? msgs
      : [{ id: 'welcome', role: 'assistant', content: WELCOME }]
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Chargement impossible'
  }
}

function startNewConversation() {
  if (running.value) return
  activeId.value = null
  messages.value = [{ id: 'welcome', role: 'assistant', content: WELCOME }]
  error.value = null
  statusLine.value = ''
}

async function deleteConversation(id: string, ev?: Event) {
  ev?.stopPropagation()
  if (running.value) return
  const conv = conversations.value.find((c) => c.id === id)
  if (!confirm(`Supprimer « ${conv?.title ?? id} » ?`)) return

  try {
    const res = await fetch(`${API_BASE}/chats/${id}/delete`, { method: 'POST' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    // Consommer le SSE rapidement
    const reader = res.body?.getReader()
    if (reader) {
      while (true) {
        const { done } = await reader.read()
        if (done) break
      }
    }
    conversations.value = conversations.value.filter((c) => c.id !== id)
    if (activeId.value === id) startNewConversation()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Suppression impossible'
  }
}

function upsertConversationMeta(id: string, title?: string) {
  const existing = conversations.value.find((c) => c.id === id)
  const now = new Date().toISOString()
  if (existing) {
    if (title) existing.title = title
    existing.updated_at = now
    existing.message_count = messages.value.filter((m) => m.id !== 'welcome').length
  } else {
    conversations.value.unshift({
      id,
      title: title || 'Nouvelle conversation',
      created_at: now,
      updated_at: now,
      message_count: 1,
      preview: '',
    })
  }
  conversations.value.sort((a, b) => (b.updated_at || '').localeCompare(a.updated_at || ''))
}

async function send() {
  const text = input.value.trim()
  if (!text || running.value) return

  error.value = null
  statusLine.value = ''
  input.value = ''

  // Retirer le welcome local
  messages.value = messages.value.filter((m) => m.id !== 'welcome')

  const userMsg: ChatMsg = {
    id: `u-${Date.now()}`,
    role: 'user',
    content: text,
  }
  messages.value.push(userMsg)

  const assistantId = `a-${Date.now()}`
  messages.value.push({ id: assistantId, role: 'assistant', content: '' })

  running.value = true
  abortController = new AbortController()

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        conversation_id: activeId.value,
      }),
      signal: abortController.signal,
    })
    if (!res.ok) throw new Error(`Erreur HTTP ${res.status}`)

    const reader = res.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let inAnswer = false
    let answer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const blocks = buffer.split('\n\n')
      buffer = blocks.pop() ?? ''

      for (const block of blocks) {
        const line = block.replace(/^data: /, '')
        if (line === '[DONE]') continue
        if (line === '[ERROR]') {
          error.value = 'Une erreur est survenue.'
          continue
        }
        if (line.startsWith('CONVERSATION:')) {
          const id = line.slice('CONVERSATION:'.length)
          activeId.value = id
          upsertConversationMeta(id)
          continue
        }
        if (line.startsWith('TITLE:')) {
          const title = line.slice('TITLE:'.length)
          if (activeId.value) upsertConversationMeta(activeId.value, title)
          continue
        }
        if (line === '[ANSWER_START]') {
          inAnswer = true
          statusLine.value = ''
          continue
        }
        if (line === '[ANSWER_END]') {
          inAnswer = false
          continue
        }
        if (inAnswer) {
          answer += line.replace(/\\n/g, '\n')
          const msg = messages.value.find((m) => m.id === assistantId)
          if (msg) msg.content = answer
        } else if (line.startsWith('Erreur')) {
          error.value = line
        } else if (line.trim()) {
          statusLine.value = line
        }
      }
    }

    const msg = messages.value.find((m) => m.id === assistantId)
    if (msg && !msg.content.trim()) {
      msg.content = error.value
        ? `Désolé — ${error.value}`
        : 'Aucune réponse reçue. Vérifie CURSOR_API_KEY et relance l’API.'
    }

    await loadConversations()
  } catch (e) {
    if ((e as Error).name !== 'AbortError') {
      error.value = e instanceof Error ? e.message : 'Erreur inconnue'
      const msg = messages.value.find((m) => m.id === assistantId)
      if (msg && !msg.content) msg.content = `Erreur : ${error.value}`
    }
  } finally {
    running.value = false
    abortController = null
    statusLine.value = ''
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    void send()
  }
}

function cancel() {
  abortController?.abort()
}

function formatWhen(iso: string | null) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })
  } catch {
    return ''
  }
}

onMounted(() => {
  void loadConversations()
})
</script>

<template>
  <div class="flex h-full overflow-hidden">
    <!-- Sidebar conversations -->
    <aside class="flex w-64 shrink-0 flex-col border-r border-[var(--border)] bg-[var(--card)]">
      <div class="border-b border-[var(--border)] p-3">
        <button
          type="button"
          class="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[var(--primary)] px-3 py-2.5 text-sm font-medium text-[var(--primary-foreground)] transition hover:opacity-90 disabled:opacity-50"
          :disabled="running"
          @click="startNewConversation"
        >
          <Plus :size="16" />
          Nouvelle conversation
        </button>
      </div>

      <div class="flex-1 overflow-y-auto p-2">
        <p v-if="listLoading" class="px-2 py-4 text-center text-xs text-[var(--muted-foreground)]">
          Chargement…
        </p>
        <p
          v-else-if="!conversations.length"
          class="px-2 py-6 text-center text-xs text-[var(--muted-foreground)]"
        >
          Aucune conversation sauvegardée
        </p>
        <button
          v-for="c in conversations"
          :key="c.id"
          type="button"
          class="group mb-1 flex w-full flex-col gap-0.5 rounded-xl px-3 py-2.5 text-left transition"
          :class="
            activeId === c.id
              ? 'bg-[var(--primary)]/12 text-[var(--foreground)]'
              : 'hover:bg-[var(--accent)] text-[var(--foreground)]'
          "
          :disabled="running"
          @click="openConversation(c.id)"
        >
          <div class="flex items-start gap-2">
            <MessageSquare
              :size="14"
              class="mt-0.5 shrink-0 text-[var(--primary)]"
            />
            <span class="min-w-0 flex-1 truncate text-sm font-medium">{{ c.title }}</span>
            <button
              type="button"
              class="shrink-0 rounded p-0.5 text-[var(--muted-foreground)] opacity-0 transition hover:text-red-600 group-hover:opacity-100"
              title="Supprimer"
              @click="deleteConversation(c.id, $event)"
            >
              <Trash2 :size="13" />
            </button>
          </div>
          <p class="pl-5 text-[10px] text-[var(--muted-foreground)]">
            {{ formatWhen(c.updated_at) }}
            <template v-if="c.message_count"> · {{ c.message_count }} msg</template>
          </p>
        </button>
      </div>
    </aside>

    <!-- Main chat -->
    <div class="flex min-w-0 flex-1 flex-col overflow-hidden">
      <div class="border-b border-[var(--border)] bg-[var(--card)] px-6 py-4">
        <h1 class="flex items-center gap-2 text-lg font-bold text-[var(--foreground)]">
          <Sparkles :size="18" class="text-[var(--primary)]" />
          <span class="truncate">{{ activeTitle }}</span>
        </h1>
        <p class="mt-0.5 text-xs text-[var(--muted-foreground)]">
          Sauvegardé dans le vault · sync OVH à chaque message
        </p>
      </div>

      <div ref="listEl" class="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
        <div class="mx-auto flex max-w-3xl flex-col gap-4">
          <div
            v-for="m in messages"
            :key="m.id"
            class="flex gap-3"
            :class="m.role === 'user' ? 'flex-row-reverse' : ''"
          >
            <div class="mt-0.5 h-8 w-8 shrink-0 overflow-hidden rounded-full ring-1 ring-[var(--border)]">
              <img
                v-if="m.role === 'user' && !userPhotoFailed"
                :src="photoUrl"
                alt="Moi"
                class="h-full w-full object-cover"
                @error="userPhotoFailed = true"
              />
              <div
                v-else-if="m.role === 'user'"
                class="flex h-full w-full items-center justify-center bg-[var(--secondary)] text-[var(--secondary-foreground)]"
              >
                <UserRound :size="15" />
              </div>
              <img
                v-else
                :src="logoIconUrl"
                alt="Asclepios"
                class="h-full w-full object-cover"
              />
            </div>
            <div
              class="max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed"
              :class="
                m.role === 'user'
                  ? 'rounded-tr-md bg-[var(--primary)] text-[var(--primary-foreground)]'
                  : 'rounded-tl-md border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)]'
              "
            >
              <div
                v-if="m.role === 'assistant' && m.content"
                class="prose prose-sm max-w-none prose-p:my-2 prose-ul:my-2 prose-li:my-0.5"
                v-html="renderMd(m.content)"
              />
              <p v-else-if="m.content" class="whitespace-pre-wrap">{{ m.content }}</p>
              <p v-else class="flex items-center gap-2 text-[var(--muted-foreground)]">
                <Loader :size="14" class="animate-spin" />
                {{ statusLine || 'Réflexion…' }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div class="border-t border-[var(--border)] bg-[var(--card)] px-4 py-4 sm:px-6">
        <div class="mx-auto max-w-3xl">
          <p v-if="error" class="mb-2 text-xs text-red-600">{{ error }}</p>
          <div
            class="flex items-end gap-2 rounded-2xl border border-[var(--border)] bg-[var(--background)] p-2 shadow-sm focus-within:border-[var(--primary)] focus-within:ring-2 focus-within:ring-[var(--primary)]/15"
          >
            <textarea
              v-model="input"
              rows="1"
              placeholder="Pose une question sur ton dossier…"
              class="max-h-40 min-h-[44px] flex-1 resize-none bg-transparent px-3 py-2.5 text-sm outline-none placeholder:text-[var(--muted-foreground)]"
              :disabled="running"
              @keydown="onKeydown"
            />
            <button
              v-if="running"
              type="button"
              class="mb-1 mr-1 inline-flex h-10 items-center gap-1.5 rounded-xl border border-red-200 bg-red-50 px-3 text-sm font-medium text-red-700"
              @click="cancel"
            >
              Stop
            </button>
            <button
              v-else
              type="button"
              class="mb-1 mr-1 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--primary)] text-[var(--primary-foreground)] transition hover:opacity-90 disabled:opacity-40"
              :disabled="!canSend"
              @click="send"
            >
              <Send :size="16" />
            </button>
          </div>
          <p class="mt-2 text-center text-[11px] text-[var(--muted-foreground)]">
            Entrée pour envoyer · chaque message est écrit dans
            <code class="rounded bg-[var(--muted)] px-1">data/chats/</code>
            puis poussé sur OVH
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
