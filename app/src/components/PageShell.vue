<script setup lang="ts">
withDefaults(
  defineProps<{
    /** Titre de page (sinon slot #title) */
    title?: string
    /** Sous-titre / description (sinon slot #description) */
    description?: string
    /** Largeur max du contenu centré */
    maxWidth?: 'narrow' | 'sm' | 'md' | 'lg' | 'xl' | 'full'
    /** Pas de scroll interne (contenu gère lui-même) */
    noScroll?: boolean
    /** Pas de padding / max-width sur le corps (ex. chat plein écran) */
    flush?: boolean
  }>(),
  {
    maxWidth: 'lg',
    noScroll: false,
    flush: false,
  },
)

const maxWidthClass: Record<string, string> = {
  narrow: 'max-w-2xl',
  sm: 'max-w-3xl',
  md: 'max-w-4xl',
  lg: 'max-w-5xl',
  xl: 'max-w-6xl',
  full: 'max-w-none',
}
</script>

<template>
  <div class="flex h-full flex-col overflow-hidden">
    <!-- Header uniforme -->
    <header
      v-if="$slots.header || title || $slots.title || description || $slots.description || $slots.actions"
      class="shrink-0 border-b border-[var(--border)] bg-[var(--card)] px-8 py-6"
    >
      <slot name="header">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div class="min-w-0 flex-1">
            <slot name="title">
              <h1
                v-if="title"
                class="text-2xl font-bold text-[var(--foreground)]"
              >
                {{ title }}
              </h1>
            </slot>
            <slot name="description">
              <p
                v-if="description"
                class="mt-0.5 text-sm text-[var(--muted-foreground)]"
              >
                {{ description }}
              </p>
            </slot>
          </div>
          <div
            v-if="$slots.actions"
            class="flex flex-wrap items-center gap-2"
          >
            <slot name="actions" />
          </div>
        </div>
      </slot>
    </header>

    <!-- Corps uniforme -->
    <div
      :class="[
        'flex-1',
        noScroll || flush ? 'overflow-hidden' : 'overflow-y-auto',
        flush ? '' : 'px-8 py-8',
        noScroll && !flush ? 'flex min-h-0 flex-col' : '',
      ]"
    >
      <div
        v-if="flush"
        class="h-full"
      >
        <slot />
      </div>
      <div
        v-else
        :class="[
          'mx-auto w-full',
          maxWidthClass[maxWidth],
          noScroll ? 'flex h-full min-h-0 flex-col' : '',
        ]"
      >
        <slot />
      </div>
    </div>
  </div>
</template>
