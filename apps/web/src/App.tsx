import { useEffect, useState } from 'react'

type ServiceRecord = {
  id: number
  name: string
  slug: string
  health_check_url: string
}

function App() {
  const [services, setServices] = useState<ServiceRecord[]>([])
  const [statuses, setStatuses] = useState<Record<string, string>>({})

  // Fetch the registered services list once when the page loads.
  useEffect(() => {
    fetch('http://localhost:8000/api/v1/services')
      .then((res) => res.json())
      .then(setServices)
      .catch(() => setServices([]))
  }, [])

  // Once we know which services exist, keep checking each one's health.
  useEffect(() => {
    if (services.length === 0) return

    const checkAll = () => {
      services.forEach((service) => {
        fetch(service.health_check_url)
          .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
          .then(({ ok, data }) =>
            setStatuses((prev) => ({
              ...prev,
              [service.slug]: ok ? data.status : `error (${data.detail})`,
            }))
          )
          .catch(() =>
            setStatuses((prev) => ({ ...prev, [service.slug]: 'unreachable' }))
          )
      })
    }

    checkAll()
    const interval = setInterval(checkAll, 3000)
    return () => clearInterval(interval)
  }, [services])

  return (
    <div style={{ fontFamily: 'sans-serif', padding: '2rem' }}>
      <h1>NEXUS Mission Control</h1>
      <ul>
        {services.map((service) => (
          <li key={service.id} style={{ fontSize: '1.2rem', margin: '0.5rem 0' }}>
            {service.name}: <strong>{statuses[service.slug] ?? 'checking...'}</strong>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default App
