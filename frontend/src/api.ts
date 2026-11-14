// Plain fetch. The session user goes in X-User; the backend maps it to a tenant.
export const USERS = ['sre-oncall', 'reviewer-dana', 'platform-lee'] as const
export type User = (typeof USERS)[number]
export const TENANT: Record<User, string> = { 'sre-oncall': 'acme-pay', 'reviewer-dana': 'acme-pay', 'platform-lee': 'globex' }

// Shapes follow docs/BRIEF.md section 6 (IDs arrive as strings).
export type Sim = { fraud_checks_enabled: boolean; deployment_version: string; checkout_error_rate: number; fraud_rate: number; incident_status: string }
export type Retrieved = { memory_id: string; version: number; score: number; text: string }
export type Variant = { actions: (string | null)[]; errors?: { run: number; type: string }[] }
export type Replay = {
  _id: string; runs_per_variant: number; status?: string; stable?: boolean
  baseline: Variant & { stability: number }
  ablations: (Variant & { removed_memory_id: string; flip_rate: number })[]
  culprit_memory_id: string | null
}
export type Verdict = {
  _id: string; memory_id: string | null; outcome: 'correct' | 'quarantine' | 'no_action'; reason: string
  proposed_text: string | null; status: string; approved_by: string | null; approved_at: string | null
  new_memory_id: string | null; memory_text: string | null; evidence_title: string | null; evidence_verified_by: string | null
}
export type Decision = {
  _id: string; tenant_id: string; user_id: string; task: string; retrieved: Retrieved[]
  action: string; rationale: string; sim_before: Sim; sim_after: Sim
  contested: { by: string; reason: string; at: string } | null
  replay?: Replay | null; verdict?: Verdict | null
}
export type Memory = { _id: string; tenant_id: string; text: string; score?: number }
export type AccessEntry = { user_id: string; kind: string; query: string; allowed: boolean; at: string }

export class ApiError extends Error {
  status: number
  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
  }
}

export async function api<T = unknown>(user: User, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { 'X-User': user, 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) {
    const text = await res.text()
    let detail = text
    try {
      const d = JSON.parse(text).detail
      if (typeof d === 'string') detail = d
    } catch { /* not JSON: show the raw body */ }
    throw new ApiError(res.status, `${res.status} ${detail || res.statusText}`)
  }
  return res.json()
}
