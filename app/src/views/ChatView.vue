<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { marked } from "marked";
import {
  FileText,
  Loader,
  Lock,
  MessageSquare,
  Plus,
  RefreshCw,
  Send,
  Sparkles,
  Trash2,
  UserRound,
} from "@lucide/vue";
import logoIconUrl from "@/assets/logo-icon.png";
import { useProfile } from "@/composables/useProfile";
import PageShell from "@/components/PageShell.vue";

interface ChatMsg {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at?: string;
}

interface ConversationMeta {
  id: string;
  title: string;
  created_at: string | null;
  updated_at: string | null;
  message_count: number;
  preview: string;
  report_id?: string | null;
}

const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) || "/api";
const WELCOME =
  "Salut — je suis **ton allié Asclepios**. Je connais ton dossier médical, et je suis là pour t’accompagner.\n\nPose-moi ce que tu veux, par exemple :\n- *Comment a évolué mon poids ?*\n- *Résume ma posologie actuelle*\n- *Prépare un brief pour mon prochain RDV*";

const router = useRouter();
const { photoUrl } = useProfile();
const userPhotoFailed = ref(false);

const conversations = ref<ConversationMeta[]>([]);
const activeId = ref<string | null>(null);
const activeReportId = ref<string | null>(null);
const messages = ref<ChatMsg[]>([
  { id: "welcome", role: "assistant", content: WELCOME },
]);
const listLoading = ref(true);
const input = ref("");
const running = ref(false);
const generatingReport = ref(false);
const statusLine = ref("");
const reportStatus = ref("");
const error = ref<string | null>(null);
const listEl = ref<HTMLElement | null>(null);
let abortController: AbortController | null = null;

const canSend = computed(
  () =>
    !running.value && !generatingReport.value && input.value.trim().length > 0,
);
const hasRealMessages = computed(() =>
  messages.value.some(
    (m) =>
      m.id !== "welcome" &&
      (m.role === "user" || m.role === "assistant") &&
      m.content.trim(),
  ),
);
const canGenerateReport = computed(
  () =>
    !!activeId.value &&
    hasRealMessages.value &&
    !running.value &&
    !generatingReport.value,
);
const activeTitle = computed(() => {
  if (!activeId.value) return "Nouvelle conversation";
  return (
    conversations.value.find((c) => c.id === activeId.value)?.title ??
    "Conversation"
  );
});

function renderMd(text: string): string {
  return (marked.parse(text, { gfm: true, breaks: true }) as string)
    .replace(/<table>/g, '<div class="table-wrap"><table>')
    .replace(/<\/table>/g, "</table></div>");
}

async function scrollToBottom() {
  await nextTick();
  if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight;
}

watch(
  () => messages.value.map((m) => m.content).join("\0"),
  () => {
    void scrollToBottom();
  },
);

async function loadConversations() {
  listLoading.value = true;
  try {
    const res = await fetch(`${API_BASE}/chats`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = (await res.json()) as { conversations: ConversationMeta[] };
    conversations.value = data.conversations ?? [];
  } catch (e) {
    error.value =
      e instanceof Error
        ? e.message
        : "Impossible de charger les conversations";
  } finally {
    listLoading.value = false;
  }
}

async function openConversation(id: string) {
  if (running.value || generatingReport.value || id === activeId.value) return;
  error.value = null;
  reportStatus.value = "";
  try {
    const res = await fetch(`${API_BASE}/chats/${id}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = (await res.json()) as {
      id: string;
      messages: ChatMsg[];
      report_id?: string | null;
    };
    activeId.value = data.id;
    activeReportId.value = data.report_id ?? null;
    const msgs = (data.messages ?? []).filter(
      (m) => m.role === "user" || m.role === "assistant",
    );
    messages.value = msgs.length
      ? msgs
      : [{ id: "welcome", role: "assistant", content: WELCOME }];
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Chargement impossible";
  }
}

function startNewConversation() {
  if (running.value || generatingReport.value) return;
  activeId.value = null;
  activeReportId.value = null;
  messages.value = [{ id: "welcome", role: "assistant", content: WELCOME }];
  error.value = null;
  statusLine.value = "";
  reportStatus.value = "";
}

async function deleteConversation(id: string, ev?: Event) {
  ev?.stopPropagation()
  ev?.preventDefault()
  if (running.value || generatingReport.value) return
  const conv = conversations.value.find((c) => c.id === id)
  if (conv?.report_id) {
    error.value = 'Cette conversation est liée à un rapport : suppression impossible.'
    return
  }
  if (!confirm(`Supprimer « ${conv?.title ?? id} » ?`)) return

  // Mise à jour immédiate de la liste (sans attendre le réseau)
  const previous = [...conversations.value]
  conversations.value = conversations.value.filter((c) => c.id !== id)
  if (activeId.value === id) startNewConversation()

  try {
    const res = await fetch(`${API_BASE}/chats/${id}/delete`, { method: 'POST' })
    if (res.status === 403) {
      conversations.value = previous
      error.value = 'Conversation liée à un rapport : suppression impossible.'
      await loadConversations()
      return
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    await loadConversations()
  } catch (e) {
    conversations.value = previous
    error.value = e instanceof Error ? e.message : 'Suppression impossible'
    await loadConversations()
  }
}

function upsertConversationMeta(
  id: string,
  title?: string,
  reportId?: string | null,
) {
  const existing = conversations.value.find((c) => c.id === id);
  const now = new Date().toISOString();
  if (existing) {
    if (title) existing.title = title;
    if (reportId !== undefined) existing.report_id = reportId;
    existing.updated_at = now;
    existing.message_count = messages.value.filter(
      (m) => m.id !== "welcome",
    ).length;
  } else {
    conversations.value.unshift({
      id,
      title: title || "Nouvelle conversation",
      created_at: now,
      updated_at: now,
      message_count: 1,
      preview: "",
      report_id: reportId ?? null,
    });
  }
  conversations.value.sort((a, b) =>
    (b.updated_at || "").localeCompare(a.updated_at || ""),
  );
}

async function generateReport() {
  if (!activeId.value || !canGenerateReport.value) return;
  error.value = null;
  reportStatus.value = "";
  generatingReport.value = true;

  try {
    const res = await fetch(
      `${API_BASE}/chats/${activeId.value}/generate-report`,
      {
        method: "POST",
      },
    );
    if (!res.ok) throw new Error(`Erreur HTTP ${res.status}`);

    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() ?? "";
      for (const block of blocks) {
        const line = block.replace(/^data: /, "");
        if (line === "[DONE]") continue;
        if (line === "[ERROR]") {
          error.value = "Échec de la génération du rapport.";
          continue;
        }
        if (line.startsWith("REPORT:")) {
          const rid = line.slice("REPORT:".length);
          activeReportId.value = rid;
          if (activeId.value)
            upsertConversationMeta(activeId.value, undefined, rid);
          continue;
        }
        if (line.startsWith("Erreur")) {
          error.value = line;
        } else if (line.trim()) {
          reportStatus.value = line;
        }
      }
    }
    await loadConversations();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Erreur génération rapport";
  } finally {
    generatingReport.value = false;
  }
}

function openLinkedReport() {
  if (activeReportId.value) {
    void router.push(`/rapports/${activeReportId.value}`);
  }
}

async function send() {
  const text = input.value.trim();
  if (!text || running.value || generatingReport.value) return;

  error.value = null;
  statusLine.value = "";
  input.value = "";

  messages.value = messages.value.filter((m) => m.id !== "welcome");

  const userMsg: ChatMsg = {
    id: `u-${Date.now()}`,
    role: "user",
    content: text,
  };
  messages.value.push(userMsg);

  const assistantId = `a-${Date.now()}`;
  messages.value.push({ id: assistantId, role: "assistant", content: "" });

  running.value = true;
  abortController = new AbortController();

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        conversation_id: activeId.value,
      }),
      signal: abortController.signal,
    });
    if (!res.ok) throw new Error(`Erreur HTTP ${res.status}`);

    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let inAnswer = false;
    let answer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() ?? "";

      for (const block of blocks) {
        const line = block.replace(/^data: /, "");
        if (line === "[DONE]") continue;
        if (line === "[ERROR]") {
          error.value = "Une erreur est survenue.";
          continue;
        }
        if (line.startsWith("CONVERSATION:")) {
          const id = line.slice("CONVERSATION:".length);
          activeId.value = id;
          upsertConversationMeta(id);
          continue;
        }
        if (line.startsWith("REPORT:")) {
          activeReportId.value = line.slice("REPORT:".length);
          if (activeId.value) {
            upsertConversationMeta(
              activeId.value,
              undefined,
              activeReportId.value,
            );
          }
          continue;
        }
        if (line.startsWith("TITLE:")) {
          const title = line.slice("TITLE:".length);
          if (activeId.value) upsertConversationMeta(activeId.value, title);
          continue;
        }
        if (line === "[ANSWER_START]") {
          inAnswer = true;
          statusLine.value = "";
          continue;
        }
        if (line === "[ANSWER_END]") {
          inAnswer = false;
          continue;
        }
        if (inAnswer) {
          answer += line.replace(/\\n/g, "\n");
          const msg = messages.value.find((m) => m.id === assistantId);
          if (msg) msg.content = answer;
        } else if (line.startsWith("Erreur")) {
          error.value = line;
        } else if (line.trim()) {
          statusLine.value = line;
        }
      }
    }

    const msg = messages.value.find((m) => m.id === assistantId);
    if (msg && !msg.content.trim()) {
      msg.content = error.value
        ? `Désolé — ${error.value}`
        : "Aucune réponse reçue. Vérifie CURSOR_API_KEY et relance l’API.";
    }

    await loadConversations();
  } catch (e) {
    if ((e as Error).name !== "AbortError") {
      error.value = e instanceof Error ? e.message : "Erreur inconnue";
      const msg = messages.value.find((m) => m.id === assistantId);
      if (msg && !msg.content) msg.content = `Erreur : ${error.value}`;
    }
  } finally {
    running.value = false;
    abortController = null;
    statusLine.value = "";
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    void send();
  }
}

function cancel() {
  abortController?.abort();
}

function formatWhen(iso: string | null) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
  } catch {
    return "";
  }
}

onMounted(() => {
  void loadConversations();
});
</script>

<template>
  <PageShell flush no-scroll>
  <div class="flex h-full overflow-hidden">
    <aside
      class="flex w-64 shrink-0 flex-col border-r border-[var(--border)] bg-[var(--card)]"
    >
      <div class="border-b border-[var(--border)] p-3">
        <button
          type="button"
          class="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[var(--primary)] px-3 py-2.5 text-sm font-medium text-[var(--primary-foreground)] transition hover:opacity-90 disabled:opacity-50"
          :disabled="running || generatingReport"
          @click="startNewConversation"
        >
          <Plus :size="16" />
          Nouvelle conversation
        </button>
      </div>

      <div class="flex-1 overflow-y-auto p-2">
        <p
          v-if="listLoading"
          class="px-2 py-4 text-center text-xs text-[var(--muted-foreground)]"
        >
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
          :disabled="running || generatingReport"
          @click="openConversation(c.id)"
        >
          <div class="flex items-start gap-2">
            <MessageSquare
              :size="14"
              class="mt-0.5 shrink-0 text-[var(--primary)]"
            />
            <span class="min-w-0 flex-1 truncate text-sm font-medium">{{
              c.title
            }}</span>
            <Lock
              v-if="c.report_id"
              :size="12"
              class="mt-0.5 shrink-0 text-[var(--muted-foreground)]"
              title="Liée à un rapport"
            />
            <button
              v-else
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
            <template v-if="c.message_count">
              · {{ c.message_count }} msg</template
            >
            <template v-if="c.report_id"> · rapport</template>
          </p>
        </button>
      </div>
    </aside>

    <div class="flex min-w-0 flex-1 flex-col overflow-hidden">
      <div class="border-b border-[var(--border)] bg-[var(--card)] px-6 py-4">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="min-w-0">
            <h1
              class="flex items-center gap-2 text-lg font-bold text-[var(--foreground)]"
            >
              <Sparkles :size="18" class="text-[var(--primary)]" />
              <span class="truncate">{{ activeTitle }}</span>
              <Lock
                v-if="activeReportId"
                :size="14"
                class="shrink-0 text-[var(--muted-foreground)]"
                title="Liée à un rapport"
              />
            </h1>
            <p class="mt-0.5 text-xs text-[var(--muted-foreground)]">
              <template v-if="activeReportId">
                Liée au rapport
                <button
                  type="button"
                  class="font-medium text-[var(--primary)] hover:underline"
                  @click="openLinkedReport"
                >
                  {{ activeReportId }}
                </button>
                · suppression désactivée
              </template>
              <template v-else>
                Sauvegardé dans le vault · sync OVH à chaque message
              </template>
            </p>
            <p v-if="reportStatus" class="mt-1 text-xs text-[var(--primary)]">
              {{ reportStatus }}
            </p>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <button
              v-if="activeReportId"
              type="button"
              class="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] px-3 py-2 text-sm text-[var(--foreground)] transition hover:bg-[var(--accent)]"
              @click="openLinkedReport"
            >
              <FileText :size="14" />
              Voir le rapport
            </button>
            <button
              type="button"
              class="inline-flex items-center gap-1.5 rounded-lg border border-[var(--primary)]/30 bg-[var(--primary)]/8 px-3 py-2 text-sm font-medium text-[var(--primary)] transition hover:bg-[var(--primary)]/15 disabled:opacity-40"
              :disabled="!canGenerateReport"
              :title="
                !activeId
                  ? 'Envoie d’abord un message'
                  : activeReportId
                    ? 'Écrase le .md existant'
                    : 'Crée un rapport dans rapports/'
              "
              @click="generateReport"
            >
              <Loader v-if="generatingReport" :size="14" class="animate-spin" />
              <RefreshCw v-else-if="activeReportId" :size="14" />
              <FileText v-else :size="14" />
              {{
                activeReportId ? "Régénérer le rapport" : "Générer un rapport"
              }}
            </button>
          </div>
        </div>
      </div>

      <div ref="listEl" class="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
        <div class="mx-auto flex w-full min-w-0 max-w-3xl flex-col gap-4">
          <div
            v-for="m in messages"
            :key="m.id"
            class="flex min-w-0 gap-3"
            :class="m.role === 'user' ? 'flex-row-reverse' : ''"
          >
            <div
              class="mt-0.5 h-8 w-8 shrink-0 overflow-hidden rounded-full ring-1 ring-[var(--border)]"
            >
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
              class="min-w-0 max-w-[85%] overflow-hidden rounded-2xl px-4 py-3 text-sm leading-relaxed"
              :class="
                m.role === 'user'
                  ? 'rounded-tr-md bg-[var(--primary)] text-[var(--primary-foreground)]'
                  : 'rounded-tl-md border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)]'
              "
            >
              <div
                v-if="m.role === 'assistant' && m.content"
                class="prose prose-sm max-w-none overflow-x-auto prose-p:my-2 prose-ul:my-2 prose-li:my-0.5"
                v-html="renderMd(m.content)"
              />
              <p v-else-if="m.content" class="whitespace-pre-wrap">
                {{ m.content }}
              </p>
              <p
                v-else
                class="flex items-center gap-2 text-[var(--muted-foreground)]"
              >
                <Loader :size="14" class="animate-spin" />
                {{ statusLine || "Réflexion…" }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div
        class="border-t border-[var(--border)] bg-[var(--card)] px-4 py-4 sm:px-6"
      >
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
              :disabled="running || generatingReport"
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
        </div>
      </div>
    </div>
  </div>
  </PageShell>
</template>
