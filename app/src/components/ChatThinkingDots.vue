<script setup lang="ts">
withDefaults(
  defineProps<{
    status?: string
  }>(),
  { status: '' },
)
</script>

<template>
  <div class="flex items-center gap-2.5" role="status" aria-live="polite">
    <span class="chat-dots" aria-hidden="true">
      <i />
      <i />
      <i />
    </span>
    <span class="text-[13px] text-[var(--muted-foreground)]">
      {{ status || 'Réflexion…' }}
    </span>
  </div>
</template>

<style scoped>
.chat-dots {
  display: inline-flex;
  align-items: flex-end;
  gap: 4px;
  height: 14px;
}

.chat-dots i {
  display: block;
  width: 6px;
  height: 6px;
  border-radius: 9999px;
  background: var(--primary);
  animation: chat-dot 1.05s ease-in-out infinite;
}

.chat-dots i:nth-child(2) {
  animation-delay: 0.16s;
}

.chat-dots i:nth-child(3) {
  animation-delay: 0.32s;
}

@keyframes chat-dot {
  0%,
  80%,
  100% {
    transform: translateY(0);
    opacity: 0.35;
  }
  40% {
    transform: translateY(-5px);
    opacity: 1;
  }
}
</style>
