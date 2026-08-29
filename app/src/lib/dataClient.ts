/** Base URL for private clinical data — never bundled into the app. */
export const DATA_BASE = (import.meta.env.VITE_DATA_BASE as string | undefined) || '/data'

export function dataUrl(relativePath: string): string {
  const clean = relativePath.replace(/^\/+/, '')
  return `${DATA_BASE.replace(/\/$/, '')}/${clean}`
}

export async function fetchText(relativePath: string): Promise<string> {
  const res = await fetch(dataUrl(relativePath))
  if (!res.ok) {
    throw new Error(`Impossible de charger ${relativePath} (${res.status})`)
  }
  return res.text()
}

export async function fetchJson<T>(relativePath: string): Promise<T> {
  const res = await fetch(dataUrl(relativePath))
  if (!res.ok) {
    throw new Error(`Impossible de charger ${relativePath} (${res.status})`)
  }
  return res.json() as Promise<T>
}
