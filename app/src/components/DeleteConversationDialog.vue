<script setup lang="ts">
import { ref } from "vue";
import { AlertTriangle, Loader, Trash2 } from "@lucide/vue";
import Dialog from "@/components/ui/Dialog.vue";

interface Props {
  conversationTitle: string;
  isLinkedToReport: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  confirm: [];
  cancel: [];
}>();

const open = defineModel<boolean>("open", { default: false });
const deleting = ref(false);

async function handleConfirm() {
  deleting.value = true;
  emit("confirm");
  // Le parent fermera la dialog après le succès
}

function handleCancel() {
  open.value = false;
  emit("cancel");
}
</script>

<template>
  <Dialog v-model:open="open" class="max-w-md">
    <template #header>
      <div class="flex items-center gap-2.5">
        <div
          class="flex h-10 w-10 items-center justify-center rounded-full"
          :class="
            isLinkedToReport
              ? 'bg-red-500/10 text-red-600'
              : 'bg-amber-500/10 text-amber-600'
          "
        >
          <AlertTriangle :size="20" />
        </div>
        <div>
          <h2 class="text-base font-semibold text-[var(--foreground)]">
            {{ isLinkedToReport ? "Suppression impossible" : "Supprimer la conversation" }}
          </h2>
        </div>
      </div>
    </template>

    <!-- Content -->
    <div class="px-6 py-5">
      <template v-if="isLinkedToReport">
        <p class="text-sm leading-relaxed text-[var(--foreground)]">
          Cette conversation est <strong>liée à un rapport médical</strong> et ne peut pas
          être supprimée.
        </p>
        <div
          class="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3.5 py-3 text-xs text-amber-800 dark:border-amber-900/30 dark:bg-amber-950/30 dark:text-amber-300"
        >
          <p class="font-medium">Pourquoi ?</p>
          <p class="mt-1 leading-relaxed">
            Les conversations liées à des rapports font partie du dossier médical et sont
            protégées contre la suppression accidentelle pour préserver l'historique
            clinique.
          </p>
        </div>
      </template>

      <template v-else>
        <p class="text-sm leading-relaxed text-[var(--foreground)]">
          Confirmes-tu la suppression définitive de cette conversation ?
        </p>
        <div class="mt-3 rounded-lg bg-[var(--muted)]/50 px-3.5 py-2.5">
          <p class="text-xs font-medium text-[var(--muted-foreground)]">
            Conversation
          </p>
          <p class="mt-0.5 text-sm font-medium text-[var(--foreground)]">
            {{ conversationTitle }}
          </p>
        </div>
        <p class="mt-4 text-xs text-[var(--muted-foreground)]">
          Cette action est irréversible. La conversation sera supprimée localement et sur
          le serveur OVH lors de la prochaine synchronisation.
        </p>
      </template>
    </div>

    <!-- Footer -->
    <div
      class="flex items-center justify-end gap-2 border-t border-[var(--border)] px-6 py-4"
    >
      <template v-if="isLinkedToReport">
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-foreground)] transition hover:opacity-90"
          @click="handleCancel"
        >
          Fermer
        </button>
      </template>
      <template v-else>
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--foreground)] transition hover:bg-[var(--accent)] disabled:opacity-40"
          :disabled="deleting"
          @click="handleCancel"
        >
          Annuler
        </button>
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-700 disabled:opacity-40"
          :disabled="deleting"
          @click="handleConfirm"
        >
          <Loader v-if="deleting" :size="14" class="animate-spin" />
          <Trash2 v-else :size="14" />
          {{ deleting ? "Suppression…" : "Supprimer" }}
        </button>
      </template>
    </div>
  </Dialog>
</template>
