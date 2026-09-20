<script setup lang="ts">
import { computed, useId } from 'vue'
import { emotionDef, type EmotionId } from '@/lib/emotions'

const props = withDefaults(
  defineProps<{
    emotion: EmotionId
    active?: boolean
    size?: number
    title?: string
  }>(),
  {
    active: false,
    size: 56,
    title: '',
  },
)

const uid = useId().replace(/:/g, '')
const def = computed(() => emotionDef(props.emotion))
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 128 128"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    role="img"
    :aria-label="title || def?.label || emotion"
    :title="title || def?.label"
    :class="active ? '' : 'grayscale contrast-[0.9] opacity-[0.48]'"
    class="overflow-visible transition-[filter,opacity,transform] duration-200"
  >
    <defs>
      <linearGradient :id="`owl-bg-${uid}`" x1="20" y1="8" x2="110" y2="124" gradientUnits="userSpaceOnUse">
        <stop stop-color="#249A82" />
        <stop offset="1" stop-color="#176B5C" />
      </linearGradient>
      <linearGradient :id="`owl-head-${uid}`" x1="40" y1="14" x2="92" y2="78" gradientUnits="userSpaceOnUse">
        <stop stop-color="#3EC9A8" />
        <stop offset="1" stop-color="#1FA888" />
      </linearGradient>
      <clipPath :id="`owl-clip-${uid}`">
        <rect x="4" y="4" width="120" height="120" rx="28" />
      </clipPath>
    </defs>

    <g :clip-path="`url(#owl-clip-${uid})`">
      <rect x="4" y="4" width="120" height="120" rx="28" :fill="`url(#owl-bg-${uid})`" />

      <!-- Coat -->
      <path
        d="M18 126 V92 C18 78 34 70 64 70 C94 70 110 78 110 92 V126 Z"
        fill="#F8FBFB"
      />
      <path d="M64 70 L52 126 H76 Z" fill="#EEF6F4" />
      <path d="M40 86 L54 126" stroke="#D7E8E3" stroke-width="2.2" stroke-linecap="round" />
      <path d="M88 86 L74 126" stroke="#D7E8E3" stroke-width="2.2" stroke-linecap="round" />
      <rect x="70" y="96" width="22" height="26" rx="4" fill="#E7F3EF" />
      <!-- Caduceus -->
      <g transform="translate(81 103)" fill="#1FA888">
        <rect x="4.2" y="0" width="2.4" height="16" rx="1.2" />
        <path d="M5.4 3.2 C9.8 1.2 12.2 5.4 8.6 7.4 C12.2 9.2 9.6 13.6 5.4 11.4" fill="none" stroke="#1FA888" stroke-width="1.7" stroke-linecap="round" />
        <path d="M5.4 3.2 C1 1.2 -1.4 5.4 2.2 7.4 C-1.4 9.2 1.2 13.6 5.4 11.4" fill="none" stroke="#1FA888" stroke-width="1.7" stroke-linecap="round" />
        <circle cx="5.4" cy="1.2" r="1.6" />
      </g>

      <!-- Head -->
      <ellipse cx="64" cy="50" rx="46" ry="40" :fill="`url(#owl-head-${uid})`" />
      <!-- Side cheeks / ears -->
      <ellipse cx="24" cy="48" rx="12" ry="16" :fill="`url(#owl-head-${uid})`" />
      <ellipse cx="104" cy="48" rx="12" ry="16" :fill="`url(#owl-head-${uid})`" />
      <!-- Tuft -->
      <ellipse cx="64" cy="16" rx="10" ry="14" fill="#2BB89A" />
      <ellipse cx="56" cy="18" rx="7" ry="11" fill="#249E86" transform="rotate(-18 56 18)" />
      <ellipse cx="72" cy="18" rx="7" ry="11" fill="#249E86" transform="rotate(18 72 18)" />

      <!-- Face disk -->
      <ellipse cx="64" cy="54" rx="34" ry="28" fill="#F7F1E4" />

      <!-- Green chest feathers under beak -->
      <ellipse cx="64" cy="78" rx="16" ry="10" fill="#2BB89A" />

      <!-- Cheeks -->
      <ellipse
        v-if="emotion === 'joie' || emotion === 'soulagement' || emotion === 'espoir'"
        cx="38"
        cy="62"
        rx="7"
        ry="4.5"
        fill="#F4C4B0"
        opacity="0.85"
      />
      <ellipse
        v-if="emotion === 'joie' || emotion === 'soulagement' || emotion === 'espoir'"
        cx="90"
        cy="62"
        rx="7"
        ry="4.5"
        fill="#F4C4B0"
        opacity="0.85"
      />
      <ellipse
        v-if="emotion === 'colere'"
        cx="38"
        cy="60"
        rx="7"
        ry="4"
        fill="#E8A090"
        opacity="0.7"
      />
      <ellipse
        v-if="emotion === 'colere'"
        cx="90"
        cy="60"
        rx="7"
        ry="4"
        fill="#E8A090"
        opacity="0.7"
      />

      <!-- Brows -->
      <g v-if="emotion === 'calme' || emotion === 'soulagement'" stroke="#1C6F60" stroke-width="3.2" stroke-linecap="round" fill="none">
        <path d="M40 38 Q50 34 58 38" />
        <path d="M70 38 Q78 34 88 38" />
      </g>
      <g v-else-if="emotion === 'joie'" stroke="#1C6F60" stroke-width="3.2" stroke-linecap="round" fill="none">
        <path d="M40 40 Q50 32 58 38" />
        <path d="M70 38 Q78 32 88 40" />
      </g>
      <g v-else-if="emotion === 'tristesse'" stroke="#1C6F60" stroke-width="3.2" stroke-linecap="round" fill="none">
        <path d="M40 36 Q50 42 58 40" />
        <path d="M70 40 Q78 42 88 36" />
      </g>
      <g v-else-if="emotion === 'anxiete'" stroke="#1C6F60" stroke-width="3.2" stroke-linecap="round" fill="none">
        <path d="M40 40 Q48 30 58 36" />
        <path d="M70 36 Q80 30 88 40" />
      </g>
      <g v-else-if="emotion === 'colere'" stroke="#1C6F60" stroke-width="3.4" stroke-linecap="round" fill="none">
        <path d="M40 34 L58 40" />
        <path d="M88 34 L70 40" />
      </g>
      <g v-else-if="emotion === 'espoir'" stroke="#1C6F60" stroke-width="3.2" stroke-linecap="round" fill="none">
        <path d="M40 40 Q50 30 58 36" />
        <path d="M70 36 Q78 30 88 40" />
      </g>
      <g v-else-if="emotion === 'fatigue'" stroke="#1C6F60" stroke-width="3" stroke-linecap="round" fill="none">
        <path d="M40 40 Q50 38 58 40" />
        <path d="M70 40 Q78 38 88 40" />
      </g>

      <!-- Eyes -->
      <g v-if="emotion === 'joie'">
        <path d="M34 52 Q46 62 58 52" stroke="#1C3D38" stroke-width="4" stroke-linecap="round" fill="none" />
        <path d="M70 52 Q82 62 94 52" stroke="#1C3D38" stroke-width="4" stroke-linecap="round" fill="none" />
      </g>
      <g v-else-if="emotion === 'soulagement'">
        <path d="M36 54 Q46 58 56 54" stroke="#1C3D38" stroke-width="3.6" stroke-linecap="round" fill="none" />
        <path d="M72 54 Q82 58 92 54" stroke="#1C3D38" stroke-width="3.6" stroke-linecap="round" fill="none" />
      </g>
      <g v-else-if="emotion === 'fatigue'">
        <ellipse cx="46" cy="54" rx="12" ry="8" fill="#fff" />
        <ellipse cx="82" cy="54" rx="12" ry="8" fill="#fff" />
        <ellipse cx="46" cy="56" rx="6" ry="4.5" fill="#1C3D38" />
        <ellipse cx="82" cy="56" rx="6" ry="4.5" fill="#1C3D38" />
        <path d="M34 50 Q46 46 58 50" stroke="#1FA888" stroke-width="5" stroke-linecap="round" fill="none" />
        <path d="M70 50 Q82 46 94 50" stroke="#1FA888" stroke-width="5" stroke-linecap="round" fill="none" />
      </g>
      <g v-else>
        <ellipse cx="46" cy="54" :rx="emotion === 'anxiete' ? 13 : 12" :ry="emotion === 'colere' ? 9 : 13" fill="#fff" />
        <ellipse cx="82" cy="54" :rx="emotion === 'anxiete' ? 13 : 12" :ry="emotion === 'colere' ? 9 : 13" fill="#fff" />
        <ellipse
          :cx="emotion === 'espoir' ? 46 : emotion === 'tristesse' ? 46 : 47"
          :cy="emotion === 'espoir' ? 50 : emotion === 'tristesse' ? 58 : emotion === 'colere' ? 55 : 54"
          :rx="emotion === 'anxiete' ? 4.5 : 6.2"
          :ry="emotion === 'anxiete' ? 4.5 : 6.8"
          fill="#1C3D38"
        />
        <ellipse
          :cx="emotion === 'espoir' ? 82 : emotion === 'tristesse' ? 82 : 81"
          :cy="emotion === 'espoir' ? 50 : emotion === 'tristesse' ? 58 : emotion === 'colere' ? 55 : 54"
          :rx="emotion === 'anxiete' ? 4.5 : 6.2"
          :ry="emotion === 'anxiete' ? 4.5 : 6.8"
          fill="#1C3D38"
        />
        <circle
          :cx="emotion === 'espoir' ? 43 : 43.5"
          :cy="emotion === 'espoir' ? 46 : emotion === 'tristesse' ? 54 : 50"
          r="2.4"
          fill="#fff"
        />
        <circle
          :cx="emotion === 'espoir' ? 79 : 77.5"
          :cy="emotion === 'espoir' ? 46 : emotion === 'tristesse' ? 54 : 50"
          r="2.4"
          fill="#fff"
        />
      </g>

      <!-- Tear -->
      <path
        v-if="emotion === 'tristesse'"
        d="M94 64 C96 70 93 76 90 76 C87 76 86 70 88 64 C90 61 93 61 94 64 Z"
        fill="#7EB4DE"
      />

      <!-- Sparkle (espoir) -->
      <g v-if="emotion === 'espoir'" fill="#F0B429">
        <path d="M104 22 L106.2 27.4 L112 28 L107.4 31.6 L108.8 37 L104 33.8 L99.2 37 L100.6 31.6 L96 28 L101.8 27.4 Z" />
      </g>

      <!-- Zzz (fatigue) -->
      <g v-if="emotion === 'fatigue'" fill="#F7F1E4" opacity="0.92">
        <path d="M96 26 h10 l-10 8 h10" stroke="#F7F1E4" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round" />
        <path d="M108 16 h7 l-7 6 h7" stroke="#F7F1E4" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round" />
      </g>

      <!-- Beak -->
      <g v-if="emotion === 'joie' || emotion === 'calme' || emotion === 'espoir' || emotion === 'soulagement'">
        <ellipse cx="64" cy="70" rx="8" ry="7" fill="#F0B429" />
        <ellipse cx="64" cy="71.5" rx="5" ry="3.2" fill="#C97816" opacity="0.85" />
      </g>
      <g v-else-if="emotion === 'tristesse'">
        <path d="M56 72 Q64 66 72 72 Q64 70 56 72 Z" fill="#F0B429" />
      </g>
      <g v-else-if="emotion === 'colere'">
        <path d="M56 68 L64 76 L72 68 Q64 70 56 68 Z" fill="#F0B429" />
      </g>
      <g v-else-if="emotion === 'anxiete'">
        <ellipse cx="64" cy="70" rx="5" ry="6" fill="#F0B429" />
        <ellipse cx="64" cy="71" rx="2.4" ry="2.8" fill="#1C3D38" opacity="0.35" />
      </g>
      <g v-else>
        <ellipse cx="64" cy="70" rx="7" ry="8" fill="#F0B429" />
        <ellipse cx="64" cy="72" rx="4" ry="3.5" fill="#C97816" opacity="0.7" />
      </g>
    </g>
  </svg>
</template>
