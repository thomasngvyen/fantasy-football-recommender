import type {
  CompareRequest,
  CompareResponse,
  PlayerOut,
  Position,
} from './types'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

async function parseError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown }
    if (typeof body.detail === 'string') {
      return body.detail
    }
    if (Array.isArray(body.detail)) {
      return body.detail.map((item) => JSON.stringify(item)).join('; ')
    }
    return response.statusText || 'Request failed'
  } catch {
    return response.statusText || 'Request failed'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })

  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  return response.json() as Promise<T>
}

export async function getPlayers(position?: Position): Promise<PlayerOut[]> {
  const query = position ? `?position=${encodeURIComponent(position)}` : ''
  return request<PlayerOut[]>(`/players${query}`)
}

export async function comparePlayers(
  payload: CompareRequest,
): Promise<CompareResponse> {
  return request<CompareResponse>('/compare', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function checkHealth(): Promise<boolean> {
  try {
    const data = await request<{ status: string }>('/health')
    return data.status === 'ok'
  } catch {
    return false
  }
}
