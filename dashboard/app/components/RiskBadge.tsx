export const RISK_STYLE: Record<string, { bg: string; color: string; border: string; dot: string }> = {
  RED:    { bg: 'rgba(232,84,84,0.12)',  color: '#e85454', border: 'rgba(232,84,84,0.3)',  dot: '#e85454' },
  ORANGE: { bg: 'rgba(232,126,53,0.12)', color: '#e87e35', border: 'rgba(232,126,53,0.3)', dot: '#e87e35' },
  YELLOW: { bg: 'rgba(232,192,53,0.12)', color: '#e8c035', border: 'rgba(232,192,53,0.3)', dot: '#e8c035' },
  GREEN:  { bg: 'rgba(92,184,92,0.12)',  color: '#5cb85c', border: 'rgba(92,184,92,0.3)',  dot: '#5cb85c' },
}

export default function RiskBadge({ risk }: { risk: string }) {
  const s = RISK_STYLE[risk] || RISK_STYLE.YELLOW
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      padding: '3px 8px', borderRadius: 4,
      background: s.bg, color: s.color, border: `1px solid ${s.border}`,
      fontSize: 11, fontWeight: 600, fontFamily: 'JetBrains Mono', letterSpacing: '0.06em',
    }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: s.dot, display: 'inline-block' }} />
      {risk}
    </span>
  )
}
