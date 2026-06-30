'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

const nav = [
  { href: '/', label: 'Overview', icon: '⊞' },
  { href: '/live', label: 'Live Monitor', icon: '◉' },
  { href: '/events', label: 'Events', icon: '≡' },
  { href: '/stats', label: 'Analytics', icon: '⟁' },
]

export default function Sidebar() {
  const path = usePathname()
  return (
    <aside style={{
      width: 240,
      minHeight: '100vh',
      background: 'var(--bg-surface)',
      borderRight: '1px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
      position: 'fixed',
      left: 0, top: 0, bottom: 0,
      zIndex: 50,
    }}>
      {/* Logo */}
      <div style={{ padding: '28px 24px 20px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 36, height: 36,
            background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
            borderRadius: 10,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 16, fontWeight: 800, color: '#fff',
            boxShadow: '0 4px 12px rgba(34,197,94,0.3)',
          }}>H</div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>HSV</div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.12em', marginTop: 1 }}>SAFETY VISION</div>
          </div>
        </div>
      </div>

      {/* Status */}
      <div style={{ padding: '14px 24px', borderBottom: '1px solid var(--border)' }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 7,
          padding: '5px 10px', borderRadius: 6,
          background: 'rgba(34,197,94,0.08)',
          border: '1px solid rgba(34,197,94,0.15)',
        }}>
          <span style={{
            width: 7, height: 7, borderRadius: '50%',
            background: 'var(--accent)',
            display: 'inline-block',
            animation: 'blink 2s ease infinite',
          }} />
          <span style={{ fontSize: 11, color: 'var(--accent)', fontWeight: 500, letterSpacing: '0.08em' }}>SYSTEM ONLINE</span>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ padding: '16px 12px', flex: 1 }}>
        <div style={{ fontSize: 10, color: 'var(--text-dim)', letterSpacing: '0.12em', padding: '0 12px 8px', fontWeight: 600 }}>NAVIGATION</div>
        {nav.map(item => {
          const active = path === item.href
          return (
            <Link key={item.href} href={item.href} style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '9px 12px', borderRadius: 8, marginBottom: 2,
              background: active ? 'rgba(34,197,94,0.08)' : 'transparent',
              border: active ? '1px solid rgba(34,197,94,0.15)' : '1px solid transparent',
              color: active ? 'var(--accent)' : 'var(--text-secondary)',
              textDecoration: 'none', fontSize: 13, fontWeight: active ? 500 : 400,
              transition: 'all 0.12s ease',
              position: 'relative',
            }}>
              {active && (
                <span style={{
                  position: 'absolute', left: 0, top: '50%', transform: 'translateY(-50%)',
                  width: 3, height: 16, background: 'var(--accent)',
                  borderRadius: '0 2px 2px 0',
                }} />
              )}
              <span style={{ fontSize: 13, width: 20, textAlign: 'center', opacity: active ? 1 : 0.6 }}>{item.icon}</span>
              {item.label}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div style={{ padding: '16px 24px', borderTop: '1px solid var(--border)' }}>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.8 }}>
          <div style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Robot Zone · CAM 1</div>
          <div>v1.0.0 · Jetson Orin</div>
        </div>
      </div>

      <style>{`@keyframes blink{0%,100%{opacity:1}50%{opacity:0.4}}`}</style>
    </aside>
  )
}