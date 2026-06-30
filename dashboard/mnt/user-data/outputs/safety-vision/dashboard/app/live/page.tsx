'use client'
import { useEffect, useState } from 'react'
import Sidebar from '../components/Sidebar'
import RiskBadge from '../components/RiskBadge'
import Link from 'next/link'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function LivePage() {
  const [events, setEvents] = useState<any[]>([])
  const [imgSrc, setImgSrc] = useState(`${API}/stream/robot_zone`)
  const [lastUpdate, setLastUpdate] = useState('')

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch(`${API}/api/events?limit=10`, { cache: 'no-store' })
        const data = await res.json()
        setEvents(data)
        setLastUpdate(new Date().toLocaleTimeString('th-TH'))
      } catch {}
    }
    load()
    const t = setInterval(load, 5000)
    return () => clearInterval(t)
  }, [])

  return (
    <div style={{ display: 'flex' }}>
      <Sidebar />
      <main style={{ marginLeft: 220, flex: 1, padding: '32px 40px', minHeight: '100vh' }}>

        <div style={{ marginBottom: 28 }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.12em', marginBottom: 4 }}>LIVE MONITOR</div>
          <h1 style={{ fontSize: 24, fontWeight: 600 }}>Robot Zone · Camera 1</h1>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 20 }}>

          {/* Camera feed */}
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '12px 16px', borderBottom: '1px solid var(--border)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--accent)', animation: 'pulse 2s infinite' }} />
                <span style={{ fontSize: 12, color: 'var(--accent)', fontFamily: 'JetBrains Mono' }}>LIVE</span>
              </div>
              <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'JetBrains Mono' }}>ROBOT RIGHT WING</span>
            </div>
            <div style={{ position: 'relative', background: '#000', aspectRatio: '16/9' }}>
              <img
                src={imgSrc}
                alt="Live camera feed"
                style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
                onError={() => setImgSrc(`${API}/stream/robot_zone`)}
              />
            </div>
          </div>

          {/* Recent alerts sidebar */}
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, display: 'flex', flexDirection: 'column' }}>
            <div style={{
              padding: '12px 16px', borderBottom: '1px solid var(--border)',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
              <span style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.1em' }}>RECENT ALERTS</span>
              <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'JetBrains Mono' }}>{lastUpdate}</span>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
              {events.length === 0 && (
                <div style={{ color: 'var(--text-muted)', fontSize: 12, padding: 20, textAlign: 'center' }}>No alerts yet</div>
              )}
              {events.map((ev: any) => (
                <Link key={ev.id} href={`/events/${ev.id}`} style={{ textDecoration: 'none' }}>
                  <div style={{
                    padding: '10px 12px', borderRadius: 8,
                    background: 'var(--bg-surface)', border: '1px solid var(--border)',
                    cursor: 'pointer',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                      <RiskBadge risk={ev.risk_level} />
                      <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'JetBrains Mono' }}>
                        {new Date(ev.triggered_at).toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 3 }}>
                      {ev.zone_id.replace(/_/g, ' ').toUpperCase()}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                      {ev.hazard_count} hazard{ev.hazard_count !== 1 ? 's' : ''} detected
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
        <style>{`@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}`}</style>
      </main>
    </div>
  )
}
