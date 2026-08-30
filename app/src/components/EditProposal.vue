<script setup lang="ts">
import { computed, ref } from "vue";
import { Check, FileEdit, Loader, X } from "@lucide/vue";
import * as Diff from "diff";

interface EditProposal {
  path: string;
  description: string;
  old_string: string;
  new_string: string;
  status?: string;
  created_at?: string;
  updated_at?: string;
}

const props = defineProps<{
  proposal: EditProposal;
  conversationId?: string;
  messageId?: string;
  proposalIndex?: number;
}>();

const emit = defineEmits<{
  applied: [];
  rejected: [];
}>();

const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) || "/api";

const applying = ref(false);
const error = ref<string | null>(null);
const applied = ref(props.proposal.status === "applied");
const rejected = ref(props.proposal.status === "rejected");

// Calcul du diff
const diffLines = computed(() => {
  const changes = Diff.diffLines(props.proposal.old_string, props.proposal.new_string);
  return changes;
});

async function updateStatus(status: "applied" | "rejected") {
  if (!props.conversationId || !props.messageId || props.proposalIndex === undefined) {
    return;
  }

  try {
    await fetch(`${API_BASE}/data/update-edit-status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        conversation_id: props.conversationId,
        message_id: props.messageId,
        proposal_index: props.proposalIndex,
        status,
      }),
    });
  } catch (e) {
    console.error("Erreur mise à jour statut:", e);
  }
}

async function applyEdit() {
  if (applying.value || applied.value) return;
  applying.value = true;
  error.value = null;

  try {
    const res = await fetch(`${API_BASE}/data/apply-edit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        path: props.proposal.path,
        old_string: props.proposal.old_string,
        new_string: props.proposal.new_string,
      }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => null);
      throw new Error(data?.detail || `HTTP ${res.status}`);
    }

    // Lire le SSE pour les logs
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
        if (line === "[DONE]") {
          applied.value = true;
          await updateStatus("applied");
          emit("applied");
        }
        if (line === "[ERROR]") {
          throw new Error("Échec de l'application de l'edit");
        }
      }
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Erreur inconnue";
  } finally {
    applying.value = false;
  }
}

async function reject() {
  rejected.value = true;
  await updateStatus("rejected");
  emit("rejected");
}
</script>

<template>
  <div
    class="my-3 overflow-hidden rounded-xl border-2 border-[var(--primary)]/30 bg-[var(--card)]"
  >
    <!-- Header -->
    <div class="border-b border-[var(--border)] bg-[var(--primary)]/5 px-4 py-3">
      <div class="flex items-start gap-3">
        <FileEdit :size="18" class="mt-0.5 shrink-0 text-[var(--primary)]" />
        <div class="min-w-0 flex-1">
          <p class="text-sm font-semibold text-[var(--foreground)]">
            Proposition de modification
          </p>
          <p class="mt-0.5 text-xs text-[var(--muted-foreground)]">
            {{ proposal.description }}
          </p>
          <p class="mt-1 text-xs font-mono text-[var(--muted-foreground)]">
            📁 data/{{ proposal.path }}
          </p>
        </div>
      </div>
    </div>

    <!-- Diff -->
    <div
      class="max-h-96 overflow-y-auto bg-[var(--background)] px-4 py-3 font-mono text-xs"
    >
      <div v-for="(change, i) in diffLines" :key="i" class="leading-relaxed">
        <div
          v-if="change.added"
          class="bg-green-500/10 text-green-700 dark:text-green-400"
        >
          <span class="select-none text-green-600 dark:text-green-500">+ </span
          >{{ change.value }}
        </div>
        <div
          v-else-if="change.removed"
          class="bg-red-500/10 text-red-700 dark:text-red-400"
        >
          <span class="select-none text-red-600 dark:text-red-500">- </span
          >{{ change.value }}
        </div>
        <div v-else class="text-[var(--muted-foreground)]">
          <span class="select-none">  </span>{{ change.value }}
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="border-t border-[var(--border)] bg-[var(--card)] px-4 py-3">
      <div v-if="error" class="mb-3 text-sm text-red-600">
        {{ error }}
      </div>
      <div v-if="applied" class="flex items-center gap-2 text-sm text-green-700 dark:text-green-400">
        <Check :size="16" />
        Modification appliquée et synchronisée
      </div>
      <div v-else-if="rejected" class="flex items-center gap-2 text-sm text-[var(--muted-foreground)]">
        <X :size="16" />
        Modification refusée
      </div>
      <div v-else class="flex items-center justify-end gap-2">
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] px-3 py-2 text-sm font-medium text-[var(--foreground)] transition hover:bg-[var(--accent)] disabled:opacity-40"
          :disabled="applying"
          @click="reject"
        >
          <X :size="14" />
          Refuser
        </button>
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-lg bg-[var(--primary)] px-3 py-2 text-sm font-medium text-[var(--primary-foreground)] transition hover:opacity-90 disabled:opacity-40"
          :disabled="applying"
          @click="applyEdit"
        >
          <Loader v-if="applying" :size="14" class="animate-spin" />
          <Check v-else :size="14" />
          Appliquer
        </button>
      </div>
    </div>
  </div>
</template>
