import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { LogoIcon } from '@/assets/icons/HomemateIcons'
import { ShieldLockIcon } from '@/assets/icons/HomeMindIcons'
import { ROUTES } from '@/config/routes'
import { SITE_NAME } from '@/config/site'
import { useSession } from '@/context/SessionContext'
import { useToast } from '@/context/ToastContext'
import { cn } from '@/utils/cn'

export function Login() {
  const navigate = useNavigate()
  const { session, login, houseName, members, homeLoading, homeError } = useSession()
  const { showToast } = useToast()
  const [selected, setSelected] = useState('')
  const [pin, setPin] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const activeId = selected || (members.length > 0 ? members[0].id : '')

  if (session) {
    return <Navigate to={ROUTES.dashboard} replace />
  }

  const enter = async () => {
    if (homeLoading || !activeId) {
      showToast('Đang tải danh sách thành viên…', 'error')
      return
    }
    if (pin.length !== 4) {
      showToast('Vui lòng nhập mã PIN 4 số', 'error')
      return
    }
    const member = members.find((m) => m.id === activeId)
    if (!member) {
      showToast('Không tìm thấy thành viên', 'error')
      return
    }
    setSubmitting(true)
    try {
      await login(activeId, pin)
      showToast(`Xin chào ${member.name}`, 'success')
      navigate(ROUTES.dashboard, { replace: true })
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Đăng nhập thất bại', 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="relative flex min-h-screen w-full items-center justify-center lg:justify-start overflow-x-hidden bg-slate-900">
      {/* Full-screen smart-home background image */}
      <div
        className="absolute inset-0 bg-cover bg-center lg:bg-right no-repeat transition-all duration-700"
        style={{
          backgroundImage: "url('/assets/images/login.jpg')",
        }}
      />

      {/* Subtle adaptive gradient overlays to ensure high contrast for the form while preserving right-side smart-home graphics */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-slate-950/60 via-transparent to-black/20 lg:hidden" />
      <div className="pointer-events-none absolute inset-y-0 left-0 hidden lg:block w-1/2 bg-gradient-to-r from-white/40 via-white/15 to-transparent" />

      {/* Main Container - Left-aligned on desktop */}
      <div className="relative z-10 flex w-full items-center justify-center lg:justify-start px-4 py-8 sm:px-8 md:px-12 lg:px-16 xl:px-24">
        {/* Glassmorphism Card */}
        <div className="relative w-full max-w-[430px] rounded-3xl border border-white/70 bg-[#FCFDFD]/85 p-6 sm:p-8 shadow-[0_20px_50px_-10px_rgba(15,23,42,0.18),0_0_0_1px_rgba(255,255,255,0.9)_inset] backdrop-blur-2xl">
          {/* Subtle cyan ambient glow at top corner */}
          <div className="pointer-events-none absolute -top-8 -right-8 h-32 w-32 rounded-full bg-cyan-400/20 blur-2xl" />

          {/* Header */}
          <div className="relative mb-6">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-[#1E4D38] to-[#2D6A4F] p-2 shadow-sm shadow-[#1E4D38]/30 ring-1 ring-white/60">
                  <LogoIcon className="h-full w-full" />
                </div>
                <div>
                  <h1 className="font-display text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">
                    {SITE_NAME}
                  </h1>
                  <p className="text-[11px] font-medium tracking-wide text-slate-500 uppercase">
                    AI Smart Home Hub
                  </p>
                </div>
              </div>

              {/* Cyan Live System Badge */}
              <div className="inline-flex items-center gap-1.5 rounded-full border border-cyan-300/60 bg-cyan-50/90 px-2.5 py-1 text-[11px] font-medium text-cyan-800 shadow-xs">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan-400 opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-cyan-500" />
                </span>
                <span>Online</span>
              </div>
            </div>

            {/* House Status Pill */}
            <div className="flex items-center gap-2 rounded-xl border border-slate-200/70 bg-white/70 px-3 py-2 text-xs text-slate-700 shadow-xs backdrop-blur-sm">
              <span className="h-2 w-2 shrink-0 rounded-full bg-emerald-500 ring-2 ring-emerald-200" />
              <span className="truncate font-medium">
                {homeLoading ? 'Đang kết nối hệ thống nhà…' : houseName || 'Hệ thống Nhà thông minh'}
              </span>
            </div>

            {homeError ? (
              <div className="mt-2.5 rounded-xl border border-red-200 bg-red-50/90 p-2.5 text-xs text-red-700">
                {homeError}
              </div>
            ) : null}
          </div>

          {/* Member Picker */}
          <div className="mb-5">
            <div className="mb-2.5 flex items-center justify-between">
              <label className="text-xs font-semibold tracking-wider text-slate-700 uppercase">
                Chọn thành viên
              </label>
              {members.length > 0 && (
                <span className="text-[11px] font-medium text-cyan-700">
                  {members.length} tài khoản
                </span>
              )}
            </div>

            <div className="grid grid-cols-3 gap-2.5 sm:gap-3">
              {members.map((member) => {
                const active = activeId === member.id
                return (
                  <button
                    key={member.id}
                    type="button"
                    onClick={() => setSelected(member.id)}
                    className={cn(
                      'group relative flex flex-col items-center rounded-2xl border p-3 text-center transition-all duration-200 cursor-pointer',
                      active
                        ? 'border-cyan-500 bg-gradient-to-b from-cyan-50/90 via-white to-white shadow-[0_4px_16px_rgba(6,182,212,0.16)] ring-2 ring-cyan-400/40'
                        : 'border-slate-200/80 bg-white/70 hover:border-cyan-300/70 hover:bg-white hover:shadow-xs',
                    )}
                  >
                    {/* Active Check Indicator */}
                    {active && (
                      <span className="absolute top-1.5 right-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-cyan-500 text-[10px] text-white shadow-xs">
                        ✓
                      </span>
                    )}

                    <span
                      className={cn(
                        'mb-1.5 flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold transition-transform duration-200 group-hover:scale-105',
                        active
                          ? 'bg-gradient-to-tr from-[#1E4D38] to-cyan-600 text-white shadow-sm shadow-cyan-600/30 ring-2 ring-white'
                          : 'bg-slate-100 text-slate-700 group-hover:bg-cyan-50 group-hover:text-cyan-800',
                      )}
                    >
                      {member.initial}
                    </span>
                    <span
                      className={cn(
                        'block w-full truncate text-xs font-semibold transition-colors',
                        active ? 'text-slate-900' : 'text-slate-700 group-hover:text-cyan-900',
                      )}
                    >
                      {member.name}
                    </span>
                    <span className="mt-0.5 text-[10px] text-slate-600">
                      {member.role === 'admin' ? 'Quản trị' : 'Thành viên'}
                    </span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* PIN Input */}
          <div className="mb-5">
            <div className="mb-2 flex items-center justify-between">
              <label className="text-xs font-semibold tracking-wider text-slate-700 uppercase">
                Mã PIN bảo mật
              </label>
              <span className="text-[11px] text-slate-600">4 chữ số</span>
            </div>

            <div className="relative">
              <input
                type="password"
                inputMode="numeric"
                maxLength={4}
                placeholder="••••"
                value={pin}
                onChange={(e) => setPin(e.target.value.replace(/\D/g, '').slice(0, 4))}
                className="w-full rounded-2xl border border-slate-200/90 bg-white/90 py-3.5 px-4 text-center text-2xl font-bold tracking-[0.5em] text-slate-900 placeholder:tracking-normal placeholder:text-slate-300 outline-none transition-all focus:border-cyan-500 focus:bg-white focus:ring-4 focus:ring-cyan-500/15 shadow-inner"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') void enter()
                }}
              />
            </div>

            {/* Visual 4-dot indicator for entered digits */}
            <div className="mt-2.5 flex justify-center gap-2.5">
              {[0, 1, 2, 3].map((idx) => {
                const filled = pin.length > idx
                return (
                  <div
                    key={idx}
                    className={cn(
                      'h-1.5 rounded-full transition-all duration-300',
                      filled
                        ? 'w-7 bg-gradient-to-r from-cyan-500 to-teal-400 shadow-[0_0_6px_rgba(6,182,212,0.6)]'
                        : 'w-5 bg-slate-200/90',
                    )}
                  />
                )
              })}
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="button"
            className="group relative flex w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-[#1E4D38] via-[#235841] to-[#1E4D38] py-3.5 px-4 text-sm font-bold text-white shadow-lg shadow-[#1E4D38]/25 transition-all duration-200 hover:shadow-xl hover:shadow-cyan-600/20 active:scale-[0.99] disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            onClick={() => void enter()}
            disabled={homeLoading || !members.length || submitting}
          >
            {submitting ? (
              <span className="flex items-center gap-2">
                <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                <span>Đang đăng nhập…</span>
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <span>Đăng nhập vào không gian sống</span>
                <span className="transition-transform duration-200 group-hover:translate-x-1">→</span>
              </span>
            )}
          </button>

          {/* Footer Security Badge */}
          <div className="mt-5 flex items-center justify-between border-t border-slate-200/70 pt-4 text-[11px] text-slate-600">
            <span className="flex items-center gap-1.5">
              <ShieldLockIcon className="h-3.5 w-3.5 text-cyan-600" />
              <span>Xác thực an toàn đa lớp</span>
            </span>
            <span className="font-mono text-[10px] text-slate-600">HomeMind OS</span>
          </div>
        </div>
      </div>
    </div>
  )
}

