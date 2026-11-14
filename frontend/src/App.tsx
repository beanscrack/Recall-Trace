import { useEffect, useRef, useState, type ReactNode } from 'react'
import {
  api, ApiError, TENANT, USERS,
  type AccessEntry, type Decision, type Memory, type Replay, type Sim, type User, type Verdict,
} from './api'

// One page, top to bottom in demo order (brief section 12). A section stays dimmed until its step happens.
const TASK =
  'Checkout API 5xx rate is 18% and rising. Fraud-check service p99 latency is 4.2s. Deploy v2.4.1 went out 10 minutes ago. Choose one action.'
const FRAUD_RED = 0.02
const STORE = 'recalltrace.case'

const pct = (n: number, digits = 1) => `${(n * 100).toFixed(digits)}%`
// Timestamps re-read from Mongo arrive without an offset; they are UTC.
const hhmm = (iso: string) => new Date(/Z|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
const short = (id: string) => id.slice(-6)
const isBad = (d: Decision) => d.sim_after.fraud_rate > FRAUD_RED

function useStep() {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const run = async (fn: () => Promise<void>) => {
    setBusy(true)
    setErr('')
    try {
      await fn()
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }
  return { busy, err, run }
}

/** Counts from the previous value to the new one in under 200ms. */
function Count({ value, fmt, fromZero }: { value: number; fmt: (n: number) => string; fromZero?: boolean }) {
  const [shown, setShown] = useState(fromZero ? 0 : value)
  const last = useRef(fromZero ? 0 : value)
  useEffect(() => {
    const start = last.current
    const t0 = performance.now()
    let raf = 0
    const tick = (t: number) => {
      const p = Math.min(1, (t - t0) / 180)
      last.current = start + (value - start) * p
      setShown(last.current)
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [value])
  return <>{fmt(shown)}</>
}

/** Honest progress text for the 3-6s calls: what is running and for how long. */
function Wait({ text }: { text: string }) {
  const [s, setS] = useState(0)
  useEffect(() => {
    const id = setInterval(() => setS((n) => n + 1), 1000)
    return () => clearInterval(id)
  }, [])
  return <p className="font-mono text-sm text-dim">{text} {s}s</p>
}

function Label({ children }: { children: ReactNode }) {
  return <div className="text-xs uppercase tracking-[0.14em] text-dim">{children}</div>
}

function Section({ n, title, active, children }: { n: string; title: string; active: boolean; children?: ReactNode }) {
  // Bring a section into view when its step happens, so the presenter never has to scroll.
  const ref = useRef<HTMLElement>(null)
  const wasActive = useRef(active)
  useEffect(() => {
    if (active && !wasActive.current) ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    wasActive.current = active
  }, [active])
  return (
    <section ref={ref} className={`mt-16 scroll-mt-6 transition-opacity duration-150 ${active ? '' : 'opacity-30'}`}>
      <div className="mb-5 flex items-baseline gap-3 border-b border-line pb-3 text-xs uppercase tracking-[0.14em] text-dim">
        <span className="font-mono">{n}</span>
        <span>{title}</span>
      </div>
      {active && children}
    </section>
  )
}

function Btn({ primary, busy, busyLabel = 'Running…', disabled, onClick, children }: {
  primary?: boolean; busy?: boolean; busyLabel?: string; disabled?: boolean; onClick: () => void; children: ReactNode
}) {
  const look = primary ? 'bg-white text-black border-white' : 'bg-transparent text-fg border-line hover:border-dim'
  return (
    <button
      onClick={onClick}
      disabled={busy || disabled}
      className={`rounded-[5px] border px-4 py-2 text-sm font-medium disabled:cursor-default disabled:opacity-50 ${look}`}
    >
      {busy ? busyLabel : children}
    </button>
  )
}

function Err({ text }: { text: string }) {
  return text ? <p className="mt-3 font-mono text-sm text-dim">{text}</p> : null
}

function Panel({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`min-w-0 rounded-[5px] border border-line bg-panel p-6 ${className}`}>{children}</div>
}

function Gauge({ label, value, red }: { label: string; value: number; red?: boolean }) {
  return (
    <div>
      <Label>{label}</Label>
      <div className={`mt-1 font-mono text-[56px] leading-none font-medium ${red ? 'text-bad' : ''}`}>
        <Count value={value} fmt={pct} />
      </div>
    </div>
  )
}

function Chips({ actions }: { actions: (string | null)[] }) {
  return (
    <div className="flex gap-1.5">
      {actions.map((a, i) => (
        <span key={i} title={a ?? 'request failed'} className="rounded-[4px] border border-line px-1.5 py-0.5 font-mono text-xs">
          {a ? a.split('_')[0] : 'error'}
        </span>
      ))}
    </div>
  )
}

function ReplayTable({ decision, replay }: { decision: Decision; replay: Replay }) {
  // Rows fill in one at a time once the results arrive.
  const total = replay.ablations.length + 1
  const [shown, setShown] = useState(0)
  useEffect(() => {
    const id = setInterval(() => setShown((n) => (n >= total ? n : n + 1)), 120)
    return () => clearInterval(id)
  }, [total])

  const rows = [
    { key: 'baseline', text: 'Nothing removed (baseline)', id: '', actions: replay.baseline.actions, flip: 1 - replay.baseline.stability, culprit: false },
    ...replay.ablations.map((a) => ({
      key: a.removed_memory_id,
      text: decision.retrieved.find((r) => r.memory_id === a.removed_memory_id)?.text ?? '',
      id: a.removed_memory_id,
      actions: a.actions,
      flip: a.flip_rate,
      culprit: a.removed_memory_id === replay.culprit_memory_id,
    })),
  ]
  return (
    <table className="w-full border-collapse">
      <thead>
        <tr className="text-left text-xs uppercase tracking-[0.14em] text-dim">
          <th className="pb-3 pl-4 font-normal">Memory removed</th>
          <th className="pb-3 font-normal">Action, {replay.runs_per_variant} runs</th>
          <th className="pb-3 text-right font-normal">Decision flips</th>
        </tr>
      </thead>
      <tbody>
        {rows.slice(0, shown).map((r) => (
          <tr key={r.key} className={`row-in border-t border-line ${r.culprit ? 'text-culprit' : ''}`}>
            <td className={`border-l-2 py-4 pr-6 pl-4 ${r.culprit ? 'border-l-culprit' : 'border-l-transparent'}`}>
              {r.id && <div className="font-mono text-xs opacity-70">{short(r.id)}</div>}
              <div className={r.id ? '' : 'text-dim'}>{r.text}</div>
            </td>
            <td className="w-px py-4 pr-6 align-middle whitespace-nowrap"><Chips actions={r.actions} /></td>
            <td className="w-40 py-4 align-middle">
              <div className="relative text-right font-mono text-[48px] leading-none font-medium">
                <span className={r.id || r.flip > 0 ? '' : 'text-dim'}><Count value={r.flip} fmt={(n) => pct(n, 0)} fromZero /></span>
                <div className="absolute right-0 -bottom-2 left-0 h-px bg-line">
                  <div className={`h-px ${r.culprit ? 'bg-culprit' : 'bg-dim'}`} style={{ width: pct(r.flip, 0) }} />
                </div>
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function OutcomeCard({ label, d, good }: { label: string; d: Decision; good: boolean }) {
  const bad = isBad(d)
  const tone = bad ? 'text-bad' : good ? 'text-ok' : ''
  return (
    <Panel>
      <Label>{label}</Label>
      <div className={`mt-3 font-mono text-[clamp(16px,3vw,30px)] leading-tight font-medium ${tone}`}>{d.action}</div>
      <div className="mt-6"><Label>Fraud rate</Label></div>
      <div className={`mt-1 font-mono text-[64px] leading-none font-medium ${tone}`}>
        <Count value={d.sim_after.fraud_rate} fmt={pct} fromZero />
      </div>
      <div className="mt-6"><Label>Memories used</Label></div>
      <ul className="mt-2 space-y-1.5 text-sm text-dim">
        {d.retrieved.map((m) => (
          <li key={m.memory_id} className="flex gap-2">
            <span className="shrink-0 font-mono">v{m.version}</span>
            <span className="line-clamp-2">{m.text}</span>
          </li>
        ))}
      </ul>
    </Panel>
  )
}

function Isolation({ user, acmeMemoryId }: { user: User; acmeMemoryId: string }) {
  const [results, setResults] = useState<Memory[] | null>(null)
  const [memId, setMemId] = useState(acmeMemoryId)
  const [refused, setRefused] = useState<{ status: string; entry?: AccessEntry } | null>(null)
  const search = useStep()
  const read = useStep()
  const tenant = TENANT[user]
  const foreign = results?.filter((r) => r.tenant_id !== tenant).length ?? 0

  return (
    <Section n="06" title="Isolation" active>
      <Label>Query, same as the Acme incident</Label>
      <p className="mt-2 mb-5">{TASK}</p>
      <Btn primary busy={search.busy} busyLabel="Searching…"
        onClick={() => search.run(async () => setResults(await api<Memory[]>(user, `/search?q=${encodeURIComponent(TASK)}`)))}>
        Search as {tenant}
      </Btn>
      <Err text={search.err} />
      {results && (
        <div className="mt-8 grid grid-cols-[auto_1fr] items-start gap-10">
          <div>
            <Label>Acme memories returned</Label>
            <div className="mt-1 font-mono text-[64px] leading-none font-medium">{foreign}</div>
          </div>
          <table className="w-full border-collapse">
            <tbody>
              {results.map((r) => (
                <tr key={r._id} className="row-in border-t border-line align-top first:border-t-0">
                  <td className="py-3 pr-4 font-mono text-sm text-dim">{r.tenant_id}</td>
                  <td className="py-3 pr-4">{r.text}</td>
                  <td className="py-3 text-right font-mono text-sm text-dim">{r.score?.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-12"><Label>Direct read of an Acme memory ID</Label></div>
      <div className="mt-3 flex gap-3">
        <input value={memId} onChange={(e) => setMemId(e.target.value.trim())} placeholder="memory id" spellCheck={false}
          className="w-72 rounded-[5px] border border-line bg-transparent px-3 py-2 font-mono text-sm outline-none focus:border-dim" />
        <Btn busy={read.busy} busyLabel="Requesting…" disabled={!memId}
          onClick={() => read.run(async () => {
            setRefused(null)
            let status = '200 returned'
            try {
              await api(user, `/memories/${memId}`)
            } catch (e) {
              if (!(e instanceof ApiError)) throw e
              status = e.message
            }
            const log = await api<AccessEntry[]>(user, '/access-log')
            setRefused({ status, entry: log.find((x) => x.kind === 'get' && x.query === memId) })
          })}>
          Request memory
        </Btn>
      </div>
      <Err text={read.err} />
      {refused && (
        <div className="mt-6">
          <div className="font-mono text-[48px] leading-none font-medium">{refused.status}</div>
          {refused.entry && (
            <p className="mt-4 font-mono text-sm text-dim">
              access_log · {hhmm(refused.entry.at)} · {refused.entry.user_id} · {refused.entry.kind} {short(refused.entry.query)} · allowed: {String(refused.entry.allowed)}
            </p>
          )}
        </div>
      )}
    </Section>
  )
}

export default function App() {
  const [user, setUser] = useState<User>('sre-oncall')
  const [sim, setSim] = useState<Sim | null>(null)
  const [decision, setDecision] = useState<Decision | null>(null)
  const [rerun, setRerun] = useState<Decision | null>(null)
  const [loadErr, setLoadErr] = useState('')
  const reset = useStep()
  const runStep = useStep()
  const replayStep = useStep()
  const verdictStep = useStep()
  const approveStep = useStep()
  const rerunStep = useStep()

  const replay = decision?.replay ?? null
  const verdict = decision?.verdict ?? null
  const globex = TENANT[user] === 'globex'

  // Restore the open case after a page reload; a 404 means the demo was reset since.
  useEffect(() => {
    api<Sim>('sre-oncall', '/sim').then(setSim).catch((e) => setLoadErr(e.message))
    let saved: { decision?: string; rerun?: string } = {}
    try {
      saved = JSON.parse(localStorage.getItem(STORE) ?? '{}')
    } catch { /* storage unavailable */ }
    if (saved.decision) api<Decision>('sre-oncall', `/decisions/${saved.decision}`).then(setDecision).catch(() => {})
    if (saved.rerun) api<Decision>('sre-oncall', `/decisions/${saved.rerun}`).then(setRerun).catch(() => {})
  }, [])
  const remember = (d: string | undefined, r: string | undefined) => {
    try {
      localStorage.setItem(STORE, JSON.stringify({ decision: d, rerun: r }))
    } catch { /* storage unavailable */ }
  }

  const resetDemo = () => reset.run(async () => {
    await api(user, '/demo/reset', {})
    setDecision(null)
    setRerun(null)
    remember(undefined, undefined)
    setSim(await api<Sim>(user, '/sim'))
  })
  const runAgent = () => runStep.run(async () => {
    const d = await api<Decision>(user, '/run', { task: TASK })
    setDecision(d)
    setRerun(null)
    setSim(d.sim_after)
    remember(d._id, undefined)
  })
  const contest = () => replayStep.run(async () => {
    const id = decision!._id
    const contested = await api<Decision['contested']>(user, `/decisions/${id}/contest`, { reason: 'Fraud rate went red after this action' })
    setDecision((d) => d && { ...d, contested })
    const r = await api<Replay>(user, `/decisions/${id}/replay`, {})
    setDecision((d) => d && { ...d, replay: r, verdict: null })
  })
  const propose = () => verdictStep.run(async () => {
    const v = await api<Verdict>(user, `/decisions/${decision!._id}/verdict`, {})
    setDecision((d) => d && { ...d, verdict: v })
  })
  const approve = () => approveStep.run(async () => {
    const v = await api<Verdict>(user, `/verdicts/${verdict!._id}/approve`, {})
    setDecision((d) => d && { ...d, verdict: v })
  })
  const runAgain = () => rerunStep.run(async () => {
    setSim(await api<Sim>(user, '/sim/reset', {}))
    const d = await api<Decision>(user, '/run', { task: TASK, rerun_of: decision!._id })
    setRerun(d)
    setSim(d.sim_after)
    remember(decision!._id, d._id)
  })

  const culprit = replay?.ablations.find((a) => a.removed_memory_id === replay.culprit_memory_id)
  const runs = decision ? (decision.retrieved.length + 1) * 3 : 0
  const approved = verdict?.status === 'approved'

  return (
    <div className="mx-auto max-w-[960px] px-6 pt-8 pb-32">
      <header className="flex items-center justify-between border-b border-line pb-5">
        <div className="flex items-baseline gap-4">
          <h1 className="text-base font-semibold">RecallTrace</h1>
          <span className="font-mono text-sm text-dim">{TENANT[user]}</span>
        </div>
        <div className="flex items-center gap-3">
          <select value={user} onChange={(e) => setUser(e.target.value as User)} aria-label="Session user"
            className="rounded-[5px] border border-line bg-bg px-3 py-2 font-mono text-sm outline-none">
            {USERS.map((u) => <option key={u}>{u}</option>)}
          </select>
          <Btn busy={reset.busy} busyLabel="Resetting…" onClick={resetDemo}>Reset demo</Btn>
        </div>
      </header>
      <Err text={reset.err || loadErr} />

      {globex ? (
        <Isolation user={user} acmeMemoryId={replay?.culprit_memory_id ?? decision?.retrieved[0]?.memory_id ?? ''} />
      ) : (
        <>
          <Section n="01" title="Incident" active>
            <p className="max-w-[720px]">{TASK}</p>
            <div className="mt-8 mb-8 flex gap-16">
              <Gauge label="Checkout error rate" value={sim?.checkout_error_rate ?? 0} />
              <Gauge label="Fraud rate" value={sim?.fraud_rate ?? 0} red={(sim?.fraud_rate ?? 0) > FRAUD_RED} />
            </div>
            {!decision && <Btn primary busy={runStep.busy} onClick={runAgent}>Run agent</Btn>}
            {runStep.busy && <div className="mt-3"><Wait text="Retrieving memories, choosing an action…" /></div>}
            <Err text={runStep.err} />
          </Section>

          <Section n="02" title="Decision" active={!!decision}>
            {decision && (
              <>
                <Label>Agent called</Label>
                <div className={`mt-1 font-mono text-[clamp(28px,7vw,56px)] leading-tight font-medium ${isBad(decision) ? 'text-bad' : ''}`}>{decision.action}</div>
                <p className="mt-3 max-w-[720px] text-dim">{decision.rationale}</p>
                <div className="mt-8"><Label>Memories retrieved</Label></div>
                <table className="mt-2 mb-8 w-full border-collapse">
                  <tbody>
                    {decision.retrieved.map((m) => (
                      <tr key={m.memory_id} className="border-t border-line align-top first:border-t-0">
                        <td className="py-3 pr-4 font-mono text-sm text-dim">{short(m.memory_id)}</td>
                        <td className="py-3 pr-4">{m.text}</td>
                        <td className="py-3 text-right font-mono text-sm text-dim">{m.score.toFixed(3)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!replay && <Btn primary busy={replayStep.busy} busyLabel="Replaying…" onClick={contest}>Contest decision</Btn>}
                {decision.contested && (
                  <p className="mt-3 font-mono text-sm text-dim">Contested by {decision.contested.by} · {hhmm(decision.contested.at)}</p>
                )}
                {replayStep.busy && <Wait text={`Replaying ${runs} runs…`} />}
                <Err text={replayStep.err} />
              </>
            )}
          </Section>

          <Section n="03" title="Investigation" active={!!replay}>
            {decision && replay && (
              <>
                <ReplayTable key={replay._id} decision={decision} replay={replay} />
                <p className="mt-8 mb-6 text-xl">
                  {culprit ? (
                    <>Remove memory <span className="font-mono text-culprit">{short(culprit.removed_memory_id)}</span> → decision flips <span className="font-mono">{pct(culprit.flip_rate, 0)}</span></>
                  ) : (
                    <span className="font-mono text-base text-dim">{replay.status ?? 'no_clear_influence'} · no single memory flips the decision</span>
                  )}
                </p>
                {culprit && !verdict && <Btn primary busy={verdictStep.busy} busyLabel="Checking…" onClick={propose}>Check against evidence</Btn>}
                {verdictStep.busy && <div className="mt-3"><Wait text="Looking up newer verified evidence, drafting a correction…" /></div>}
                <Err text={verdictStep.err} />
              </>
            )}
          </Section>

          <Section n="04" title="Verdict" active={!!verdict}>
            {verdict && (
              <>
                {verdict.memory_text && (
                  <div className="grid grid-cols-2 gap-4">
                    <Panel>
                      <Label>{approved ? 'Quarantined' : 'Current memory'}</Label>
                      <p className="mt-3 text-dim line-through">{verdict.memory_text}</p>
                    </Panel>
                    <Panel>
                      <Label>{verdict.outcome === 'correct' ? (approved ? 'Active, supersedes it' : 'Proposed replacement') : 'No replacement'}</Label>
                      <p className="mt-3">{verdict.proposed_text ?? <span className="font-mono text-dim">{verdict.outcome}</span>}</p>
                    </Panel>
                  </div>
                )}
                {verdict.evidence_title && (
                  <p className="mt-5">Evidence: {verdict.evidence_title} · verified by <span className="font-mono">{verdict.evidence_verified_by}</span></p>
                )}
                <p className="mt-2 mb-6 max-w-[720px] text-dim">{verdict.reason}</p>
                {approved ? (
                  <p>Approved by <span className="font-mono">{verdict.approved_by}</span> · <span className="font-mono">{hhmm(verdict.approved_at!)}</span></p>
                ) : verdict.outcome !== 'no_action' && (
                  <Btn primary busy={approveStep.busy} busyLabel="Approving…" onClick={approve}>Approve as {user}</Btn>
                )}
                <Err text={approveStep.err} />
              </>
            )}
          </Section>

          <Section n="05" title="Rerun" active={approved}>
            {decision && approved && (
              <>
                {!rerun && <Btn primary busy={rerunStep.busy} onClick={runAgain}>Reset simulation and rerun</Btn>}
                {rerunStep.busy && <div className="mt-3"><Wait text="Same task, fresh retrieval…" /></div>}
                <Err text={rerunStep.err} />
                {rerun && (
                  <div className="grid grid-cols-2 gap-4">
                    <OutcomeCard label="Before" d={decision} good={false} />
                    <OutcomeCard label="After" d={rerun} good />
                  </div>
                )}
              </>
            )}
          </Section>
        </>
      )}
    </div>
  )
}
