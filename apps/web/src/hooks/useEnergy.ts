import { useEffect, useState } from 'react'
import { fetchEnergy } from '@/api/energy'
import type { EnergyPeriod, EnergyReport } from '@/types/energy'

export function useEnergy(
  period: EnergyPeriod,
  filters: { roomId?: string; deviceId?: string; anchor?: string } = {},
) {
  const [data, setData] = useState<EnergyReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const roomId = filters.roomId
  const deviceId = filters.deviceId
  const anchor = filters.anchor

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)
    setData(null)

    const load = () => {
      void fetchEnergy(period, { roomId, deviceId, anchor })
        .then((result) => {
          if (active) {
            setData(result)
            setError(null)
          }
        })
        .catch((reason: unknown) => {
          if (active) setError(reason instanceof Error ? reason.message : 'Không tải được điện năng')
        })
        .finally(() => {
          if (active) setLoading(false)
        })
    }
    load()
    const timer = window.setInterval(load, 60_000)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [period, roomId, deviceId, anchor])

  return { data, loading, error }
}
