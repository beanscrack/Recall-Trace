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
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const start = last.current
    const t0 = performance.now()
    let raf = 0
    const tick = (t: number) => {
      const p = reducedMotion ? 1 : Math.min(1, (t - t0) / 180)
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
  return <p role="status" className="font-mono text-sm text-dim">{text} {s}s</p>
}

function Label({ children }: { children: ReactNode }) {
  return <div className="text-xs uppercase tracking-[0.14em] text-dim">{children}</div>
}

const STEP_GUIDE: Record<string, { description: string; waiting: string }> = {
  '01': { description: 'A checkout incident arrives. The agent will search stored incident memories and choose a response.', waiting: '' },
  '02': { description: 'See the action the agent chose, its simulated impact, and the memories it retrieved from Atlas.', waiting: 'Run the agent to see its decision and retrieved memories.' },
  '03': { description: 'Black Box Replay removes one memory at a time and repeats the same decision. A flip means the agent chose a different action. Replay never executes tools.', waiting: 'Contest the decision to investigate which memory influenced it.' },
  '04': { description: 'Compare the candidate memory against newer verified evidence. A person must approve any change to stored memory.', waiting: 'Check an influential memory against evidence to review a proposed correction.' },
  '05': { description: 'Run the same incident with fresh Atlas retrieval and compare the measured outcomes.', waiting: 'Approve a memory change to unlock the comparison.' },
  '06': { description: 'Switch to a different company. Search results must stay within its tenant, and direct access to another tenant’s memory must be refused.', waiting: '' },
}

function Section({ n, title, active, visible = true, children }: { n: string; title: string; active: boolean; visible?: boolean; children?: ReactNode }) {
  return (
    <section id={`step-${n}`} role="tabpanel" aria-labelledby={`tab-${Number(n) - 1}`} hidden={!visible} tabIndex={0} className={`demo-panel mt-6 rounded-xl border p-5 sm:p-7 ${active ? 'border-line bg-panel' : 'border-line/60'}`}>
      <h2 className="mb-5 flex items-baseline gap-3 border-b border-line pb-3 text-xs uppercase tracking-[0.14em] text-dim">
        <span className="font-mono">{n}</span>
        <span className="text-base font-semibold tracking-normal normal-case text-fg">{title}</span>
        {!active && <span className="ml-auto tracking-normal normal-case">Upcoming</span>}
      </h2>
      <p className="mb-6 max-w-[760px] text-sm leading-relaxed text-dim">{active ? STEP_GUIDE[n].description : STEP_GUIDE[n].waiting}</p>
      {active && children}
    </section>
  )
}

function Btn({ primary, busy, busyLabel = 'Running…', disabled, onClick, children }: {
  primary?: boolean; busy?: boolean; busyLabel?: string; disabled?: boolean; onClick: () => void; children: ReactNode
}) {
  const look = primary ? 'bg-white text-black border-white shadow-sm hover:bg-white/90' : 'bg-panel text-fg border-line hover:border-dim hover:bg-white/5'
  return (
    <button
      onClick={onClick}
      disabled={busy || disabled}
      aria-busy={busy || undefined}
      className={`ui-button rounded-lg border px-4 py-2 text-sm font-medium disabled:cursor-default disabled:opacity-50 ${look}`}
    >
      {busy ? busyLabel : children}
    </button>
  )
}

function Err({ text }: { text: string }) {
  return text ? <p role="alert" className="mt-3 rounded border border-bad/40 bg-bad/5 p-3 font-mono text-sm break-words text-fg">{text}</p> : null
}

function Panel({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`surface min-w-0 rounded-xl border border-line bg-panel p-6 ${className}`}>{children}</div>
}

function Gauge({ label, value, red }: { label: string; value: number; red?: boolean }) {
  return (
    <div className="rounded-lg border border-line bg-bg/60 p-5">
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
    { key: 'baseline', text: 'Nothing removed (baseline)', id: '', actions: replay.baseline.actions,
      flip: replay.baseline.actions.filter((a) => a !== null && a !== decision.action).length / replay.runs_per_variant, culprit: false },
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
    <div className="overflow-x-auto rounded-[5px] border border-line p-3" role="region" aria-label="Replay comparisons" tabIndex={0}>
    <table className="w-full min-w-[600px] border-collapse">
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
    </div>
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
        <div className="mt-8 grid grid-cols-1 items-start gap-6 sm:grid-cols-[auto_1fr] sm:gap-10">
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
      <div className="mt-3 flex flex-wrap gap-3">
        <input value={memId} onChange={(e) => setMemId(e.target.value.trim())} placeholder="memory id" spellCheck={false}
          aria-label="Acme memory ID" className="w-72 max-w-full rounded-[5px] border border-line bg-transparent px-3 py-2 font-mono text-sm outline-none focus:border-dim" />
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
  const [page, setPage] = useState(0)
  const goTo = (step: number) => {
    setPage(step)
    if (step === 5) setUser('platform-lee')
    else setUser((current) => TENANT[current] === 'globex' ? 'sre-oncall' : current)
    window.scrollTo({ top: 0, behavior: 'instant' })
  }
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
    goTo(0)
    remember(undefined, undefined)
    setSim(await api<Sim>(user, '/sim'))
  })
  const runAgent = () => runStep.run(async () => {
    const d = await api<Decision>(user, '/run', { task: TASK })
    setDecision(d)
    setRerun(null)
    setSim(d.sim_after)
    remember(d._id, undefined)
    goTo(1)
  })
  const contest = () => replayStep.run(async () => {
    const id = decision!._id
    const contested = await api<Decision['contested']>(user, `/decisions/${id}/contest`, { reason: 'Fraud rate went red after this action' })
    setDecision((d) => d && { ...d, contested })
    const r = await api<Replay>(user, `/decisions/${id}/replay`, {})
    setDecision((d) => d && { ...d, replay: r, verdict: null })
    goTo(2)
  })
  const propose = () => verdictStep.run(async () => {
    const v = await api<Verdict>(user, `/decisions/${decision!._id}/verdict`, {})
    setDecision((d) => d && { ...d, verdict: v })
    goTo(3)
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
  const stage = globex ? 5 : !decision ? 0 : !replay ? 1 : !verdict ? 2 : !approved ? 3 : 4
  const steps = ['Run incident', 'Inspect decision', 'Replay memories', 'Review correction', 'Compare outcomes', 'Check isolation']
  const nextMessage = globex ? 'Search as Globex, then try reading an Acme memory to verify the boundary.'
    : !decision ? 'Start by running the agent on the checkout incident below.'
    : !replay ? 'Inspect the decision, then contest it to investigate memory influence.'
    : !verdict ? culprit ? 'A candidate memory was found. Check it against newer verified evidence.' : 'The replay is inconclusive. Review the results and retry if needed.'
    : !approved ? verdict.outcome === 'no_action' ? 'The evidence did not support a change. The memory remains unchanged.' : 'Review the evidence and proposed change, then approve it when satisfied.'
    : !rerun ? 'The change is approved. Rerun the same incident with fresh retrieval.'
    : 'Compare the actual outcomes below, then check isolation with the second tenant.'

  return (
    <div className="app-shell mx-auto max-w-[1120px] px-4 pt-5 pb-12 sm:px-6">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-line pb-5">
        <div className="flex items-center gap-3">
          <span className="brand-mark" aria-hidden="true"><svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M5 6h9a5 5 0 0 1 0 10H9m0-4-4 4 4 4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"/><circle cx="5" cy="6" r="2" fill="currentColor"/></svg></span>
          <h1 className="text-base font-semibold tracking-tight">RecallTrace</h1>
          <span className="tenant-badge">{TENANT[user]}</span>
        </div>
        <div className="flex items-center gap-3">
          <select title="Demo identity: determines the tenant used for requests" value={user} onChange={(e) => { const next = e.target.value as User; setUser(next); if (TENANT[next] === 'globex') setPage(5); else if (page === 5) setPage(0) }} aria-label="Session user"
            className="rounded-lg border border-line bg-panel px-3 py-2 text-sm outline-none">
            {USERS.map((u) => <option key={u} value={u}>{u === 'sre-oncall' ? 'Acme · On-call' : u === 'reviewer-dana' ? 'Acme · Reviewer' : 'Globex · Platform'}</option>)}
          </select>
          <Btn busy={reset.busy} busyLabel="Resetting…" onClick={resetDemo}>Reset demo</Btn>
        </div>
      </header>
      {page === 0 ? <div className="hero my-7 rounded-xl border border-line p-6 sm:p-8">
        <div className="flex flex-wrap items-center gap-3"><span className="eyebrow">AI memory governance</span><span className="text-xs text-dim">Interactive product demo</span></div>
        <p className="mt-5 max-w-[760px] text-3xl font-semibold tracking-[-0.04em] sm:text-[42px] sm:leading-[1.12]">Better decisions start<br className="hidden sm:block" /> with better memory.</p>
        <p className="mt-4 max-w-[660px] text-sm leading-relaxed text-dim sm:text-base">Trace a bad agent decision to the memories that influenced it. Review the evidence, approve a correction, and see what changes.</p>
        <div className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-dim"><span>01 &nbsp; Investigate</span><span aria-hidden="true">→</span><span>02 &nbsp; Approve</span><span aria-hidden="true">→</span><span>03 &nbsp; Verify</span></div>
        <details className="mt-5 border-t border-line pt-4 text-xs text-dim"><summary className="cursor-pointer">How this demo uses MongoDB Atlas</summary><p className="mt-3 max-w-[680px] leading-relaxed">Atlas stores memories, exact decision snapshots, corrections, and audit history. Vector Search retrieves relevant memories. Replay uses the recorded snapshot. Checkout actions and fraud metrics are simulated.</p></details>
      </div> : <div className="my-7 flex items-center justify-between gap-4"><div><p className="text-xs text-dim">Memory governance / Checkout incident</p><p className="mt-2 text-2xl font-semibold tracking-tight">{steps[page]}</p></div><span className="eyebrow shrink-0">Demo workspace</span></div>}
      <nav aria-label="Demo steps" className="step-nav sticky top-0 z-10 overflow-x-auto border-b border-line bg-bg/95 backdrop-blur">
        <ol role="tablist" aria-label="Demo steps" className="flex min-w-max gap-1 sm:min-w-0">
          {steps.map((label, i) => <li role="presentation" key={label} className="flex-1">
            <button role="tab" id={`tab-${i}`} aria-controls={`step-0${i + 1}`} aria-selected={page === i} tabIndex={page === i ? 0 : -1} aria-label={`${i + 1} ${label}`} onClick={() => goTo(i)} onKeyDown={(e) => {
              const target = e.key === 'ArrowRight' ? (i + 1) % steps.length : e.key === 'ArrowLeft' ? (i + steps.length - 1) % steps.length : e.key === 'Home' ? 0 : e.key === 'End' ? steps.length - 1 : null
              if (target !== null) { e.preventDefault(); goTo(target); document.getElementById(`tab-${target}`)?.focus() }
            }} className={`step-tab w-full px-3 py-4 text-left text-xs ${page === i ? 'selected text-fg' : 'text-dim hover:text-fg'}`} >
              <span className="step-number mr-2">{i + 1}</span>{label}
            </button>
          </li>)}
        </ol>
      </nav>
      <aside className="guidance mt-5 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line px-4 py-3" aria-label="Current demo step">
        <div><p className="text-xs font-semibold uppercase tracking-wider text-dim">{`Viewing ${page + 1} of 6 · ${steps[page]}`}</p><p className="mt-1 text-sm">{nextMessage}</p></div>
        {page !== stage && <Btn onClick={() => goTo(stage)}>Resume current task →</Btn>}
      </aside>
      <Err text={reset.err || loadErr} />

      <div hidden={page !== 5}>
        <Isolation key={replay?.culprit_memory_id ?? decision?.retrieved[0]?.memory_id ?? 'empty'} user={user} acmeMemoryId={replay?.culprit_memory_id ?? decision?.retrieved[0]?.memory_id ?? ''} />
      </div>
        <>
          <Section visible={page === 0} n="01" title="Incident" active>
            <p className="max-w-[720px]">{TASK}</p>
            <div className="metrics mt-6 mb-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Gauge label="Checkout error rate" value={sim?.checkout_error_rate ?? 0} />
              <Gauge label="Fraud rate" value={sim?.fraud_rate ?? 0} red={(sim?.fraud_rate ?? 0) > FRAUD_RED} />
            </div>
            <p className="mb-8 text-xs text-dim">Current simulator metrics · The incident above is the fixed task used for both decisions.</p>
            {!decision && <Btn primary busy={runStep.busy} onClick={runAgent}>Run agent</Btn>}
            {runStep.busy && <div className="mt-3"><Wait text="Retrieving memories, choosing an action…" /></div>}
            <Err text={runStep.err} />
          </Section>

          <Section visible={page === 1} n="02" title="Decision" active={!!decision}>
            {decision && (
              <>
                <Label>Selected tool action</Label>
                <div className={`mt-1 font-mono text-[clamp(28px,7vw,56px)] leading-tight break-words font-medium ${isBad(decision) ? 'text-bad' : ''}`}>{decision.action}</div>
                <p className="mt-3 max-w-[720px] text-dim">{decision.rationale}</p>
                <div className={`mt-5 rounded-lg border p-4 ${isBad(decision) ? 'border-bad/40 bg-bad/5' : 'border-line'}`}>
                  <p className="font-medium">{isBad(decision) ? 'Unsafe simulated outcome' : 'Recorded simulated outcome'}</p>
                  <p className="mt-1 text-sm">Fraud rate: {pct(decision.sim_before.fraud_rate)} → <strong>{pct(decision.sim_after.fraud_rate)}</strong> · Checkout errors: {pct(decision.sim_before.checkout_error_rate)} → {pct(decision.sim_after.checkout_error_rate)}</p>
                </div>
                <div className="mt-8"><Label>Memories retrieved</Label></div>
                <table className="mt-2 mb-8 w-full border-collapse">
                  <thead><tr className="text-left text-xs text-dim"><th className="py-3 pr-3 font-normal">ID</th><th className="py-3 font-normal">Memory used in this decision</th><th className="py-3 text-right font-normal">Similarity</th></tr></thead>
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
                {!replay && <p className="mb-3 text-sm text-dim">Next: contest this decision to compare repeated replays with each memory removed.</p>}
                {!replay && <Btn primary busy={replayStep.busy} busyLabel="Replaying…" onClick={contest}>Contest decision</Btn>}
                {decision.contested && (
                  <p className="mt-3 font-mono text-sm text-dim">Contested by {decision.contested.by} · {hhmm(decision.contested.at)}</p>
                )}
                {replayStep.busy && <Wait text={`Replaying ${runs} runs…`} />}
                <Err text={replayStep.err} />
              </>
            )}
          </Section>

          <Section visible={page === 2} n="03" title="Investigation" active={!!replay}>
            {decision && replay && (
              <>
                <p className="mb-5 text-sm text-dim">Read the table: each row removes one memory. A higher flip rate means that removal changed the selected action more often.</p>
                <ReplayTable key={replay._id} decision={decision} replay={replay} />
                <p className="mt-4 text-sm text-dim">
                  Baseline matches original action: {pct(replay.baseline.stability, 0)} ·{' '}
                  {replay.baseline.actions.filter((a) => a !== null).length}/{replay.runs_per_variant} successful calls.
                  Failed calls are not counted as action flips.
                </p>
                <p className="mt-8 mb-6 text-xl">
                  {culprit ? (
                    <>Remove memory <span className="font-mono text-culprit">{short(culprit.removed_memory_id)}</span> → decision flips <span className="font-mono">{pct(culprit.flip_rate, 0)}</span></>
                  ) : (
                    <span className="text-base text-dim">
                      {replay.status === 'incomplete' ? 'Some model requests failed. No memory can be attributed from this incomplete comparison.'
                        : replay.status === 'unstable_baseline' ? 'The baseline did not reproduce the original action reliably enough to compare memory removals.'
                        : 'No unique memory met the influence threshold. Rates below 2/3 and tied leaders remain inconclusive.'}
                    </span>
                  )}
                </p>
                {!culprit && !approved && (
                  <Btn busy={replayStep.busy} busyLabel="Replaying…" onClick={contest}>Retry replay</Btn>
                )}
                {culprit && !verdict && <Btn primary busy={verdictStep.busy} busyLabel="Checking…" onClick={propose}>Check against evidence</Btn>}
                <p className="mt-4 text-xs text-dim">Repeated comparisons provide evidence of influence, not proof of causation.</p>
                {verdictStep.busy && <div className="mt-3"><Wait text="Looking up newer verified evidence, drafting a correction…" /></div>}
                <Err text={verdictStep.err} />
              </>
            )}
          </Section>

          <Section visible={page === 3} n="04" title="Verdict" active={!!verdict}>
            {verdict && (
              <>
                {verdict.memory_text && (
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <Panel>
                      <Label>{approved ? 'Quarantined' : 'Current memory'}</Label>
                      <p className={`mt-3 text-dim ${approved ? 'line-through' : ''}`}>{verdict.memory_text}</p>
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

          <Section visible={page === 4} n="05" title="Rerun" active={approved}>
            {decision && approved && (
              <>
                {!rerun && <Btn primary busy={rerunStep.busy} onClick={runAgain}>Reset simulation and rerun</Btn>}
                {rerunStep.busy && <div className="mt-3"><Wait text="Same task, fresh retrieval…" /></div>}
                <Err text={rerunStep.err} />
                {rerun && <p className="mb-5 rounded-lg border border-line p-4 text-sm">{decision.action !== rerun.action ? 'The selected action changed after the approved memory update.' : 'The selected action stayed the same after the approved memory update.'} Simulated fraud rate: <strong>{pct(decision.sim_after.fraud_rate)} → {pct(rerun.sim_after.fraud_rate)}</strong>. Compare the retrieved memories below.</p>}
                {rerun && (
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <OutcomeCard label="Before" d={decision} good={false} />
                    <OutcomeCard label="After" d={rerun} good />
                  </div>
                )}
              </>
            )}
            {rerun && <div className="mt-6"><Btn onClick={() => goTo(5)}>Next: verify tenant isolation</Btn></div>}
          </Section>
        </>
      <footer className="mt-6 flex items-center justify-between gap-3 border-t border-line pt-5">
        <Btn disabled={page === 0} onClick={() => goTo(page - 1)}>← Previous</Btn>
        <span className="text-xs text-dim">{page + 1} / {steps.length}</span>
        <Btn disabled={page === steps.length - 1} onClick={() => goTo(page + 1)}>Next →</Btn>
      </footer>
    </div>
  )
}
