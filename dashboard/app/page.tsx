import { fetchStats, fetchEvents, snapshotUrl } from './lib/api'
import RiskBadge from './components/RiskBadge'
import Sidebar from './components/Sidebar'
import Link from 'next/link'

function StatCard({ label, value, sub, color, trend }: {
  label: string; value: string | number; sub?: string; color?: string; trend?: string
}) {
  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: 14,
      padding: '24px',
      position: 'relative',
      overflow: 'hidden',
      transition: 'border-color 0.2s',
    }}>
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: 2,
        background: color ? `linear-gradient(90deg, ${color}, transparent)` : 'transparent',
      }} />
      <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.1em', fontWeight: 600, marginBottom: 12 }}>{label}</div>
      <div style={{
        fontSize: 40, fontWeight: 800, color: color || 'var(--text-primary)',
        letterSpacing: '-0.02em', lineHeight: 1, marginBottom: 8,
        fontVariantNumeric: 'tabular-nums',
      }}>{value}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        {trend && <span style={{ fontSize: 11, color: 'var(--accent)', fontWeight: 500 }}>{trend}</span>}
        {sub && <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{sub}</span>}
      </div>
    </div>
  )
}

export default async function OverviewPage() {
  let stats = { total_events: 0, today_events: 0, by_risk: {} as Record<string, number> }
  let events: any[] = []
  try {
    stats = await fetchStats('robot_zone')
    events = await fetchEvents({ limit: 6 })
  } catch {}

  const red = stats.by_risk?.RED || 0
  const orange = stats.by_risk?.ORANGE || 0
  const yellow = stats.by_risk?.YELLOW || 0
  const total = red + orange + yellow || 1

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar />
      <main style={{ marginLeft: 240, flex: 1, padding: '40px 48px', maxWidth: 'calc(100vw - 240px)' }}>

        {/* Header */}
        <div style={{ marginBottom: 40 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.12em', fontWeight: 600 }}>OVERVIEW</span>
            <span style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--text-dim)', display: 'inline-block' }} />
            <span style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.08em' }}>ROBOT ZONE</span>
          </div>
          <h1 style={{
            fontSize: 32, fontWeight: 800, color: 'var(--text-primary)',
            letterSpacing: '-0.02em', lineHeight: 1.1,
          }}>Safety Dashboard</h1>
          <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 6 }}>
            Real-time AI-powered monitoring · ABB Robot Zone
          </p>
        </div>

        {/* Stat cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 32 }}>
          <StatCard label="TOTAL ALERTS" value={stats.total_events} sub="all time" color="var(--accent)" />
          <StatCard label="TODAY" value={stats.today_events} sub="last 24h" color="var(--accent)" />
          <StatCard label="CRITICAL" value={red} sub="RED risk" color="var(--red)" />
          <StatCard label="SERIOUS" value={orange + yellow} sub="ORANGE + YELLOW" color="var(--orange)" />
        </div>

        {/* Main grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: 20, marginBottom: 20 }}>

          {/* Risk breakdown */}
          <div style={{
            background: 'var(--bg-card)', border: '1px solid var(--border)',
            borderRadius: 14, padding: '24px',
          }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.1em', fontWeight: 600, marginBottom: 24 }}>RISK BREAKDOWN</div>
            
            {[
              { label: 'CRITICAL', sub: 'RED', val: red, color: 'var(--red)', bg: 'var(--red-dim)' },
              { label: 'SERIOUS', sub: 'ORANGE', val: orange, color: 'var(--orange)', bg: 'var(--orange-dim)' },
              { label: 'MINOR', sub: 'YELLOW', val: yellow, color: 'var(--yellow)', bg: 'var(--yellow-dim)' },
            ].map(({ label, sub, val, color, bg }) => (
              <div key={label} style={{ marginBottom: 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <div>
                    <span style={{ fontSize: 12, color, fontWeight: 600 }}>{label}</span>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 6 }}>· {sub}</span>
                  </div>
                  <span style={{
                    fontSize: 20, fontWeight: 700, color,
                    fontVariantNumeric: 'tabular-nums',
                  }}>{val}</span>
                </div>
                <div style={{ height: 6, background: 'rgba(255,255,255,0.04)', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{
                    height: '100%',
                    width: `${Math.round((val / total) * 100)}%`,
                    background: color,
                    borderRadius: 3,
                    transition: 'width 0.8s cubic-bezier(0.4,0,0.2,1)',
                    opacity: 0.8,
                  }} />
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                  {Math.round((val / total) * 100)}% of total
                </div>
              </div>
            ))}
          </div>

          {/* Recent alerts */}
          <div style={{
            background: 'var(--bg-card)', border: '1px solid var(--border)',
            borderRadius: 14, padding: '24px',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.1em', fontWeight: 600 }}>RECENT ALERTS</div>
              <Link href="/events" style={{
                fontSize: 12, color: 'var(--accent)', textDecoration: 'none',
                padding: '4px 10px', borderRadius: 6,
                border: '1px solid rgba(34,197,94,0.2)',
                background: 'rgba(34,197,94,0.06)',
                fontWeight: 500,
              }}>View all</Link>
            </div>

            {events.length === 0 ? (
              <div style={{
                display: 'flex', flexDirection: 'column', alignItems: 'center',
                justifyContent: 'center', padding: '40px 0',
                color: 'var(--text-muted)', fontSize: 13,
              }}>
                <div style={{ fontSize: 32, marginBottom: 12, opacity: 0.3 }}>◎</div>
                No alerts yet
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {events.map((ev: any) => (
                  <Link key={ev.id} href={`/events/${ev.id}`} style={{ textDecoration: 'none' }}>
                    <div style={{
                      display: 'flex', alignItems: 'center', gap: 14,
                      padding: '14px 16px', borderRadius: 10,
                      background: 'var(--bg-surface)',
                      border: '1px solid var(--border)',
                      cursor: 'pointer',
                      transition: 'border-color 0.15s, background 0.15s',
                    }}>
                      {/* Snapshot thumbnail */}
                      <div style={{
                        width: 52, height: 36, borderRadius: 6,
                        background: 'var(--bg-elevated)',
                        overflow: 'hidden', flexShrink: 0,
                      }}>
                        <img
                          src={snapshotUrl(ev.id)}
                          alt=""
                          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                        />
                      </div>

                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
                          <RiskBadge risk={ev.risk_level} />
                          <span style={{ fontSize: 12, color: 'var(--text-primary)', fontWeight: 500 }}>
                            {ev.zone_id.replace(/_/g, ' ').toUpperCase()}
                          </span>
                        </div>
                        <div style={{
                          fontSize: 11, color: 'var(--text-muted)',
                          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                        }}>
                          {ev.situation_summary_en || `${ev.hazard_count} hazards detected`}
                        </div>
                      </div>

                      <div style={{ textAlign: 'right', flexShrink: 0 }}>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums' }}>
                          {new Date(ev.triggered_at).toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit' })}
                        </div>
                        <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 2 }}>
                          {new Date(ev.triggered_at).toLocaleDateString('en', { month: 'short', day: 'numeric' })}
                        </div>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Bottom: Hazard type breakdown */}
        <div style={{
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          borderRadius: 14, padding: '24px',
        }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.1em', fontWeight: 600, marginBottom: 20 }}>SYSTEM INFO</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
            {[
              { label: 'AI Model', value: 'YOLO11m-pose' },
              { label: 'VLM', value: 'Gemini 2.5 Flash' },
              { label: 'Camera', value: 'HEVC 1080p' },
              { label: 'Processing', value: 'Jetson Orin' },
            ].map(({ label, value }) => (
              <div key={label} style={{
                padding: '16px', borderRadius: 10,
                background: 'var(--bg-surface)', border: '1px solid var(--border)',
              }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.08em', marginBottom: 6, fontWeight: 600 }}>{label}</div>
                <div style={{ fontSize: 13, color: 'var(--text-primary)', fontWeight: 500 }}>{value}</div>
              </div>
            ))}
          </div>
        </div>

      </main>
    </div>
  )
}