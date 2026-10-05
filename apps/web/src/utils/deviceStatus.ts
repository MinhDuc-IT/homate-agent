import type {
  ControlWhen,
  Device,
  DeviceControl,
  DeviceState,
  DeviceStateValue,
} from '@/types/device'

export function matchesWhen(when: ControlWhen | undefined, state: DeviceState): boolean {
  if (!when) return true
  return Object.entries(when).every(([key, expected]) => state[key] === expected)
}

export function visibleControls(device: Device): DeviceControl[] {
  return device.controls.filter((control) => matchesWhen(control.when, device.state))
}

export function isDeviceActive(device: Device): boolean {
  const { state, controls } = device

  const level = controls.find((c) => c.type === 'level')
  if (level && typeof state[level.key] === 'number') {
    return (state[level.key] as number) > 0
  }

  if (typeof state.power === 'boolean') return state.power
  if (typeof state.recording === 'boolean') return state.recording
  if (typeof state.locked === 'boolean') return !state.locked
  if (typeof state.position === 'number') return state.position > 0

  return false
}

function labelForEnum(control: DeviceControl, value: DeviceStateValue): string | undefined {
  if (control.type !== 'enum') return undefined
  return control.options.find((o) => o.value === value)?.label
}

function labelForLevel(control: DeviceControl, value: DeviceStateValue): string | undefined {
  if (control.type !== 'level' || typeof value !== 'number') return undefined
  const index = control.levels.indexOf(value)
  return index >= 0 ? control.labels[index] : String(value)
}

/** Human-readable one-line status for device cards. */
export function formatDeviceStatus(device: Device): string {
  const { state, controls } = device
  const parts: string[] = []

  const toggle = controls.find((c) => c.type === 'toggle' && c.key === 'power')
  if (toggle && typeof state.power === 'boolean') {
    parts.push(state.power ? 'Bật' : 'Tắt')
  }

  const level = controls.find((c) => c.type === 'level')
  if (level && state[level.key] !== undefined) {
    const label = labelForLevel(level, state[level.key])
    if (label) {
      if (typeof state[level.key] === 'number' && (state[level.key] as number) === 0) {
        return label
      }
      parts.push(label.startsWith('Nút') || label === 'Tắt' ? label : `Nút ${label}`)
    }
  }

  for (const control of controls) {
    if (!matchesWhen(control.when, state)) continue
    const value = state[control.key]
    if (value === undefined) continue

    if (control.type === 'range' || control.type === 'step') {
      if (typeof value !== 'number') continue
      if (control.key === 'power') continue
      const unit = control.unit ?? ''
      if (control.key === 'brightness') {
        parts.push(`${value}${unit || '%'}`)
        continue
      }
      if (control.key === 'volume') {
        parts.push(`âm lượng ${value}${unit || '%'}`)
        continue
      }
      if (control.key === 'temperature') {
        parts.push(`${value}${unit || '°C'}`)
        continue
      }
      if (control.key === 'position') {
        parts.push(`${value}${unit || '%'}`)
        continue
      }
      parts.push(`${value}${unit}`)
    }

    if (control.type === 'enum') {
      const label = labelForEnum(control, value)
      if (label) parts.push(label)
    }

    if (control.type === 'toggle' && control.key !== 'power' && typeof value === 'boolean') {
      if (control.key === 'recording') {
        parts.push(value ? 'Đang ghi' : 'Tắt ghi')
      }
    }

    if (control.type === 'action' && control.key === 'unlock' && state.locked === true) {
      parts.push('Đã khóa')
    }
  }

  if (typeof state.locked === 'boolean' && !parts.includes('Đã khóa') && !parts.includes('Đã mở')) {
    parts.push(state.locked ? 'Đã khóa' : 'Đã mở')
  }

  // Deduplicate while preserving order
  const unique = [...new Set(parts.filter(Boolean))]
  return unique.length > 0 ? unique.join(' · ') : '—'
}

export function hasQuickToggle(device: Device): boolean {
  return device.controls.some(
    (c) =>
      (c.type === 'toggle' && (c.key === 'power' || c.key === 'recording')) ||
      c.type === 'level',
  )
}

export function patchDeviceState(
  device: Device,
  key: string,
  value: DeviceStateValue,
): Device {
  const nextState: DeviceState = { ...device.state, [key]: value }

  // Keep curtain preset roughly in sync with position when either changes
  if (key === 'position' && typeof value === 'number') {
    if (value <= 5) nextState.preset = 'closed'
    else if (value <= 40) nextState.preset = 'ajar'
    else nextState.preset = 'open'
  }
  if (key === 'preset' && typeof value === 'string') {
    if (value === 'closed') nextState.position = 0
    else if (value === 'ajar') nextState.position = 30
    else if (value === 'open') nextState.position = 100
  }

  // Turning off power can leave secondary values as-is (UI hides via `when`)
  if (key === 'power' && value === false) {
    // no-op extras
  }

  return { ...device, state: nextState }
}
