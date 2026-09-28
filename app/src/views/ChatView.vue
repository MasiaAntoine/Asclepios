<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { marked } from "marked";
import {
  EllipsisVertical,
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
  X,
} from "@lucide/vue";
import logoIconUrl from "@/assets/logo-icon.png";
import { useProfile } from "@/composables/useProfile";
import { useChatKeyboardLayout } from "@/composables/useChatKeyboardLayout";
import PageShell from "@/components/PageShell.vue";
import ChatThinkingDots from "@/components/ChatThinkingDots.vue";
import BottomSheet from "@/components/ui/BottomSheet.vue";
import AiForgeOverlay from "@/components/AiForgeOverlay.vue";
import ReportDetailView from "@/views/ReportDetailView.vue";
import { useMobileSheet } from "@/composables/useMobileSheet";
import EditProposal from "@/components/EditProposal.vue";
import DeleteConversationDialog from "@/components/DeleteConversationDialog.vue";
import { apiFetch } from '@/lib/apiFetch'
import { useReports } from '@/composables/useReports'
import { promptReportEmotions } from '@/composables/useEmotionPrompt'
import { useReportEmotions } from '@/composables/useReportEmotions'

interface EditProposalData {
  path: string;
  description: string;
  old_string: string;
  new_string: string;
  status?: string;
  created_at?: string;
  updated_at?: string;
}

interface ChatMsg {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at?: string;
  editProposals?: EditProposalData[];
}

interface ConversationMeta {
  id: string;
  title: string;
  created_at: string | null;
  updated_at: string | null;
  message_count: number;
  preview: string;
  report_id?: string | null;
  kind?: string | null;
}

const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) || "/api";
const WELCOME =
  "Salut — je suis **ton allié Asclepios**. Je connais ton dossier médical, et je suis là pour t’accompagner.\n\nPose-moi ce que tu veux, par exemple :\n- *Comment a évolué mon poids ?*\n- *Résume ma posologie actuelle*\n- *Prépare un brief pour mon prochain RDV*";

const router = useRouter();
const route = useRoute();
const { photoUrl } = useProfile();
const { reload: reloadReports } = useReports();
const { isEvaluated } = useReportEmotions();
const { itemId: reportSheetId, sheetOpen: reportSheetOpen, openItem: openReportSheet } = useMobileSheet();
const userPhotoFailed = ref(false);

const conversations = ref<ConversationMeta[]>([]);
const activeId = ref<string | null>(null);
const activeReportId = ref<string | null>(null);
const activeKind = ref<string | null>(null);
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
const inputEl = ref<HTMLTextAreaElement | null>(null);
/** Liste des conversations (tiroir mobile). */
const listOpen = ref(false);
let abortController: AbortController | null = null;
let checkinKickoffFor: string | null = null;

const { shellStyle, keyboardOpen, syncViewport } = useChatKeyboardLayout(listEl);

function autoResizeInput() {
  const el = inputEl.value;
  if (!el) return;
  el.style.height = "auto";
  el.style.height = `${Math.min(el.scrollHeight, 128)}px`;
}

watch(input, () => {
  void nextTick(autoResizeInput);
});

// Delete dialog state
const deleteDialogOpen = ref(false);
const conversationToDelete = ref<{ id: string; title: string; isLinked: boolean } | null>(
  null,
);

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

/** Horodatage ISO du serveur (UTC) → heure locale « 21:07 ». */
function messageTime(iso?: string): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

/** Date complète pour l'infobulle (le jour n'est pas visible dans la bulle). */
function messageDateTitle(iso?: string): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function scrollToBottom() {
  await nextTick();
  if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight;
}

const streamingId = ref<string | null>(null);
const revealed = ref("");
const revealTarget = ref("");
const freshIds = ref<Set<string>>(new Set());
let revealTimer: ReturnType<typeof setTimeout> | null = null;

const showCaret = computed(
  () =>
    streamingId.value != null &&
    revealed.value.length > 0 &&
    revealed.value.length < revealTarget.value.length,
);

function stopReveal() {
  if (revealTimer != null) {
    clearTimeout(revealTimer);
    revealTimer = null;
  }
}

function flushReveal() {
  stopReveal();
  revealed.value = revealTarget.value;
}

function stepReveal() {
  revealTimer = null;
  if (revealed.value.length >= revealTarget.value.length) {
    if (!running.value) streamingId.value = null;
    return;
  }
  const rest = revealTarget.value.slice(revealed.value.length);
  const take = rest.match(/^\s*\S+/);
  const chunk = take ? take[0] : rest.slice(0, 1);
  revealed.value += chunk;
  if (revealed.value.length >= revealTarget.value.length) {
    if (!running.value) streamingId.value = null;
    return;
  }
  // Un peu plus rapide que la lecture à voix haute, encore lisible mot à mot.
  const letters = chunk.trim().length;
  const delay = Math.min(90, Math.max(36, 32 + letters * 4));
  revealTimer = window.setTimeout(stepReveal, delay);
}

function queueReveal(full: string) {
  revealTarget.value = full;
  if (revealTimer == null && revealed.value.length < revealTarget.value.length) {
    stepReveal();
  }
}

function bubbleText(m: ChatMsg) {
  if (m.id === streamingId.value) return revealed.value;
  return m.content;
}

function markFresh(id: string) {
  const next = new Set(freshIds.value);
  next.add(id);
  freshIds.value = next;
}

onUnmounted(() => {
  stopReveal();
});

async function loadConversations() {
  listLoading.value = true;
  try {
    const res = await apiFetch(`${API_BASE}/chats`);
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

function routeChatId(): string | undefined {
  const id = route.params.id;
  return typeof id === "string" && id.length ? id : undefined;
}

function resetConversationState() {
  stopReveal();
  streamingId.value = null;
  revealed.value = "";
  revealTarget.value = "";
  freshIds.value = new Set();
  activeId.value = null;
  activeReportId.value = null;
  activeKind.value = null;
  messages.value = [{ id: "welcome", role: "assistant", content: WELCOME }];
  error.value = null;
  statusLine.value = "";
  reportStatus.value = "";
  listOpen.value = false;
}

async function openConversation(id: string) {
  if (running.value || generatingReport.value) {
    listOpen.value = false;
    return;
  }
  error.value = null;
  reportStatus.value = "";
  listOpen.value = false;
  stopReveal();
  streamingId.value = null;
  revealed.value = "";
  revealTarget.value = "";
  freshIds.value = new Set();
  try {
    const res = await apiFetch(`${API_BASE}/chats/${id}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = (await res.json()) as {
      id: string;
      messages: ChatMsg[];
      report_id?: string | null;
      kind?: string | null;
      title?: string;
    };
    activeId.value = data.id;
    activeReportId.value = data.report_id ?? null;
    activeKind.value = data.kind ?? null;
    const msgs = (data.messages ?? []).filter(
      (m) => m.role === "user" || m.role === "assistant",
    );
    const isCheckin = data.kind === "checkin";
    messages.value = msgs.length
      ? msgs
      : isCheckin
        ? []
        : [{ id: "welcome", role: "assistant", content: WELCOME }];
    void scrollToBottom();
    const hasAssistant = msgs.some(
      (m) => m.role === "assistant" && m.content.trim(),
    );
    if (isCheckin && !hasAssistant && !running.value && !generatingReport.value) {
      void startCheckin(data.id);
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Chargement impossible";
  }
}

function selectConversation(id: string) {
  listOpen.value = false;
  if (routeChatId() === id) return;
  void router.push({ name: "chat", params: { id } });
}

function startNewConversation() {
  if (running.value || generatingReport.value) return;
  listOpen.value = false;
  if (!routeChatId()) {
    resetConversationState();
    return;
  }
  void router.push("/assistant");
}

function openDeleteDialog(id: string, ev?: Event) {
  ev?.stopPropagation();
  ev?.preventDefault();
  if (running.value || generatingReport.value) return;

  const conv = conversations.value.find((c) => c.id === id);
  if (!conv) return;

  conversationToDelete.value = {
    id: conv.id,
    title: conv.title,
    isLinked: !!conv.report_id,
  };
  deleteDialogOpen.value = true;
}

async function confirmDelete() {
  if (!conversationToDelete.value) return;

  const id = conversationToDelete.value.id;

  // Mise à jour immédiate de la liste (sans attendre le réseau)
  const previous = [...conversations.value];
  conversations.value = conversations.value.filter((c) => c.id !== id);
  if (activeId.value === id) startNewConversation();

  try {
    const res = await apiFetch(`${API_BASE}/chats/${id}/delete`, { method: "POST" });
    if (res.status === 403) {
      conversations.value = previous;
      error.value = "Conversation liée à un rapport : suppression impossible.";
      await loadConversations();
      deleteDialogOpen.value = false;
      return;
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    await loadConversations();
    deleteDialogOpen.value = false;
    conversationToDelete.value = null;
  } catch (e) {
    conversations.value = previous;
    error.value = e instanceof Error ? e.message : "Suppression impossible";
    await loadConversations();
    deleteDialogOpen.value = false;
  }
}

function cancelDelete() {
  deleteDialogOpen.value = false;
  conversationToDelete.value = null;
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
    if (activeKind.value) existing.kind = activeKind.value;
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
      kind: activeKind.value,
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
    const res = await apiFetch(
      `${API_BASE}/chats/${activeId.value}/generate-report`,
      {
        method: "POST",
      },
    );
    if (!res.ok) throw new Error(`Erreur HTTP ${res.status}`);

    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let generatedId: string | null = null;

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
          generatedId = rid;
          activeReportId.value = rid;
          if (activeId.value)
            upsertConversationMeta(activeId.value, undefined, rid);
          void reloadReports();
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
    if (generatedId && !error.value) {
      window.setTimeout(() => promptReportEmotions(generatedId!), 400);
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Erreur génération rapport";
  } finally {
    generatingReport.value = false;
  }
}

async function openLinkedReport() {
  if (!activeReportId.value) return
  await reloadReports()
  openReportSheet(activeReportId.value, `/rapports/${activeReportId.value}`)
}

async function send() {
  const text = input.value.trim();
  if (!text || running.value || generatingReport.value) return;

  error.value = null;
  statusLine.value = "";
  input.value = "";
  void nextTick(() => {
    autoResizeInput();
    void scrollToBottom();
  });

  messages.value = messages.value.filter((m) => m.id !== "welcome");

  const userMsg: ChatMsg = {
    id: `u-${Date.now()}`,
    role: "user",
    content: text,
    created_at: new Date().toISOString(),
  };
  messages.value.push(userMsg);
  markFresh(userMsg.id);

  const assistantId = `a-${Date.now()}`;
  let aborted = false;
  // `created_at` est posé à la fin du stream, comme côté serveur : l'heure
  // affichée reste donc la même après un rechargement de la conversation.
  messages.value.push({
    id: assistantId,
    role: "assistant",
    content: "",
    editProposals: [],
  });
  markFresh(assistantId);
  stopReveal();
  streamingId.value = assistantId;
  revealed.value = "";
  revealTarget.value = "";
  void scrollToBottom();

  running.value = true;
  abortController = new AbortController();

  try {
    const res = await apiFetch(`${API_BASE}/chat`, {
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
          if (routeChatId() !== id) {
            void router.replace({ name: "chat", params: { id } });
          }
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
        if (line.startsWith("EDIT_PROPOSAL:")) {
          try {
            const proposal = JSON.parse(
              line.slice("EDIT_PROPOSAL:".length),
            ) as EditProposalData;
            const msg = messages.value.find((m) => m.id === assistantId);
            if (msg) {
              msg.editProposals = msg.editProposals || [];
              msg.editProposals.push(proposal);
            }
          } catch {
            // Ignore invalid JSON
          }
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
          queueReveal(answer);
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
    if (msg) msg.created_at = new Date().toISOString();

    await loadConversations();
  } catch (e) {
    if ((e as Error).name !== "AbortError") {
      error.value = e instanceof Error ? e.message : "Erreur inconnue";
      const msg = messages.value.find((m) => m.id === assistantId);
      if (msg && !msg.content) msg.content = `Erreur : ${error.value}`;
      if (msg) msg.created_at = new Date().toISOString();
    } else {
      aborted = true;
    }
  } finally {
    running.value = false;
    abortController = null;
    statusLine.value = "";
    const done = messages.value.find((m) => m.id === assistantId);
    if (done?.content) {
      queueReveal(done.content);
      if (revealed.value.length >= revealTarget.value.length) {
        streamingId.value = null;
      }
    } else {
      flushReveal();
      streamingId.value = null;
    }
    if (
      !aborted &&
      !error.value &&
      done?.content &&
      activeReportId.value &&
      !isEvaluated(activeReportId.value)
    ) {
      promptReportEmotions(activeReportId.value, { force: false });
    }
  }
}

async function startCheckin(conversationId: string) {
  if (running.value || generatingReport.value) return;
  if (checkinKickoffFor === conversationId) return;
  checkinKickoffFor = conversationId;

  error.value = null;
  statusLine.value = "";
  messages.value = messages.value.filter((m) => m.id !== "welcome");

  const assistantId = `a-${Date.now()}`;
  messages.value.push({
    id: assistantId,
    role: "assistant",
    content: "",
    editProposals: [],
  });
  markFresh(assistantId);
  stopReveal();
  streamingId.value = assistantId;
  revealed.value = "";
  revealTarget.value = "";
  void scrollToBottom();

  running.value = true;
  abortController = new AbortController();
  activeKind.value = "checkin";
  activeId.value = conversationId;
  upsertConversationMeta(conversationId, "Comment ça va ?");

  try {
    const res = await apiFetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: "",
        conversation_id: conversationId,
        checkin: true,
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
        if (line === "[DONE]" || line === "[ERROR]") continue;
        if (line.startsWith("CONVERSATION:")) {
          const id = line.slice("CONVERSATION:".length);
          activeId.value = id;
          upsertConversationMeta(id, "Comment ça va ?");
          if (routeChatId() !== id) {
            void router.replace({ name: "chat", params: { id } });
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
          queueReveal(answer);
        } else if (line.startsWith("Erreur")) {
          error.value = line;
        } else if (line.trim() && !line.startsWith("REPORT:") && !line.startsWith("EDIT_PROPOSAL:")) {
          statusLine.value = line;
        }
      }
    }

    const msg = messages.value.find((m) => m.id === assistantId);
    if (msg && !msg.content.trim()) {
      msg.content = error.value
        ? `Désolé — ${error.value}`
        : "Je n’ai pas réussi à ouvrir le check-in. Réessaie dans un instant.";
    }
    if (msg) msg.created_at = new Date().toISOString();
    await loadConversations();
  } catch (e) {
    if ((e as Error).name !== "AbortError") {
      error.value = e instanceof Error ? e.message : "Erreur inconnue";
      const msg = messages.value.find((m) => m.id === assistantId);
      if (msg && !msg.content) msg.content = `Erreur : ${error.value}`;
      checkinKickoffFor = null;
    }
  } finally {
    running.value = false;
    abortController = null;
    statusLine.value = "";
    const done = messages.value.find((m) => m.id === assistantId);
    if (done?.content) {
      queueReveal(done.content);
      if (revealed.value.length >= revealTarget.value.length) {
        streamingId.value = null;
      }
    } else {
      flushReveal();
      streamingId.value = null;
    }
  }
}

async function openCheckinFromNotif() {
  if (running.value || generatingReport.value) return;
  try {
    const res = await apiFetch(`${API_BASE}/chats/checkin`, { method: "POST" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = (await res.json()) as { id: string };
    if (!data.id) return;
    if (routeChatId() === data.id) {
      await openConversation(data.id);
      return;
    }
    await router.replace({ name: "chat", params: { id: data.id } });
  } catch (e) {
    error.value =
      e instanceof Error ? e.message : "Impossible d’ouvrir le check-in";
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    void send();
  }
}

function onComposerFocus() {
  void scrollToBottom();
  window.setTimeout(() => {
    syncViewport();
    void scrollToBottom();
  }, 50);
  window.setTimeout(() => {
    syncViewport();
    void scrollToBottom();
  }, 350);
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

watch(
  () => routeChatId(),
  (id) => {
    if (!id) {
      if (activeId.value) resetConversationState();
      return;
    }
    if (id === activeId.value) return;
    void openConversation(id);
  },
);

watch(
  () => route.query.checkin,
  (raw) => {
    if (raw === undefined || raw === null || raw === "") return;
    void openCheckinFromNotif();
  },
  { immediate: true },
);

onMounted(() => {
  void loadConversations();
  const id = routeChatId();
  if (id) void openConversation(id);
});
</script>

<template>
  <PageShell flush no-scroll>
    <DeleteConversationDialog
      v-if="conversationToDelete"
      v-model:open="deleteDialogOpen"
      :conversation-title="conversationToDelete.title"
      :is-linked-to-report="conversationToDelete.isLinked"
      @confirm="confirmDelete"
      @cancel="cancelDelete"
    />

    <div
      class="relative flex h-full min-h-0 overflow-hidden md:h-full"
      :style="shellStyle"
    >      <Transition
        enter-active-class="transition-opacity duration-200"
        leave-active-class="transition-opacity duration-150"
        enter-from-class="opacity-0"
        leave-to-class="opacity-0"
      >
        <div
          v-if="listOpen"
          class="absolute inset-0 z-30 bg-black/40 md:hidden"
          @click="listOpen = false"
        />
      </Transition>

      <aside
        class="absolute inset-y-0 left-0 z-40 flex w-[min(18rem,88vw)] shrink-0 flex-col border-r border-[var(--border)] bg-[var(--card)] transition-transform duration-200 md:static md:z-auto md:w-64 md:translate-x-0"
        :class="listOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'"
      >
        <div class="flex items-center gap-2 border-b border-[var(--border)] p-3">
          <button
            type="button"
            class="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-[var(--primary)] px-3 py-2.5 text-sm font-medium text-[var(--primary-foreground)] transition hover:opacity-90 disabled:opacity-50"
            :disabled="running || generatingReport"
            @click="startNewConversation"
          >
            <Plus :size="16" />
            Nouvelle
          </button>
          <button
            type="button"
            class="rounded-lg p-2 text-[var(--muted-foreground)] transition hover:bg-[var(--muted)] md:hidden"
            aria-label="Fermer la liste"
            @click="listOpen = false"
          >
            <X :size="18" />
          </button>
        </div>

        <div class="flex-1 overflow-y-auto overscroll-contain p-2">
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
            @click="selectConversation(c.id)"
          >
            <div class="flex items-start gap-2">
              <MessageSquare
                v-if="c.kind !== 'checkin'"
                :size="14"
                class="mt-0.5 shrink-0 text-[var(--primary)]"
              />
              <Sparkles
                v-else
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
                class="shrink-0 rounded p-1 text-[var(--muted-foreground)] transition hover:text-red-600 md:opacity-0 md:group-hover:opacity-100"
                title="Supprimer"
                @click="openDeleteDialog(c.id, $event)"
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
              <template v-else-if="c.kind === 'checkin'"> · check-in</template>
            </p>
          </button>
        </div>
      </aside>

      <div class="flex min-w-0 flex-1 flex-col overflow-hidden">
        <div
          class="shrink-0 border-b border-[var(--border)] bg-[var(--card)] transition-[padding] px-3 sm:px-6"
          :class="keyboardOpen ? 'py-2' : 'py-3 sm:py-4'"
        >
          <div class="flex items-center gap-2 sm:items-start sm:gap-3">
            <button
              type="button"
              class="rounded-lg p-2 text-[var(--foreground)] transition hover:bg-[var(--accent)] md:hidden"
              aria-label="Menu conversations"
              @click="listOpen = true"
            >
              <EllipsisVertical :size="20" />
            </button>
            <div class="min-w-0 flex-1">
              <h1
                class="flex items-center gap-2 text-base font-bold text-[var(--foreground)] sm:text-lg"
              >
                <Sparkles
                  :size="18"
                  class="hidden shrink-0 text-[var(--primary)] sm:block"
                />
                <span class="truncate">{{ activeTitle }}</span>
                <Lock
                  v-if="activeReportId"
                  :size="14"
                  class="shrink-0 text-[var(--muted-foreground)]"
                  title="Liée à un rapport"
                />
              </h1>
              <p
                v-if="!keyboardOpen"
                class="mt-0.5 hidden text-xs text-[var(--muted-foreground)] sm:block"
              >
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
                <template v-else-if="activeKind === 'checkin'">
                  Check-in du moment — questions précises, pas un briefing dossier
                </template>
                <template v-else>
                  Sauvegardé dans le vault · sync OVH à chaque message
                </template>
              </p>
              <p v-if="reportStatus && !keyboardOpen" class="mt-1 text-xs text-[var(--primary)]">
                {{ reportStatus }}
              </p>
            </div>
            <div
              v-if="!keyboardOpen"
              class="flex shrink-0 flex-col items-stretch gap-1.5 sm:flex-row sm:items-center sm:gap-2"
            >
              <button
                v-if="activeReportId"
                type="button"
                class="inline-flex items-center justify-center gap-1.5 rounded-lg border border-[var(--border)] px-2.5 py-2 text-xs text-[var(--foreground)] transition hover:bg-[var(--accent)] sm:px-3 sm:text-sm"
                @click="openLinkedReport"
              >
                <FileText :size="14" />
                <span class="hidden sm:inline">Voir le rapport</span>
              </button>
              <button
                type="button"
                class="inline-flex items-center justify-center gap-1.5 rounded-lg border border-[var(--primary)]/30 bg-[var(--primary)]/8 px-2.5 py-2 text-xs font-medium text-[var(--primary)] transition hover:bg-[var(--primary)]/15 disabled:opacity-40 sm:px-3 sm:text-sm"
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
                <span>{{ activeReportId ? "Régénérer" : "Rapport" }}</span>
              </button>
            </div>
          </div>
        </div>

        <div
          ref="listEl"
          class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-3 py-4 sm:px-6 sm:py-6"
        >
          <div class="mx-auto flex w-full min-w-0 max-w-3xl flex-col gap-3 sm:gap-4">
            <div
              v-for="m in messages"
              :key="m.id"
              class="flex min-w-0 gap-2 sm:gap-3"
              :class="[
                m.role === 'user' ? 'flex-row-reverse' : '',
                freshIds.has(m.id)
                  ? m.role === 'user'
                    ? 'chat-row-in-user'
                    : 'chat-row-in-ai'
                  : '',
              ]"
            >
              <div
                class="mt-0.5 h-7 w-7 shrink-0 overflow-hidden rounded-full ring-1 ring-[var(--border)] sm:h-8 sm:w-8"
                :class="
                  m.role === 'assistant' && streamingId === m.id && !bubbleText(m)
                    ? 'chat-avatar-think'
                    : ''
                "
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
              <div class="flex min-w-0 max-w-[88%] flex-col gap-2 sm:max-w-[85%]">
                <template v-if="m.role === 'assistant' && m.editProposals?.length">
                  <EditProposal
                    v-for="(proposal, pIdx) in m.editProposals"
                    :key="`${m.id}-edit-${pIdx}`"
                    :proposal="proposal"
                    :conversation-id="activeId || undefined"
                    :message-id="m.id"
                    :proposal-index="pIdx"
                    @applied="() => void loadConversations()"
                    @rejected="() => {}"
                  />
                </template>

                <div
                  class="overflow-hidden rounded-2xl px-3 py-2.5 text-sm leading-relaxed sm:px-4 sm:py-3"
                  :class="
                    m.role === 'user'
                      ? 'rounded-tr-md bg-[var(--primary)] text-[var(--primary-foreground)]'
                      : 'rounded-tl-md border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)]'
                  "
                >
                  <div
                    v-if="m.role === 'assistant' && bubbleText(m)"
                    class="prose prose-sm max-w-none overflow-x-auto break-words prose-p:my-2 prose-ul:my-2 prose-li:my-0.5"
                  >
                    <div v-html="renderMd(bubbleText(m))" />
                    <span
                      v-if="showCaret && streamingId === m.id"
                      class="chat-caret"
                      aria-hidden="true"
                    />
                  </div>
                  <p v-else-if="m.content" class="whitespace-pre-wrap break-words">
                    {{ m.content }}
                  </p>
                  <ChatThinkingDots
                    v-else
                    :status="statusLine"
                  />
                </div>

                <span
                  v-if="messageTime(m.created_at)"
                  class="-mt-1 px-1 text-[11px] tabular-nums text-[var(--muted-foreground)]"
                  :class="m.role === 'user' ? 'self-end' : 'self-start'"
                  :title="messageDateTitle(m.created_at)"
                >
                  {{ messageTime(m.created_at) }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div
          class="shrink-0 border-t border-[var(--border)] bg-[var(--card)] px-3 pt-2 sm:px-6 sm:pt-4"
          :style="
            keyboardOpen
              ? { paddingBottom: '0.5rem' }
              : undefined
          "
          :class="keyboardOpen ? '' : 'pb-3 sm:pb-4'"
        >
          <div class="mx-auto max-w-3xl">
            <p v-if="error" class="mb-2 text-xs text-red-600">{{ error }}</p>
            <div
              class="flex items-end gap-2 rounded-2xl border border-[var(--border)] bg-[var(--background)] p-1.5 shadow-sm focus-within:border-[var(--primary)] focus-within:ring-2 focus-within:ring-[var(--primary)]/15 sm:p-2"
            >
              <textarea
                ref="inputEl"
                v-model="input"
                rows="1"
                enterkeyhint="send"
                autocomplete="off"
                autocorrect="on"
                placeholder="Écrire un message…"
                class="max-h-32 min-h-[44px] flex-1 resize-none bg-transparent px-2 py-2.5 text-base leading-5 outline-none placeholder:text-[var(--muted-foreground)] sm:max-h-40 sm:px-3 sm:text-sm"
                :disabled="running || generatingReport"
                @keydown="onKeydown"
                @focus="onComposerFocus"
                @input="autoResizeInput"
              />
              <Transition name="chat-send" mode="out-in">
                <button
                  v-if="running"
                  key="stop"
                  type="button"
                  class="mb-0.5 inline-flex h-11 shrink-0 items-center gap-1.5 rounded-xl border border-red-200 bg-red-50 px-3 text-sm font-medium text-red-700"
                  @click="cancel"
                >
                  Stop
                </button>
                <button
                  v-else
                  key="send"
                  type="button"
                  class="mb-0.5 inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[var(--primary)] text-[var(--primary-foreground)] transition duration-200 hover:opacity-90 active:scale-90 disabled:opacity-40"
                  :disabled="!canSend"
                  @click="send"
                >
                  <Send :size="18" />
                </button>
              </Transition>
            </div>
          </div>
        </div>
      </div>
    </div>
  </PageShell>

  <BottomSheet v-model:open="reportSheetOpen">
    <ReportDetailView v-if="reportSheetId" embedded :item-id="reportSheetId" />
  </BottomSheet>

  <AiForgeOverlay :open="generatingReport" :status="reportStatus" />
</template>

<style scoped>
.chat-row-in-user {
  animation: chat-in-user 0.32s ease-out;
}

.chat-row-in-ai {
  animation: chat-in-ai 0.38s ease-out;
}

@keyframes chat-in-user {
  from {
    opacity: 0;
    transform: translateY(10px) translateX(12px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

@keyframes chat-in-ai {
  from {
    opacity: 0;
    transform: translateY(10px) translateX(-8px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

.chat-avatar-think {
  animation: chat-avatar-pulse 1.6s ease-in-out infinite;
}

@keyframes chat-avatar-pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 color-mix(in oklch, var(--primary) 45%, transparent);
  }
  50% {
    box-shadow: 0 0 0 6px color-mix(in oklch, var(--primary) 0%, transparent);
  }
}

.chat-caret {
  display: inline-block;
  width: 2px;
  height: 0.9em;
  margin-left: 1px;
  vertical-align: text-bottom;
  background: var(--primary);
  animation: chat-caret 0.9s steps(1) infinite;
}

@keyframes chat-caret {
  0%,
  45% {
    opacity: 1;
  }
  50%,
  100% {
    opacity: 0;
  }
}

.chat-send-enter-active,
.chat-send-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.chat-send-enter-from,
.chat-send-leave-to {
  opacity: 0;
  transform: scale(0.88);
}
</style>
