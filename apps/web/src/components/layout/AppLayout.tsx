import { useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  BellIcon,
  LogoIcon,
  NavCameraIcon,
  NavDeviceIcon,
  NavEnergyIcon,
  NavHomeIcon,
  NavRoomIcon,
  NavSceneIcon,
  NavSettingIcon,
  UserIcon,
} from '@/assets/icons/HomemateIcons'
import { VoiceDock } from '@/components/homemind/VoiceDock'
import { ROUTES } from '@/config/routes'
import { useSession } from '@/context/SessionContext'
import { cn } from '@/utils/cn'

export function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { session, logout } = useSession()
  const [profileMenuOpen, setProfileMenuOpen] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const navItems = [
    { to: ROUTES.dashboard, label: 'Trang chủ', icon: NavHomeIcon },
    { to: ROUTES.room, label: 'Phòng', icon: NavRoomIcon },
    { to: ROUTES.energy, label: 'Điện năng', icon: NavEnergyIcon },
    { to: ROUTES.devices, label: 'Thiết bị', icon: NavDeviceIcon },
    { to: ROUTES.camera, label: 'Camera', icon: NavCameraIcon },
    { to: ROUTES.scenes, label: 'Kịch bản', icon: NavSceneIcon },
    { to: ROUTES.schedules, label: 'Lịch tự động', icon: NavSceneIcon },
    { to: ROUTES.settings, label: 'Cài đặt', icon: NavSettingIcon },
  ]

  const isRoomScreen = location.pathname.startsWith(ROUTES.room)

  return (
    <div className="flex min-h-screen w-full justify-center bg-[#E2E8E0] font-sans text-[#1C2721] antialiased">
      <div className="flex h-screen w-full max-w-[1180px] overflow-hidden bg-[#F4F6F3] shadow-[0_0_60px_rgba(0,0,0,0.06)]">
      {/* Mobile Drawer Backdrop */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 backdrop-blur-xs md:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Left Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-[200px] flex-col border-r border-[#E6EBE3] bg-[#FBFDFA] transition-transform duration-300 md:static md:translate-x-0',
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        {/* Brand Logo */}
        <div className="flex items-center gap-2.5 px-4 pt-4 pb-3">
          <LogoIcon className="h-8 w-8 shrink-0" />
          <span className="font-display text-lg font-bold tracking-tight text-[#1E4D38]">
            HomeMate
          </span>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 space-y-0.5 overflow-y-auto px-2.5 py-1">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive =
              location.pathname === item.to ||
              (item.to === ROUTES.scenes &&
                location.pathname === ROUTES.scenarios)
            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => setMobileMenuOpen(false)}
                className={cn(
                  'group flex items-center gap-2.5 rounded-xl px-3 py-2 text-[13px] font-medium transition-colors',
                  isActive
                    ? 'bg-[#E2EFE5] font-semibold text-[#1E4D38] shadow-xs'
                    : 'text-[#5A6860] hover:bg-[#EDF3EB] hover:text-[#1C2721]',
                )}
              >
                <Icon
                  className={cn(
                    'h-5 w-5 transition-colors',
                    isActive
                      ? 'text-[#1E4D38]'
                      : 'text-[#6B7C72] group-hover:text-[#1C2721]',
                  )}
                />
                <span>{item.label}</span>
              </NavLink>
            )
          })}
        </nav>

        {/* Sidebar Footer Artwork & User Profile */}
        <div className="relative mt-auto border-t border-[#E8EDE6]/80 pt-3 pr-3 pb-4 pl-3">
          {/* User Profile Card */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setProfileMenuOpen((prev) => !prev)}
              className="flex w-full items-center gap-3 rounded-xl p-2 text-left transition hover:bg-[#EDF3EB]"
            >
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[#E2EFE5] ring-2 ring-[#D5E5D8]">
                <UserIcon className="h-4.5 w-4.5 text-[#1E4D38]" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-[#1C2721]">
                  {session?.memberName || 'Minh'}
                </p>
                <p className="truncate text-xs text-[#718076]">
                  {session?.role === 'admin' ? 'Quản trị viên' : 'Thành viên'}
                </p>
              </div>
              <svg
                className={cn(
                  'h-4 w-4 text-[#718076] transition-transform',
                  profileMenuOpen && 'rotate-180',
                )}
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>

            {/* Profile Dropdown */}
            {profileMenuOpen && (
              <div className="absolute right-0 bottom-full left-0 mb-2 rounded-xl border border-[#E6EBE3] bg-white p-1.5 shadow-lg">
                <button
                  type="button"
                  onClick={() => {
                    setProfileMenuOpen(false)
                    navigate(ROUTES.settings)
                  }}
                  className="flex w-full items-center rounded-lg px-3 py-2 text-xs font-medium text-[#1C2721] hover:bg-[#F4F6F3]"
                >
                  Cài đặt tài khoản
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setProfileMenuOpen(false)
                    navigate(ROUTES.voiceAgent)
                  }}
                  className="flex w-full items-center rounded-lg px-3 py-2 text-xs font-medium text-[#1E4D38] hover:bg-[#E2EFE5]"
                >
                  Mở Voice Agent
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setProfileMenuOpen(false)
                    void logout().then(() =>
                      navigate(ROUTES.login, { replace: true }),
                    )
                  }}
                  className="flex w-full items-center rounded-lg px-3 py-2 text-xs font-medium text-red-600 hover:bg-red-50"
                >
                  Đăng xuất
                </button>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Header */}
        <header className="relative z-20 flex shrink-0 items-center gap-2 border-b border-[#E8EDE6]/60 bg-[#F4F6F3] px-3 py-2 md:gap-3 md:px-4">
          <button
            type="button"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[#E6EBE3] bg-white text-[#5A6860] md:hidden"
            onClick={() => setMobileMenuOpen(true)}
            aria-label="Open menu"
          >
            <svg
              className="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          {isRoomScreen ? (
            <button
              type="button"
              onClick={() => navigate(ROUTES.dashboard)}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white text-[#5A6860] shadow-xs transition hover:bg-[#E2EFE5] hover:text-[#1E4D38] md:hidden"
              aria-label="Back"
            >
              <svg
                className="h-4 w-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
              >
                <path d="M19 12H5M12 19l-7-7 7-7" />
              </svg>
            </button>
          ) : null}

          <VoiceDock variant="header" />

          <div className="flex shrink-0 items-center gap-2">
            {/* Notification Bell with Badge */}
            <div className="relative">
              <button
                type="button"
                className="flex h-9 w-9 items-center justify-center rounded-full border border-[#E4E9E1] bg-white text-[#5A6860] shadow-xs transition hover:bg-[#F2F6F0] hover:text-[#1C2721]"
                aria-label="Notifications"
                onClick={() => navigate(ROUTES.camera)}
              >
                <BellIcon className="h-4 w-4" />
              </button>
              <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white shadow-xs">
                1
              </span>
            </div>

            {/* Quick Add Button */}
            <button
              type="button"
              className="flex h-9 w-9 items-center justify-center rounded-full bg-[#1E4D38] text-white shadow-sm transition hover:bg-[#153828]"
              title="Thêm thiết bị / kịch bản mới"
              onClick={() => navigate(ROUTES.devices)}
              aria-label="Add"
            >
              <svg
                className="h-5 w-5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
              >
                <path d="M12 5v14M5 12h14" />
              </svg>
            </button>
          </div>
        </header>

        {/* Main content: no page-level scroll; screens manage internal overflow */}
        <main className="min-h-0 flex-1 overflow-hidden p-3 md:p-4">
          <Outlet />
        </main>
      </div>
      </div>
    </div>
  )
}
