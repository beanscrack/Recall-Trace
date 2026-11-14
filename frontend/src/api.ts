// Plain fetch. The session user goes in X-User; the backend maps it to a tenant.
export const USERS = ['sre-oncall', 'reviewer-dana', 'platform-lee'] as const
export type User = (typeof USERS)[number]

export async function api<T = any>(user: User, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { 'X-User': user, 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
  return res.json()
}
