<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import logoIconUrl from '@/assets/logo-icon.png'
import { useAuth } from '@/composables/useAuth'
import { KeyRound, Loader2, Lock } from '@lucide/vue'

const password = ref('')
const totpCode = ref('')
const totpInput = ref<HTMLInputElement | null>(null)
const { login, verifyTotp, loading, error, pendingTotp } = useAuth()
const router = useRouter()
const route = useRoute()

watch(pendingTotp, async (pending) => {
  if (!pending) return
  await nextTick()
  totpInput.value?.focus()
})

async function onPasswordSubmit() {
  if (!password.value || loading.value) return
  const ok = await login(password.value)
  if (!ok) return
  totpCode.value = ''
}

async function onTotpSubmit() {
  if (totpCode.value.replace(/\D/g, '').length < 6 || loading.value) return
  const ok = await verifyTotp(totpCode.value)
  if (!ok) return
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
  await router.replace(redirect || '/')
}

function backToPassword() {
  pendingTotp.value = false
  totpCode.value = ''
  error.value = null
}
</script>

<template>
  <div
    class="flex min-h-dvh items-center justify-center bg-[var(--background)] px-4 py-10"
  >
    <div
      class="w-full max-w-sm rounded-2xl border border-[var(--border)] bg-[var(--card)] p-8 shadow-sm"
    >
      <div class="mb-8 flex flex-col items-center text-center">
        <img
          :src="logoIconUrl"
          alt="Asclepios"
          class="mb-4 h-16 w-16 rounded-2xl object-cover shadow-sm"
        />
        <h1 class="text-xl font-bold tracking-tight text-[var(--foreground)]">Asclepios</h1>
        <p class="mt-1 text-sm text-[var(--muted-foreground)]">
          {{ pendingTotp ? 'Code Google Authenticator' : 'Connexion au dossier médical' }}
        </p>
      </div>

      <form
        v-if="!pendingTotp"
        class="space-y-4"
        @submit.prevent="onPasswordSubmit"
      >
        <label class="block text-xs font-medium text-[var(--muted-foreground)]">
          Mot de passe
          <div class="relative mt-1.5">
            <Lock
              :size="15"
              class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]"
            />
            <input
              v-model="password"
              type="password"
              autocomplete="current-password"
              autofocus
              class="w-full rounded-xl border border-[var(--border)] bg-[var(--background)] py-2.5 pl-9 pr-3 text-sm text-[var(--foreground)] outline-none ring-[var(--primary)] focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary)]/20"
              placeholder="••••••••"
            />
          </div>
        </label>

        <p v-if="error" class="text-sm text-red-600">{{ error }}</p>

        <button
          type="submit"
          class="flex w-full items-center justify-center gap-2 rounded-xl bg-[var(--primary)] px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-[var(--primary)]/90 disabled:opacity-50"
          :disabled="!password || loading"
        >
          <Loader2 v-if="loading" :size="16" class="animate-spin" />
          {{ loading ? 'Vérification…' : 'Continuer' }}
        </button>
      </form>

      <form
        v-else
        class="space-y-4"
        @submit.prevent="onTotpSubmit"
      >
        <label class="block text-xs font-medium text-[var(--muted-foreground)]">
          Code à 6 chiffres
          <div class="relative mt-1.5">
            <KeyRound
              :size="15"
              class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]"
            />
            <input
              ref="totpInput"
              v-model="totpCode"
              type="text"
              inputmode="numeric"
              autocomplete="one-time-code"
              maxlength="8"
              class="w-full rounded-xl border border-[var(--border)] bg-[var(--background)] py-2.5 pl-9 pr-3 text-center text-lg tracking-[0.35em] text-[var(--foreground)] outline-none ring-[var(--primary)] focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary)]/20"
              placeholder="••••••"
            />
          </div>
        </label>

        <p v-if="error" class="text-sm text-red-600">{{ error }}</p>

        <button
          type="submit"
          class="flex w-full items-center justify-center gap-2 rounded-xl bg-[var(--primary)] px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-[var(--primary)]/90 disabled:opacity-50"
          :disabled="totpCode.replace(/\D/g, '').length < 6 || loading"
        >
          <Loader2 v-if="loading" :size="16" class="animate-spin" />
          {{ loading ? 'Vérification…' : 'Valider' }}
        </button>

        <button
          type="button"
          class="w-full text-center text-xs text-[var(--muted-foreground)] hover:underline"
          @click="backToPassword"
        >
          Retour
        </button>
      </form>
    </div>
  </div>
</template>
