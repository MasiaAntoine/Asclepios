<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import HubSubnav from '@/components/HubSubnav.vue'
import { hubForPath } from '@/lib/hubs'

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
    /** Sans chrome (hub, header, padding) — pour embarquer dans une feuille mobile */
    plain?: boolean
  }>(),
  {
    maxWidth: 'lg',
    noScroll: false,
    flush: false,
    plain: false,
  },
)

const route = useRoute()
const hub = computed(() => hubForPath(route.path))

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
  <div v-if="plain" class="min-h-0">
    <slot />
  </div>
  <div v-else class="flex h-full min-h-0 flex-col overflow-hidden">
    <header
      v-if="$slots.header || hub || title || $slots.title || description || $slots.description || $slots.actions"
      class="min-w-0 shrink-0 overflow-x-hidden border-b border-[var(--border)] bg-[var(--card)] px-4 py-3 sm:px-6 sm:py-4 md:px-8"
    >
      <slot name="header">
        <div class="flex min-w-0 flex-col gap-3">
          <HubSubnav v-if="hub" :hub="hub" />
          <div
            v-if="(!hub && (title || $slots.title || description || $slots.description)) || $slots.actions || description || $slots.description"
            class="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-start sm:justify-between sm:gap-4"
          >
            <div v-if="!hub" class="min-w-0 flex-1">
              <slot name="title">
                <h1
                  v-if="title"
                  class="hidden text-2xl font-bold text-[var(--foreground)] md:block"
                >
                  {{ title }}
                </h1>
              </slot>
              <slot name="description">
                <p
                  v-if="description"
                  class="text-sm text-[var(--muted-foreground)] md:mt-0.5"
                >
                  {{ description }}
                </p>
              </slot>
            </div>
            <div v-else-if="description || $slots.description" class="min-w-0 flex-1">
              <slot name="description">
                <p
                  v-if="description"
                  class="text-sm text-[var(--muted-foreground)]"
                >
                  {{ description }}
                </p>
              </slot>
            </div>
            <div
              v-if="$slots.actions"
              class="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:flex-wrap sm:items-center"
            >
              <slot name="actions" />
            </div>
          </div>
        </div>
      </slot>
    </header>

    <div
      :class="[
        'min-h-0 flex-1',
        noScroll || flush ? 'overflow-hidden' : 'overflow-y-auto overscroll-contain',
        flush ? '' : 'px-4 py-4 sm:px-6 sm:py-6 md:px-8 md:py-8',
        noScroll && !flush ? 'flex min-h-0 flex-col' : '',
        flush || noScroll ? '' : 'pb-4 md:pb-8',
      ]"
    >
      <div
        v-if="flush"
        class="h-full min-h-0"
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
