import { fetchEvent, snapshotUrl } from '../../lib/api'
import Sidebar from '../../components/Sidebar'
import RiskBadge, { RISK_STYLE } from '../../components/RiskBadge'
import Link from 'next/link'
import { notFound } from 'next/navigation'

export default async function EventDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  let ev: any = null
  try { ev = await fetchEvent(Number(id)) } catch { notFound() }

  const promptA = ev.hazards?.filter((h: any) => h.source === 'prompt_a') || []
  const promptB = ev.hazards?.filter((h: any) => h.source !== 'prompt_a') || []

  return (
    <div style={{ display: 'flex' }}>
      <Sidebar />
      <main style={{ marginLeft: 220, flex: 1, padding: '32px 40px', minHeight: '100vh' }}>

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 28 }}>
          <Link href="/events" style={{ color: 'var(--text-muted)', textDecoration: 'none', fontSize: 13 }}>← Events</Link>
          <span style={{ color: 'var(--border)' }}>|</span>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.12em' }}>EVENT #{ev.id}</div>
          <RiskBadge risk={ev.risk_level} />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 420px', gap: 20 }}>

          {/* Left: snapshot + meta */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* Snapshot */}
            <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
              <div style={{ padding: '10px 16px', borderBottom: '1px solid var(--border)', fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.1em' }}>
                SNAPSHOT
              </div>
              <div style={{ background: '#000', position: 'relative' }}>
                <img
                  src={snapshotUrl(ev.id)}
                  alt="Event snapshot"
                  style={{ width: '100%', display: 'block', objectFit: 'contain' }}

                />
              </div>
            </div>

            {/* Situation summary */}
            {ev.situation_summary_th && (
              <div style={{
                background: 'var(--bg-card)', border: `1px solid ${RISK_STYLE[ev.risk_level]?.border || 'var(--border)'}`,
                borderRadius: 10, padding: 20,
                borderLeft: `3px solid ${RISK_STYLE[ev.risk_level]?.dot || 'var(--accent)'}`,
              }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: 10 }}>SITUATION SUMMARY</div>
                <div style={{ fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.7, marginBottom: 10 }}>{ev.situation_summary_th}</div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6, fontStyle: 'italic' }}>{ev.situation_summary_en}</div>
              </div>
            )}
          </div>

          {/* Right: hazards + meta */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* Meta */}
            <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, padding: 20 }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: 16 }}>EVENT INFO</div>
              {[
                { label: 'Zone', value: ev.zone_id.replace(/_/g, ' ').toUpperCase() },
                { label: 'Site', value: ev.site_id },
                { label: 'Person ID', value: ev.person_track_id ? `P${ev.person_track_id}` : '—' },
                { label: 'Speed', value: ev.person_speed ? `${ev.person_speed.toFixed(1)} px/f` : '—' },
                { label: 'Time', value: new Date(ev.triggered_at).toLocaleString('en-GB') },
                { label: 'Total hazards', value: ev.hazards?.length || 0 },
              ].map(({ label, value }) => (
                <div key={label} style={{
                  display: 'flex', justifyContent: 'space-between',
                  padding: '8px 0', borderBottom: '1px solid var(--border)',
                }}>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{label}</span>
                  <span style={{ fontSize: 12, color: 'var(--text-primary)', fontFamily: 'JetBrains Mono' }}>{value}</span>
                </div>
              ))}
            </div>

            {/* Person hazards */}
            {promptA.length > 0 && (
              <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, padding: 20 }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: 14 }}>PPE & BEHAVIOR</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {promptA.map((h: any, i: number) => {
                    const s = RISK_STYLE[h.risk] || RISK_STYLE.YELLOW
                    return (
                      <div key={i} style={{
                        padding: '10px 12px', borderRadius: 8,
                        background: s.bg, border: `1px solid ${s.border}`,
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                          <span style={{ fontSize: 11, color: s.color, fontFamily: 'JetBrains Mono', fontWeight: 500 }}>
                            {h.label.replace(/_/g, ' ')}
                          </span>
                          <RiskBadge risk={h.risk} />
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 2 }}>{h.reason_th}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic' }}>{h.reason_en}</div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Environment hazards */}
            {promptB.length > 0 && (
              <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, padding: 20 }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: 14 }}>ENVIRONMENT</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {promptB.map((h: any, i: number) => {
                    const s = RISK_STYLE[h.risk] || RISK_STYLE.YELLOW
                    return (
                      <div key={i} style={{
                        padding: '10px 12px', borderRadius: 8,
                        background: s.bg, border: `1px solid ${s.border}`,
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                          <span style={{ fontSize: 11, color: s.color, fontFamily: 'JetBrains Mono', fontWeight: 500 }}>
                            {h.label.replace(/_/g, ' ')}
                          </span>
                          <RiskBadge risk={h.risk} />
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 2 }}>{h.reason_th}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic' }}>{h.reason_en}</div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}