<script setup lang="ts">
withDefaults(
  defineProps<{
    open: boolean
    status?: string
  }>(),
  { status: '' },
)
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-opacity duration-300 ease-out"
      enter-from-class="opacity-0"
      leave-active-class="transition-opacity duration-400 ease-in"
      leave-to-class="opacity-0"
    >
      <div
        v-if="open"
        class="ai-forge fixed inset-0 z-[80] flex flex-col items-center justify-center px-6"
        role="status"
        aria-live="polite"
        aria-label="Génération du rapport"
      >
        <div class="pointer-events-none absolute inset-0 overflow-hidden">
          <div class="ai-forge-glow ai-forge-glow--a" />
          <div class="ai-forge-glow ai-forge-glow--b" />
        </div>

        <div class="relative h-[min(72vw,280px)] w-[min(72vw,280px)]">
          <svg
            class="h-full w-full"
            viewBox="0 0 280 280"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <defs>
              <linearGradient id="aiForgeStroke" x1="40" y1="40" x2="240" y2="240" gradientUnits="userSpaceOnUse">
                <stop stop-color="var(--primary)" stop-opacity="0.15" />
                <stop offset="0.5" stop-color="var(--primary)" stop-opacity="0.9" />
                <stop offset="1" stop-color="var(--accent)" stop-opacity="0.4" />
              </linearGradient>
              <linearGradient id="aiForgeCore" x1="110" y1="100" x2="170" y2="180" gradientUnits="userSpaceOnUse">
                <stop stop-color="oklch(0.72 0.12 165)" />
                <stop offset="1" stop-color="var(--primary)" />
              </linearGradient>
              <filter id="aiForgeBlur" x="-40%" y="-40%" width="180%" height="180%">
                <feGaussianBlur stdDeviation="4" />
              </filter>
            </defs>

            <g class="ai-forge-spin-rev" style="transform-origin: 140px 140px">
              <circle
                cx="140"
                cy="140"
                r="118"
                stroke="var(--primary)"
                stroke-opacity="0.18"
                stroke-width="1"
                stroke-dasharray="3 10"
              />
            </g>
            <g class="ai-forge-spin" style="transform-origin: 140px 140px">
              <circle
                cx="140"
                cy="140"
                r="96"
                stroke="url(#aiForgeStroke)"
                stroke-width="1.4"
                stroke-dasharray="18 14"
                stroke-linecap="round"
              />
            </g>
            <g class="ai-forge-spin-slow" style="transform-origin: 140px 140px">
              <circle
                cx="140"
                cy="140"
                r="74"
                stroke="var(--primary)"
                stroke-opacity="0.28"
                stroke-width="0.8"
              />
              <circle cx="140" cy="66" r="4" fill="var(--primary)" />
              <circle cx="206" cy="178" r="3" fill="var(--primary)" fill-opacity="0.7" />
              <circle cx="74" cy="178" r="3.5" fill="var(--accent)" />
            </g>

            <g class="ai-forge-orbit" style="transform-origin: 140px 140px">
              <polygon
                points="140,38 146,50 140,46 134,50"
                fill="var(--primary)"
                opacity="0.85"
              />
              <rect x="214" y="128" width="10" height="10" rx="2" fill="var(--primary)" opacity="0.55" transform="rotate(20 219 133)" />
              <circle cx="58" cy="120" r="3" fill="var(--primary)" />
              <path d="M86 214 l6 0 l0 6 l-6 0 z" fill="var(--accent)" opacity="0.8" />
            </g>

            <circle
              cx="140"
              cy="140"
              r="52"
              fill="var(--primary)"
              fill-opacity="0.12"
              filter="url(#aiForgeBlur)"
              class="ai-forge-pulse"
            />

            <!-- Document qui se construit -->
            <g transform="translate(98 86)">
              <rect
                x="0"
                y="0"
                width="84"
                height="108"
                rx="8"
                fill="var(--card)"
                stroke="var(--primary)"
                stroke-opacity="0.45"
                stroke-width="1.4"
                class="ai-forge-sheet"
              />
              <path
                d="M56 0 v18 a8 8 0 0 0 8 8 h20"
                stroke="var(--primary)"
                stroke-opacity="0.4"
                stroke-width="1.2"
                fill="var(--accent)"
                fill-opacity="0.35"
              />
              <g class="ai-forge-lines">
                <rect x="12" y="28" width="48" height="4" rx="2" fill="var(--primary)" opacity="0.85" />
                <rect x="12" y="40" width="60" height="3.2" rx="1.6" fill="var(--primary)" opacity="0.45" />
                <rect x="12" y="50" width="54" height="3.2" rx="1.6" fill="var(--primary)" opacity="0.38" />
                <rect x="12" y="60" width="42" height="3.2" rx="1.6" fill="var(--primary)" opacity="0.32" />
                <rect x="12" y="74" width="58" height="3.2" rx="1.6" fill="var(--primary)" opacity="0.28" />
                <rect x="12" y="84" width="36" height="3.2" rx="1.6" fill="var(--primary)" opacity="0.22" />
              </g>
            </g>

            <!-- Particules qui convergent -->
            <g class="ai-forge-bits">
              <circle cx="48" cy="72" r="2" fill="var(--primary)" />
              <circle cx="232" cy="88" r="1.6" fill="var(--primary)" />
              <circle cx="44" cy="200" r="1.8" fill="var(--accent)" />
              <circle cx="228" cy="208" r="2.2" fill="var(--primary)" />
              <rect x="36" y="140" width="6" height="6" rx="1" fill="var(--primary)" opacity="0.5" />
              <rect x="238" y="148" width="5" height="5" rx="1" fill="var(--primary)" opacity="0.45" />
            </g>
          </svg>
        </div>

        <p class="relative mt-6 text-center text-sm font-semibold tracking-wide text-[var(--foreground)]">
          L’IA rédige ton rapport
        </p>
        <p
          class="relative mt-2 min-h-[1.25rem] max-w-sm text-center text-xs text-[var(--muted-foreground)]"
        >
          {{ status || 'Analyse de la conversation…' }}
        </p>
        <div class="relative mt-5 flex gap-1.5" aria-hidden="true">
          <span class="ai-forge-dot" />
          <span class="ai-forge-dot" style="animation-delay: 0.18s" />
          <span class="ai-forge-dot" style="animation-delay: 0.36s" />
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.ai-forge {
  background:
    radial-gradient(ellipse 80% 60% at 50% 42%, color-mix(in oklch, var(--primary) 22%, transparent), transparent 70%),
    color-mix(in oklch, var(--background) 88%, transparent);
  backdrop-filter: blur(14px);
}

.ai-forge-glow {
  position: absolute;
  border-radius: 9999px;
  filter: blur(40px);
  opacity: 0.45;
}

.ai-forge-glow--a {
  width: 18rem;
  height: 18rem;
  left: 8%;
  top: 22%;
  background: color-mix(in oklch, var(--primary) 50%, transparent);
  animation: ai-forge-drift 8s ease-in-out infinite;
}

.ai-forge-glow--b {
  width: 14rem;
  height: 14rem;
  right: 10%;
  bottom: 18%;
  background: color-mix(in oklch, var(--accent) 70%, transparent);
  animation: ai-forge-drift 10s ease-in-out infinite reverse;
}

.ai-forge-spin {
  animation: ai-forge-rotate 14s linear infinite;
}

.ai-forge-spin-slow {
  animation: ai-forge-rotate 22s linear infinite;
}

.ai-forge-spin-rev {
  animation: ai-forge-rotate 18s linear infinite reverse;
}

.ai-forge-orbit {
  animation: ai-forge-rotate 9s linear infinite;
}

.ai-forge-pulse {
  transform-origin: 140px 140px;
  animation: ai-forge-pulse 2.4s ease-in-out infinite;
}

.ai-forge-sheet {
  animation: ai-forge-sheet 2.8s ease-in-out infinite;
  transform-origin: 42px 54px;
}

.ai-forge-lines rect {
  animation: ai-forge-line 2.2s ease-in-out infinite;
  transform-box: fill-box;
  transform-origin: left center;
}

.ai-forge-lines rect:nth-child(2) { animation-delay: 0.12s; }
.ai-forge-lines rect:nth-child(3) { animation-delay: 0.24s; }
.ai-forge-lines rect:nth-child(4) { animation-delay: 0.36s; }
.ai-forge-lines rect:nth-child(5) { animation-delay: 0.48s; }
.ai-forge-lines rect:nth-child(6) { animation-delay: 0.6s; }

.ai-forge-bits circle,
.ai-forge-bits rect {
  animation: ai-forge-bit 2.6s ease-in-out infinite;
}

.ai-forge-bits circle:nth-child(2),
.ai-forge-bits rect:nth-child(6) {
  animation-delay: 0.4s;
}

.ai-forge-bits circle:nth-child(3) {
  animation-delay: 0.8s;
}

.ai-forge-bits circle:nth-child(4) {
  animation-delay: 1.2s;
}

.ai-forge-dot {
  display: block;
  height: 6px;
  width: 6px;
  border-radius: 9999px;
  background: var(--primary);
  animation: ai-forge-dot 1s ease-in-out infinite;
}

@keyframes ai-forge-rotate {
  to {
    transform: rotate(360deg);
  }
}

@keyframes ai-forge-pulse {
  0%,
  100% {
    transform: scale(1);
    opacity: 0.7;
  }
  50% {
    transform: scale(1.12);
    opacity: 1;
  }
}

@keyframes ai-forge-sheet {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-3px);
  }
}

@keyframes ai-forge-line {
  0%,
  100% {
    transform: scaleX(0.35);
    opacity: 0.25;
  }
  50% {
    transform: scaleX(1);
    opacity: 1;
  }
}

@keyframes ai-forge-bit {
  0%,
  100% {
    transform: translate(0, 0);
    opacity: 0.25;
  }
  50% {
    transform: translate(12px, 10px);
    opacity: 1;
  }
}

@keyframes ai-forge-drift {
  0%,
  100% {
    transform: translate(0, 0);
  }
  50% {
    transform: translate(24px, -18px);
  }
}

@keyframes ai-forge-dot {
  0%,
  100% {
    opacity: 0.25;
    transform: translateY(0);
  }
  50% {
    opacity: 1;
    transform: translateY(-4px);
  }
}
</style>
