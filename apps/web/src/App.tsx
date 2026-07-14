import { useEffect, useState } from 'react'

type ServiceCheck = {
  name: string
  url: string
}

const services: ServiceCheck[] = [
  { name: 'Platform API', url: 'http://localhost:8000/health' },
  { name: 'Payment Service', url: 'http://localhost:8001/health' },
]

function App() {
  const [statuses, setStatuses] = useState<Record<string, string>>({})

  useEffect(() => {
    const checkAll = () => {
      services.forEach((service) => {
        fetch(service.url)
          .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
          .then(({ ok, data }) =>
            setStatuses((prev) => ({
              ...prev,
              [service.name]: ok ? data.status : `error (${data.detail})`,
            }))
          )
          .catch(() =>
            setStatuses((prev) => ({ ...prev, [service.name]: 'unreachable' }))
          )
      })
    }

    checkAll()
    const interval = setInterval(checkAll, 3000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div style={{ fontFamily: 'sans-serif', padding: '2rem' }}>
      <h1>NEXUS Mission Control</h1>
      <ul>
        {services.map((service) => (
          <li key={service.name} style={{ fontSize: '1.2rem', margin: '0.5rem 0' }}>
            {service.name}: <strong>{statuses[service.name] ?? 'checking...'}</strong>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default App
