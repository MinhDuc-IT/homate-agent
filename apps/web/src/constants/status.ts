export const STATUS_VARIANTS = {
  warning: 'warning',
  pending: 'pending',
  success: 'success',
  error: 'error',
  neutral: 'neutral',
} as const

export type StatusVariant = (typeof STATUS_VARIANTS)[keyof typeof STATUS_VARIANTS]
