export const HOUSE_NAME = 'Michelin Bois'

export { INITIAL_DEVICES } from '@/mocks/devices'
export type { Device, DeviceIconKind, DeviceControl } from '@/types/device'

export const COMMAND_LOGS = [
  {
    command: 'Tối đón khách...',
    time: '19:42',
    result: 'Hoàn thành',
    resultTone: 'success' as const,
    note: '—',
    noteTone: 'muted' as const,
  },
  {
    command: 'Mở khóa cửa chính',
    time: '19:38',
    result: 'Hoàn thành',
    resultTone: 'success' as const,
    note: 'Có HITL',
    noteTone: 'warning' as const,
  },
  {
    command: 'Bật đèn',
    time: '19:20',
    result: 'Đã hỏi lại',
    resultTone: 'secondary' as const,
    note: 'Phòng nào?',
    noteTone: 'muted' as const,
  },
] as const
