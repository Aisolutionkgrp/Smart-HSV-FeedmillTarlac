import { fetchEvents } from '../lib/api'
import Sidebar from '../components/Sidebar'
import RiskBadge from '../components/RiskBadge'
import Link from 'next/link'

export default async function EventsPage({
  searchParams,
}: {
  searchParams: Promise<{ risk?: string }>
}) {
  const params = await searchParams
  let events: any[] = []
  try {
    events = await fetchEvents({ risk_level: params.risk, limit: 50 })
  } catch {}

  return (
    <div style={{ display: 'flex' }}>
      <Sidebar />
      <main style={{ marginLeft: 220, flex: 1, padding: '32px 40px', minHeight: '100vh' }}>

        <div style={{ marginBottom: 28 }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.12em', marginBottom: 4 }}>EVENTS</div>
          <h1 style={{ fontSize: 24, fontWeight: 600 }}>Alert History</h1>
        </div>

        {/* Filter */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
          {['', 'RED', 'ORANGE', 'YELLOW'].map(r => (
            <Link key={r} href={r ? `/events?risk=${r}` : '/events'} style={{ textDecoration: 'none' }}>
              <button style={{
                padding: '6px 14px', borderRadius: 6, fontSize: 12, cursor: 'pointer',
                fontFamily: 'JetBrains Mono', fontWeight: 500, letterSpacing: '0.05em',
                background: params.risk === r || (!r && !params.risk) ? 'var(--accent)' : 'var(--bg-card)',
                color: params.risk === r || (!r && !params.risk) ? '#0f1117' : 'var(--text-secondary)',
                border: '1px solid var(--border)',
              }}>
                {r || 'ALL'}
              </button>
            </Link>
          ))}
          <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-muted)', alignSelf: 'center' }}>
            {events.length} events
          </span>
        </div>

        {/* Table */}
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {['ID', 'Risk', 'Zone', 'Situation', 'Hazards', 'Person', 'Time'].map(h => (
                  <th key={h} style={{
                    padding: '12px 16px', textAlign: 'left',
                    fontSize: 10, color: 'var(--text-muted)', fontWeight: 500,
                    letterSpacing: '0.1em', fontFamily: 'JetBrains Mono',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {events.length === 0 && (
                <tr><td colSpan={7} style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>No events found</td></tr>
              )}
              {events.map((ev: any) => (
                <tr key={ev.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '12px 16px' }}>
                    <Link href={`/events/${ev.id}`} style={{ color: 'var(--accent)', textDecoration: 'none', fontFamily: 'JetBrains Mono', fontSize: 12 }}>
                      #{ev.id}
                    </Link>
                  </td>
                  <td style={{ padding: '12px 16px' }}><RiskBadge risk={ev.risk_level} /></td>
                  <td style={{ padding: '12px 16px', fontSize: 12, color: 'var(--text-secondary)', fontFamily: 'JetBrains Mono' }}>
                    {ev.zone_id.replace(/_/g, ' ')}
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: 12, color: 'var(--text-muted)', maxWidth: 300 }}>
                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {ev.situation_summary_en || '—'}
                    </div>
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: 12, color: 'var(--text-primary)', fontFamily: 'JetBrains Mono', textAlign: 'center' }}>
                    {ev.hazard_count}
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: 12, color: 'var(--text-muted)', fontFamily: 'JetBrains Mono' }}>
                    {ev.person_track_id ? `P${ev.person_track_id}` : '—'}
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: 11, color: 'var(--text-muted)', fontFamily: 'JetBrains Mono', whiteSpace: 'nowrap' }}>
                    {new Date(ev.triggered_at).toLocaleString('th-TH', { dateStyle: 'short', timeStyle: 'short' })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  )
}
