import { computed, ref } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import { useRouter } from 'vue-router'

export function useMobileSheet() {
  const router = useRouter()
  const isMobile = useMediaQuery('(max-width: 767px)')
  const itemId = ref<string | null>(null)

  const sheetOpen = computed({
    get: () => Boolean(itemId.value) && isMobile.value,
    set: (value: boolean) => {
      if (!value) itemId.value = null
    },
  })

  function openItem(id: string, desktopPath: string) {
    if (isMobile.value) {
      itemId.value = id
      return
    }
    void router.push(desktopPath)
  }

  return { isMobile, itemId, sheetOpen, openItem }
}
