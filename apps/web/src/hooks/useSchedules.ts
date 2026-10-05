import { useCallback, useEffect, useState } from 'react'
import { fetchSchedules, type Schedule } from '@/api/schedules'

export function useSchedules(filters: { roomId?: string; sceneId?: string } = {}) {
  const { roomId, sceneId } = filters
  const [data, setData] = useState<Schedule[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    try {
      setData(await fetchSchedules({ roomId, sceneId }))
      setError(null)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Không tải được lịch tự động')
    } finally {
      setLoading(false)
    }
  }, [roomId, sceneId])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch external schedule state on mount/filter change
    void reload()
    const timer = window.setInterval(() => void reload(), 60_000)
    const onExecuted = () => void reload()
    window.addEventListener('schedule.executed', onExecuted)
    return () => {
      window.clearInterval(timer)
      window.removeEventListener('schedule.executed', onExecuted)
    }
  }, [reload])

  return { data, loading, error, reload }
}
