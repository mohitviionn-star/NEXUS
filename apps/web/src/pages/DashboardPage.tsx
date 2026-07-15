import { useEffect, useState } from 'react'
import { useAuth } from '../AuthContext'

type ServiceRecord = {
  id: number
  name: string
  slug: string
  health_check_url: string
  status: string
}

type IncidentRecord = {
  id: number
  service_id: number
  severity: string
  status: string
  opened_at: string
  resolved_at: string | null
}

const badgeStyles: Record<string, string> = {
  healthy: 'bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30',
  unhealthy: 'bg-red-500/15 text-red-400 ring-1 ring-red-500/30',
  unknown: 'bg-slate-500/15 text-slate-400 ring-1 ring-slate-500/30',
  open: 'bg-red-500/15 text-red-400 ring-1 ring-red-500/30',
  resolved: 'bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30',
}

function StatusDot({ status }: { status: string }) {
  const color =
    status === 'healthy' || status === 'resolved'
      ? 'bg-emerald-400'
      : status === 'unhealthy' || status === 'open'
        ? 'bg-red-400'
        : 'bg-slate-400'
  return <span className={`inline-block h-2.5 w-2.5 rounded-full ${color}`} />
}

// Backend timestamps are plain UTC with no "Z" suffix - add it so the
// browser parses them as UTC instead of guessing it's local time.
function formatTimestamp(value: string) {
  return new Date(value.endsWith('Z') ? value : `${value}Z`).toLocaleString()
}

export default function DashboardPage() {
  const { authFetch, logout } = useAuth()
  const [services, setServices] = useState<ServiceRecord[]>([])
  const [incidents, setIncidents] = useState<IncidentRecord[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        // authFetch automatically refreshes an expired access token and
        // retries once - we only end up here if that also failed.
        const [servicesRes, incidentsRes] = await Promise.all([
          authFetch('/api/v1/services'),
          authFetch('/api/v1/incidents'),
        ])

        setServices(await servicesRes.json())
        setIncidents(await incidentsRes.json())
        setError(null)
      } catch {
        logout() // refresh token was also invalid/expired - back to login
      }
    }

    load()
    const interval = setInterval(load, 3000)
    return () => clearInterval(interval)
  }, [authFetch, logout])

  const openIncidents = incidents.filter((incident) => incident.status === 'open')

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <header className="flex items-center justify-between border-b border-slate-800 px-8 py-4">
        <div>
          <h1 className="text-lg font-semibold">NEXUS Mission Control</h1>
          <p className="text-sm text-slate-400">
            {openIncidents.length === 0
              ? 'All systems normal'
              : `${openIncidents.length} open incident${openIncidents.length > 1 ? 's' : ''}`}
          </p>
        </div>
        <button
          onClick={logout}
          className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 transition hover:bg-slate-800"
        >
          Log out
        </button>
      </header>

      <main className="mx-auto max-w-5xl px-8 py-8">
        {error && <p className="mb-6 text-sm text-red-400">{error}</p>}

        <section className="mb-10">
          <h2 className="mb-4 text-sm font-medium tracking-wide text-slate-400 uppercase">Services</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {services.map((service) => (
              <div key={service.id} className="rounded-xl border border-slate-800 bg-slate-900 p-5">
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="font-medium">{service.name}</h3>
                  <StatusDot status={service.status} />
                </div>
                <span
                  className={`inline-block rounded-full px-2.5 py-1 text-xs font-medium ${
                    badgeStyles[service.status] ?? badgeStyles.unknown
                  }`}
                >
                  {service.status}
                </span>
              </div>
            ))}
            {services.length === 0 && !error && (
              <p className="text-sm text-slate-500">No services registered yet.</p>
            )}
          </div>
        </section>

        <section>
          <h2 className="mb-4 text-sm font-medium tracking-wide text-slate-400 uppercase">Incidents</h2>
          <div className="overflow-hidden rounded-xl border border-slate-800">
            {incidents.length === 0 && (
              <p className="bg-slate-900 p-5 text-sm text-slate-500">No incidents recorded yet.</p>
            )}
            {incidents.map((incident) => {
              const service = services.find((s) => s.id === incident.service_id)
              return (
                <div
                  key={incident.id}
                  className="flex items-center justify-between border-b border-slate-800 bg-slate-900 px-5 py-4 last:border-b-0"
                >
                  <div className="flex items-center gap-3">
                    <StatusDot status={incident.status} />
                    <div>
                      <p className="font-medium">{service?.name ?? `Service #${incident.service_id}`}</p>
                      <p className="text-xs text-slate-500">Opened {formatTimestamp(incident.opened_at)}</p>
                    </div>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                      badgeStyles[incident.status] ?? badgeStyles.unknown
                    }`}
                  >
                    {incident.status}
                  </span>
                </div>
              )
            })}
          </div>
        </section>
      </main>
    </div>
  )
}
