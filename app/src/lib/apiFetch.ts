/** Fetch API Asclepios avec cookie de session. */

export async function apiFetch(input: string, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers)
  return fetch(input, {
    ...init,
    credentials: 'include',
    headers,
  })
}
