export type EnergyPeriod = 'today' | '7days' | '30days' | '3months' | 'week' | 'month' | 'year'

export type EnergyBreakdown = {
  id: string
  name: string
  kwh: number
  current_power_w?: number
  active_minutes_today?: number
  current_session_minutes?: number
  room_id?: string
  kind?: string
}

export type EnergyPoint = { bucket: string; kwh: number }

export type EnergyReport = {
  period: EnergyPeriod
  from: string
  to: string
  total_kwh: number
  previous_total_kwh: number
  change_percent: number | null
  estimated_cost: number | null
  currency: string
  source: 'estimated' | 'measured' | 'mixed'
  measurement_coverage: number
  timeseries: EnergyPoint[]
  by_device: EnergyBreakdown[]
  by_room: EnergyBreakdown[]
}
