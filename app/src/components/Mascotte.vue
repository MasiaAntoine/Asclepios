<script setup lang="ts">
import wavingImg    from '@/assets/mascotte-waving.png'
import winkImg      from '@/assets/mascotte-wink.png'
import readingImg   from '@/assets/mascotte-reading.png'
import stethoImg    from '@/assets/mascotte-stethoscope.png'

const props = withDefaults(
  defineProps<{
    pose?: 'waving' | 'reading' | 'stethoscope' | 'wink'
  }>(),
  { pose: 'waving' },
)

const src = {
  waving:      wavingImg,
  wink:        winkImg,
  reading:     readingImg,
  stethoscope: stethoImg,
}
</script>

<template>
  <img
    :src="src[props.pose]"
    :alt="`Mascotte Asclepios — ${props.pose}`"
    draggable="false"
    aria-hidden="true"
  />
</template>
