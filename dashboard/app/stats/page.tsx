import { fetchEvents, fetchStats } from '../lib/api'
import Sidebar from '../components/Sidebar'
import RiskBadge from '../components/RiskBadge'
import Link from 'next/link'

function formatHour(iso: string) {
  return new Date(iso).getHours() + ':00'
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
}

export default async function StatsPage() {
  let stats = { total_events: 0, today_events: 0, by_risk: {} as Record<string, number> }
  let events: any[] = []

  try {
    stats = await fetchStats('robot_zone')
    events = await fetchEvents({ limit: 100 })
  } catch {}

  const red = stats.by_risk?.RED || 0
  const orange = stats.by_risk?.ORANGE || 0
  const yellow = stats.by_risk?.YELLOW || 0
  const total = red + orange + yellow || 1

  // Group by date
  const byDate: Record<string, number> = {}
  const byZone: Record<string, number> = {}
  const byHour: Record<number, number> = {}
  const hazardLabels: Record<string, number> = {}

  events.forEach((ev: any) => {
    const date = formatDate(ev.triggered_at)
    byDate[date] = (byDate[date] || 0) + 1

    const zone = ev.zone_id.replace(/_/g, ' ')
    byZone[zone] = (byZone[zone] || 0) + 1

    const hour = new Date(ev.triggered_at).getHours()
    byHour[hour] = (byHour[hour] || 0) + 1
  })

  const maxByDate = Math.max(...Object.values(byDate), 1)
  const maxByHour = Math.max(...Object.values(byHour), 1)

  const riskItems = [
    { label: 'CRITICAL', risk: 'RED', val: red, color: 'var(--red)' },
    { label: 'SERIOUS', risk: 'ORANGE', val: orange, color: 'var(--orange)' },
    { label: 'MINOR', risk: 'YELLOW', val: yellow, color: 'var(--yellow)' },
  ]

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar />
      <main style={{ marginLeft: 240, flex: 1, padding: '40px 48px' }}>

        {/* Header */}
        <div style={{ marginBottom: 36 }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.12em', fontWeight: 600, marginBottom: 8 }}>ANALYTICS</div>
          <h1 style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.02em' }}>Safety Analytics</h1>
          <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 6 }}>
            {events.length} total events analyzed · Robot Zone
          </p>
        </div>

        {/* Top stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 28 }}>
          {riskItems.map(({ label, risk, val, color }) => (
            <div key={risk} style={{
              background: 'var(--bg-card)', border: '1px solid var(--border)',
              borderRadius: 14, padding: '24px', position: 'relative', overflow: 'hidden',
            }}>
              <div style={{
                position: 'absolute', top: 0, left: 0, right: 0, height: 2,
                background: `linear-gradient(90deg, ${color}, transparent)`,
              }} />
              <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.1em', fontWeight: 600, marginBottom: 10 }}>{label}</div>
              <div style={{ fontSize: 48, fontWeight: 800, color, letterSpacing: '-0.03em', lineHeight: 1 }}>{val}</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
                {Math.round((val / total) * 100)}% of total alerts
              </div>
            </div>
          ))}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>

          {/* Events by date */}
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 14, padding: '24px' }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.1em', fontWeight: 600, marginBottom: 24 }}>ALERTS BY DATE</div>
            {Object.keys(byDate).length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: 13, textAlign: 'center', padding: '20px 0' }}>No data yet</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {Object.entries(byDate).sort().map(([date, count]) => (
                  <div key={date}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                      <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{date}</span>
                      <span style={{ fontSize: 12, color: 'var(--text-primary)', fontWeight: 600 }}>{count}</span>
                    </div>
                    <div style={{ height: 6, background: 'rgba(255,255,255,0.04)', borderRadius: 3 }}>
                      <div style={{
                        height: '100%', width: `${(count / maxByDate) * 100}%`,
                        background: 'var(--accent)', borderRadius: 3, opacity: 0.8,
                      }} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Events by hour */}
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 14, padding: '24px' }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.1em', fontWeight: 600, marginBottom: 24 }}>ALERTS BY HOUR</div>
            {Object.keys(byHour).length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: 13, textAlign: 'center', padding: '20px 0' }}>No data yet</div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 120, padding: '0 4px' }}>
                {Array.from({ length: 24 }, (_, h) => {
                  const count = byHour[h] || 0
                  const pct = (count / maxByHour) * 100
                  return (
                    <div key={h} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, height: '100%', justifyContent: 'flex-end' }}>
                      <div style={{
                        width: '100%', borderRadius: '2px 2px 0 0',
                        background: count > 0 ? 'var(--accent)' : 'rgba(255,255,255,0.04)',
                        height: `${Math.max(pct, count > 0 ? 8 : 4)}%`,
                        opacity: count > 0 ? 0.8 : 1,
                        transition: 'height 0.6s ease',
                      }} />
                    </div>
                  )
                })}
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8 }}>
              {['00', '06', '12', '18', '23'].map(h => (
                <span key={h} style={{ fontSize: 10, color: 'var(--text-muted)' }}>{h}:00</span>
              ))}
            </div>
          </div>
        </div>

        {/* Zone breakdown + Top hazards */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>

          {/* By zone */}
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 14, padding: '24px' }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.1em', fontWeight: 600, marginBottom: 20 }}>ALERTS BY ZONE</div>
            {Object.keys(byZone).length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: 13, textAlign: 'center', padding: '20px 0' }}>No data yet</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {Object.entries(byZone).sort((a, b) => b[1] - a[1]).map(([zone, count]) => {
                  const pct = Math.round((count / events.length) * 100)
                  return (
                    <div key={zone}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                        <span style={{ fontSize: 12, color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{zone}</span>
                        <span style={{ fontSize: 12, color: 'var(--text-primary)', fontWeight: 600 }}>{count} <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>({pct}%)</span></span>
                      </div>
                      <div style={{ height: 6, background: 'rgba(255,255,255,0.04)', borderRadius: 3 }}>
                        <div style={{
                          height: '100%', width: `${pct}%`,
                          background: 'linear-gradient(90deg, var(--accent), rgba(34,197,94,0.4))',
                          borderRadius: 3,
                        }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Risk pie-like */}
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 14, padding: '24px' }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.1em', fontWeight: 600, marginBottom: 20 }}>RISK DISTRIBUTION</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {riskItems.map(({ label, risk, val, color }) => {
                const pct = Math.round((val / total) * 100)
                return (
                  <div key={risk} style={{
                    display: 'flex', alignItems: 'center', gap: 14,
                    padding: '14px 16px', borderRadius: 10,
                    background: 'var(--bg-surface)', border: '1px solid var(--border)',
                  }}>
                    <div style={{
                      width: 44, height: 44, borderRadius: '50%',
                      background: `conic-gradient(${color} ${pct * 3.6}deg, rgba(255,255,255,0.04) 0deg)`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      flexShrink: 0,
                    }}>
                      <div style={{
                        width: 32, height: 32, borderRadius: '50%',
                        background: 'var(--bg-surface)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: 11, fontWeight: 700, color,
                      }}>{pct}%</div>
                    </div>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600, color }}>{label}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{val} events</div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* Recent events table */}
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 14, overflow: 'hidden' }}>
          <div style={{
            padding: '20px 24px', borderBottom: '1px solid var(--border)',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.1em', fontWeight: 600 }}>RECENT EVENTS</div>
            <Link href="/events" style={{
              fontSize: 12, color: 'var(--accent)', textDecoration: 'none',
              padding: '4px 10px', borderRadius: 6,
              border: '1px solid rgba(34,197,94,0.2)',
              background: 'rgba(34,197,94,0.06)',
            }}>View all</Link>
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {['#', 'Risk', 'Zone', 'Hazards', 'Time'].map(h => (
                  <th key={h} style={{
                    padding: '12px 20px', textAlign: 'left',
                    fontSize: 10, color: 'var(--text-muted)',
                    fontWeight: 600, letterSpacing: '0.1em',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {events.slice(0, 8).map((ev: any) => (
                <tr key={ev.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '12px 20px' }}>
                    <Link href={`/events/${ev.id}`} style={{ color: 'var(--accent)', textDecoration: 'none', fontSize: 12, fontWeight: 600 }}>#{ev.id}</Link>
                  </td>
                  <td style={{ padding: '12px 20px' }}><RiskBadge risk={ev.risk_level} /></td>
                  <td style={{ padding: '12px 20px', fontSize: 12, color: 'var(--text-secondary)' }}>
                    {ev.zone_id.replace(/_/g, ' ')}
                  </td>
                  <td style={{ padding: '12px 20px', fontSize: 12, color: 'var(--text-primary)', fontWeight: 600 }}>{ev.hazard_count}</td>
                  <td style={{ padding: '12px 20px', fontSize: 11, color: 'var(--text-muted)' }}>
                    {new Date(ev.triggered_at).toLocaleDateString('en-GB', {
                      day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false,
                    })}
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