export const SITE_NAME = 'HomeMate'
export const SITE_FULL_NAME = 'HomeMate — Ngôi nhà thông minh'
export const SITE_DESCRIPTION =
  'Hệ thống quản lý và điều khiển ngôi nhà thông minh với trợ lý ảo HomeMate AI.'

export const LOADING_PAGE_TITLE = SITE_FULL_NAME

export const PAGE_TITLES = {
  login: 'Đăng nhập',
  dashboard: 'Trang chủ',
  room: 'Phòng',
  energy: 'Điện năng',
  devices: 'Thiết bị',
  camera: 'Camera',
  scenes: 'Kịch bản',
  schedules: 'Lịch tự động',
  settings: 'Cài đặt',
  voice: 'Giọng nói',
  voiceAgent: 'Voice Agent',
  clarify: 'Làm rõ lệnh',
  hitl: 'Xác nhận HITL',
  scenarios: 'Kịch bản',
  mock: 'Mock ngoại cảnh',
  uiKit: 'UI Kit',
} as const

export function formatPageTitle(pageTitle: string): string {
  if (pageTitle === SITE_FULL_NAME) return SITE_FULL_NAME
  return `${pageTitle} | ${SITE_NAME}`
}
