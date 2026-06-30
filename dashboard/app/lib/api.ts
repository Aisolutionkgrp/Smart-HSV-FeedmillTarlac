const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function fetchEvents(params?: { site_id?: string; risk_level?: string; limit?: number }) {
  const q = new URLSearchParams()
  if (params?.site_id) q.set('site_id', params.site_id)
  if (params?.risk_level) q.set('risk_level', params.risk_level)
  if (params?.limit) q.set('limit', String(params.limit))
  const res = await fetch(`${API}/api/events?${q}`, { cache: 'no-store' })
  if (!res.ok) throw new Error('Failed to fetch events')
  return res.json()
}

export async function fetchEvent(id: number) {
  const res = await fetch(`${API}/api/events/${id}`, { cache: 'no-store' })
  if (!res.ok) throw new Error('Not found')
  return res.json()
}

export async function fetchStats(site_id?: string) {
  const q = site_id ? `?site_id=${site_id}` : ''
  const res = await fetch(`${API}/api/stats${q}`, { cache: 'no-store' })
  if (!res.ok) throw new Error('Failed to fetch stats')
  return res.json()
}

export function snapshotUrl(id: number) {
  return `${API}/api/events/${id}/image`
}

export function streamUrl(site_id: string) {
  return `${API}/stream/${site_id}`
}
