import { useState } from 'react'
import { USERS, type User } from './api'
import mock from './mock/decision.json'

// One page, top to bottom in demo order (brief section 12). Panels render mock data until routes exist.
function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-700 bg-slate-900 p-6">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">{title}</h2>
      {children}
    </section>
  )
}

export default function App() {
  const [user, setUser] = useState<User>('sre-oncall')
  const d = mock

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="flex items-center justify-between border-b border-slate-800 px-8 py-4">
        <div>
          <h1 className="text-2xl font-bold">RecallTrace</h1>
          <p className="text-xs text-slate-400">Agent memory governance · sample data preview</p>
        </div>
        <div className="flex gap-3">
          <select className="rounded bg-slate-800 px-3 py-2" value={user} onChange={(e) => setUser(e.target.value as User)}>
            {USERS.map((u) => <option key={u}>{u}</option>)}
          </select>
          <button className="rounded bg-slate-700 px-4 py-2">Reset demo</button>
        </div>
      </header>
      <main className="mx-auto grid max-w-6xl gap-6 p-8">
        <Panel title="Incident">
          <p className="text-lg">{d.task}</p>
          <div className="mt-4 flex gap-8 text-3xl font-bold">
            <span>Errors {(d.sim_after.checkout_error_rate * 100).toFixed(1)}%</span>
            <span className={d.sim_after.fraud_rate > 0.02 ? 'text-red-500' : 'text-emerald-400'}>
              Fraud {(d.sim_after.fraud_rate * 100).toFixed(1)}%
            </span>
          </div>
        </Panel>
        <Panel title="Decision">
          <p className="font-mono text-4xl font-bold text-red-400">{d.action}</p>
          <p className="mt-2 text-slate-300">{d.rationale}</p>
        </Panel>
        <Panel title="Investigation (Black Box)">
          {d.replay.ablations.map((a) => (
            <div key={a.removed_memory_id}
              className={`flex justify-between py-2 text-xl ${a.removed_memory_id === d.replay.culprit_memory_id ? 'text-amber-400' : ''}`}>
              <span className="truncate pr-4">− {d.retrieved.find((r) => r.memory_id === a.removed_memory_id)?.text}</span>
              <span className="font-bold">{Math.round(a.flip_rate * 100)}%</span>
            </div>
          ))}
        </Panel>
        <Panel title="Verdict · evidence review"><p>{d.verdict.reason}</p></Panel>
        <Panel title="Rerun">TODO: before / after</Panel>
        {user === 'platform-lee' && <Panel title="Isolation">TODO: search results + refused read</Panel>}
      </main>
    </div>
  )
}
