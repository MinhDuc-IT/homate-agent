import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { UserIcon } from '@/assets/icons/HomemateIcons'
import { TabletScreen } from '@/components/layout/TabletScreen'
import { useSession } from '@/context/SessionContext'
import { useToast } from '@/context/ToastContext'
import { MockPanel } from '@/screens/MockPanel'
import { HitlSettingsPanel } from '@/screens/HitlSettingsPanel'
import {
  createUser,
  deleteUser,
  fetchMyProfile,
  fetchUsers,
  updateUser,
  type UserProfile,
} from '@/api/users'

function Toggle({
  on,
  onToggle,
}: {
  on: boolean
  onToggle: () => void
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={`relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 border-transparent transition-colors ${
        on ? 'bg-[#2D6A4F]' : 'bg-gray-300'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition ${
          on ? 'translate-x-4' : 'translate-x-0'
        }`}
      />
    </button>
  )
}

export function SettingScreen() {
  const { showToast } = useToast()
  const { session, isAdmin, members, homeLoading, homeError, reloadHome } = useSession()
  const [searchParams, setSearchParams] = useSearchParams()
  const requestedTab = searchParams.get('tab')
  const activeTab = requestedTab === 'mock' && isAdmin
    ? 'mock'
    : requestedTab === 'hitl'
      ? 'hitl'
      : 'general'

  const [notifications, setNotifications] = useState({
    push: true,
    email: true,
    security: true,
    weeklyReport: false,
  })

  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [managedUsers, setManagedUsers] = useState<UserProfile[]>([])
  const [editingUser, setEditingUser] = useState<UserProfile | null>(null)
  const [showUserForm, setShowUserForm] = useState(false)
  const [userForm, setUserForm] = useState({ name: '', email: '', phone: '', role: 'member' as 'admin' | 'member', pin: '' })

  const loadUsers = async () => {
    const mine = await fetchMyProfile()
    setProfile(mine)
    if (isAdmin) setManagedUsers(await fetchUsers())
  }

  useEffect(() => {
    if (!session) return
    void loadUsers().catch((error: unknown) =>
      showToast(error instanceof Error ? error.message : 'Không tải được hồ sơ', 'error'),
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.memberId, isAdmin])

  const openCreateUser = () => {
    setEditingUser(null)
    setUserForm({ name: '', email: '', phone: '', role: 'member', pin: '' })
    setShowUserForm(true)
  }

  const openEditUser = (user: UserProfile) => {
    setEditingUser(user)
    setUserForm({ name: user.name, email: user.email ?? '', phone: user.phone ?? '', role: user.role, pin: '' })
    setShowUserForm(true)
  }

  const saveUser = async () => {
    try {
      const payload = { ...userForm, email: userForm.email || null, phone: userForm.phone || null }
      if (editingUser) {
        await updateUser(editingUser.id, { ...payload, pin: payload.pin || undefined })
      } else {
        if (!/^\d{4}$/.test(payload.pin)) throw new Error('PIN phải gồm đúng 4 chữ số')
        await createUser({ ...payload, pin: payload.pin })
      }
      await loadUsers()
      await reloadHome()
      setShowUserForm(false)
      showToast(editingUser ? 'Đã cập nhật thành viên' : 'Đã thêm thành viên', 'success')
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Không lưu được thành viên', 'error')
    }
  }

  const removeUser = async (user: UserProfile) => {
    if (!window.confirm(`Xóa thành viên “${user.name}”?`)) return
    try {
      await deleteUser(user.id)
      await loadUsers()
      await reloadHome()
      showToast('Đã xóa thành viên', 'success')
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Không xóa được thành viên', 'error')
    }
  }

  const toggleNotif = (key: keyof typeof notifications, name: string) => {
    setNotifications((prev) => {
      const next = !prev[key]
      showToast(`${name}: ${next ? 'Đã bật' : 'Đã tắt'}`, 'info')
      return { ...prev, [key]: next }
    })
  }

  const handleBackup = () => {
    showToast('Đang tạo bản sao lưu cấu hình...', 'info')
    setTimeout(() => showToast('Đã sao lưu thành công!', 'success'), 800)
  }

  const handleCheckUpdate = () => {
    showToast('Ứng dụng đang ở phiên bản mới nhất (v2.1.0)', 'success')
  }

  const notifItems = [
    {
      key: 'push' as const,
      title: 'Thông báo đẩy',
      desc: 'Nhận thông báo trên thiết bị di động',
    },
    {
      key: 'email' as const,
      title: 'Thông báo email',
      desc: 'Nhận thông báo qua email',
    },
    {
      key: 'security' as const,
      title: 'Cảnh báo an ninh',
      desc: 'Báo động, phát hiện chuyển động...',
    },
    {
      key: 'weeklyReport' as const,
      title: 'Báo cáo định kỳ',
      desc: 'Nhận báo cáo điện năng mỗi tuần',
    },
  ]
  const displayedMembers = isAdmin && managedUsers.length > 0 ? managedUsers : members

  return (
    <TabletScreen>
      <div className="mb-2 flex shrink-0 gap-1 rounded-xl border border-[#E6ECE3] bg-white p-1 shadow-sm">
        <button
          type="button"
          onClick={() => setSearchParams({})}
          className={`rounded-lg px-3 py-1.5 text-[10px] font-bold transition-colors ${
            activeTab === 'general'
              ? 'bg-[#1E4D38] text-white'
              : 'text-[#5A6860] hover:bg-[#F0F5EF]'
          }`}
        >
          Cài đặt chung
        </button>
        <button
          type="button"
          onClick={() => setSearchParams({ tab: 'hitl' })}
          className={`rounded-lg px-3 py-1.5 text-[10px] font-bold transition-colors ${
            activeTab === 'hitl'
              ? 'bg-[#1E4D38] text-white'
              : 'text-[#5A6860] hover:bg-[#F0F5EF]'
          }`}
        >
          Xác nhận HITL
        </button>
        {isAdmin && (
          <button
            type="button"
            onClick={() => setSearchParams({ tab: 'mock' })}
            className={`rounded-lg px-3 py-1.5 text-[10px] font-bold transition-colors ${
              activeTab === 'mock'
                ? 'bg-[#1E4D38] text-white'
                : 'text-[#5A6860] hover:bg-[#F0F5EF]'
            }`}
          >
            Dữ liệu mô phỏng
          </button>
        )}
      </div>

      {activeTab === 'mock' ? (
        <div className="min-h-0 flex-1 overflow-y-auto pr-1">
          <MockPanel />
        </div>
      ) : activeTab === 'hitl' ? (
        <div className="min-h-0 flex-1 overflow-y-auto pr-1">
          <HitlSettingsPanel />
        </div>
      ) : (
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-2 lg:grid-cols-2">
        <div className="flex min-h-0 flex-col gap-2 overflow-y-auto pr-0.5 lg:pr-1">
          <div className="shrink-0 rounded-2xl border border-[#E6ECE3] bg-white p-3 shadow-sm">
            <h3 className="font-display text-xs font-bold text-[#1C2721]">
              Hồ sơ của tôi
            </h3>
            <div className="mt-2 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[#E2EFE5] ring-2 ring-[#D5E5D8]">
                  <UserIcon className="h-5 w-5 text-[#1E4D38]" />
                </span>
                <div>
                  <div className="flex items-center gap-1.5">
                    <p className="font-display text-sm font-bold text-[#1C2721]">
                      {profile?.name ?? session?.memberName ?? '—'}
                    </p>
                    <span className="rounded-md bg-[#E8F5EB] px-1.5 py-px text-[8px] font-bold text-[#2E7D32]">
                      {(profile?.role ?? session?.role) === 'admin' ? 'Quản trị viên' : 'Thành viên'}
                    </span>
                  </div>
                  <p className="text-[10px] text-[#5A6860]">
                    {profile?.email || 'Chưa cập nhật email'}
                  </p>
                  <p className="text-[10px] text-[#88968E]">{profile?.phone || 'Chưa cập nhật số điện thoại'}</p>
                </div>
              </div>
              <span className="text-gray-400">›</span>
            </div>
          </div>

          <div className="shrink-0 rounded-2xl border border-[#E6ECE3] bg-white p-3 shadow-sm">
            <h3 className="font-display text-xs font-bold text-[#1C2721]">
              Thành viên ngôi nhà
            </h3>
            <div className="mt-2 space-y-1.5 text-[10px]">
              {homeLoading && (
                <p className="rounded-xl bg-[#F8FAF7] p-2 text-[#718076]">
                  Đang tải thành viên...
                </p>
              )}
              {!homeLoading && homeError && (
                <p className="rounded-xl bg-red-50 p-2 text-red-700">
                  Không tải được danh sách thành viên.
                </p>
              )}
              {!homeLoading && !homeError && members.length === 0 && (
                <p className="rounded-xl bg-[#F8FAF7] p-2 text-[#718076]">
                  Chưa có thành viên.
                </p>
              )}
              {displayedMembers.map((member) => (
                <div
                  key={member.id}
                  className="flex items-center justify-between rounded-xl bg-[#F8FAF7] p-2"
                >
                  <div className="flex items-center gap-2">
                    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#E2EFE5]">
                      <span className="text-[10px] font-bold text-[#1E4D38]">
                        {member.initial || member.name.charAt(0).toUpperCase()}
                      </span>
                    </span>
                    <div>
                      <p className="font-bold text-[#1C2721]">{member.name}</p>
                      <p className="text-[9px] text-[#718076]">
                        {member.role === 'admin' ? 'Quản trị viên' : 'Thành viên'}
                      </p>
                    </div>
                  </div>
                  {isAdmin && 'email' in member ? (
                    <div className="flex items-center gap-1">
                      <button type="button" onClick={() => openEditUser(member as UserProfile)} className="rounded-md border border-[#D5E5D8] bg-white px-1.5 py-0.5 text-[9px] font-bold text-[#1E4D38] hover:bg-[#EAF5ED]">Sửa</button>
                      {member.id !== session?.memberId && (
                        <button type="button" onClick={() => void removeUser(member as UserProfile)} className="rounded-md border border-red-200 bg-white px-1.5 py-0.5 text-[9px] font-bold text-red-600 hover:bg-red-50">Xóa</button>
                      )}
                    </div>
                  ) : null}
                </div>
              ))}
              {isAdmin && (
                <>
                  {showUserForm && (
                    <div className="grid grid-cols-2 gap-1.5 rounded-xl border border-[#D5E5D8] bg-white p-2">
                      <input value={userForm.name} onChange={(e) => setUserForm((f) => ({ ...f, name: e.target.value }))} placeholder="Tên thành viên" className="rounded-md border border-[#E0E7DE] px-2 py-1 outline-none" />
                      <select value={userForm.role} onChange={(e) => setUserForm((f) => ({ ...f, role: e.target.value as 'admin' | 'member' }))} disabled={editingUser?.id === session?.memberId} className="rounded-md border border-[#E0E7DE] px-2 py-1 outline-none disabled:opacity-60">
                        <option value="member">Thành viên</option>
                        <option value="admin">Quản trị viên</option>
                      </select>
                      <input type="email" value={userForm.email} onChange={(e) => setUserForm((f) => ({ ...f, email: e.target.value }))} placeholder="Email" className="rounded-md border border-[#E0E7DE] px-2 py-1 outline-none" />
                      <input value={userForm.phone} onChange={(e) => setUserForm((f) => ({ ...f, phone: e.target.value }))} placeholder="Số điện thoại" className="rounded-md border border-[#E0E7DE] px-2 py-1 outline-none" />
                      <input inputMode="numeric" maxLength={4} value={userForm.pin} onChange={(e) => setUserForm((f) => ({ ...f, pin: e.target.value.replace(/\D/g, '') }))} placeholder={editingUser ? 'PIN mới (để trống nếu giữ)' : 'PIN 4 số'} className="col-span-2 rounded-md border border-[#E0E7DE] px-2 py-1 outline-none" />
                      <div className="col-span-2 flex justify-end gap-1">
                        <button type="button" onClick={() => setShowUserForm(false)} className="rounded-md px-2 py-1 font-semibold text-[#718076]">Hủy</button>
                        <button type="button" disabled={!userForm.name.trim()} onClick={() => void saveUser()} className="rounded-md bg-[#1E4D38] px-2 py-1 font-bold text-white disabled:opacity-50">Lưu</button>
                      </div>
                    </div>
                  )}
                  {!showUserForm && (
                    <button
                      type="button"
                      onClick={openCreateUser}
                      className="flex w-full items-center justify-center gap-1 rounded-xl border border-dashed border-[#2D6A4F] py-2 text-[10px] font-bold text-[#1E4D38] hover:bg-[#EAF5ED]"
                    >
                      <span>+</span>
                      <span>Thêm thành viên</span>
                    </button>
                  )}
                </>
              )}
            </div>
          </div>

          {/* <div className="shrink-0 rounded-2xl border border-[#E6ECE3] bg-white p-3 shadow-sm">
            <h3 className="font-display text-xs font-bold text-[#1C2721]">
              Dịch vụ &amp; thiết bị kết nối
            </h3>
            <div className="mt-2 divide-y divide-[#F0F4EE] text-[10px]">
              {[
                { icon: '🔵', name: 'Google Assistant', status: 'Đã kết nối ›' },
                { icon: '🔷', name: 'Amazon Alexa', status: 'Đã kết nối ›' },
                { icon: '🏠', name: 'Apple HomeKit', status: 'Đã kết nối ›' },
                { icon: '🔴', name: 'Zigbee Gateway', status: 'Kết nối ổn định ›' },
                { icon: '⚙', name: 'Quản lý thiết bị', status: '32 thiết bị ›' },
              ].map((svc) => (
                <div
                  key={svc.name}
                  className="flex items-center justify-between py-2"
                >
                  <span>
                    {svc.icon} {svc.name}
                  </span>
                  <span className="font-semibold text-[#22C55E]">{svc.status}</span>
                </div>
              ))}
            </div>
          </div> */}

          <div className="shrink-0 rounded-2xl border border-[#E6ECE3] bg-white p-3 shadow-sm">
            <h3 className="font-display text-xs font-bold text-[#1C2721]">
              Sao lưu &amp; khôi phục
            </h3>
            <p className="mt-0.5 text-[10px] text-[#718076]">
              Sao lưu cài đặt và khôi phục khi cần thiết.
            </p>
            <button
              type="button"
              onClick={handleBackup}
              className="mt-2 flex w-full items-center justify-center gap-1.5 rounded-full border border-[#D5E5D8] bg-[#F8FAF7] py-1.5 text-[10px] font-bold text-[#1E4D38] hover:bg-[#E2EFE5]"
            >
              <span>↑</span>
              <span>Sao lưu ngay</span>
            </button>
          </div>
        </div>

        <div className="flex min-h-0 flex-col gap-2 overflow-y-auto pl-0.5 lg:pl-1">
          <div className="shrink-0 rounded-2xl border border-[#E6ECE3] bg-white p-3 shadow-sm">
            <h3 className="font-display text-xs font-bold text-[#1C2721]">
              Tùy chọn thông báo
            </h3>
            <div className="mt-2 space-y-2 text-[10px]">
              {notifItems.map((item) => (
                <div key={item.key} className="flex items-center justify-between">
                  <div>
                    <p className="font-bold text-[#1C2721]">{item.title}</p>
                    <p className="text-[9px] text-[#718076]">{item.desc}</p>
                  </div>
                  <Toggle
                    on={notifications[item.key]}
                    onToggle={() => toggleNotif(item.key, item.title)}
                  />
                </div>
              ))}
            </div>
          </div>

          <div className="shrink-0 rounded-2xl border border-[#E6ECE3] bg-white p-3 shadow-sm">
            <h3 className="font-display text-xs font-bold text-[#1C2721]">
              Quyền riêng tư &amp; bảo mật
            </h3>
            <div className="mt-2 divide-y divide-[#F0F4EE] text-[10px]">
              {[
                { label: '🔑 Đổi mật khẩu', action: () => showToast('Đổi mật khẩu tài khoản', 'info'), right: '›' },
                { label: '🛡 Đăng nhập 2 lớp', action: () => showToast('Cài đặt xác thực 2 lớp', 'info'), right: 'Đang bật ›', green: true },
                { label: '💻 Quản lý thiết bị đăng nhập', action: () => showToast('3 thiết bị đang đăng nhập', 'info'), right: '3 thiết bị ›' },
                { label: '⏱ Lịch sử hoạt động', action: () => showToast('Đang mở nhật ký lệnh...', 'info'), right: '›' },
              ].map((row) => (
                <div
                  key={row.label}
                  className="flex cursor-pointer items-center justify-between py-2 hover:text-[#1E4D38]"
                  onClick={row.action}
                >
                  <span>{row.label}</span>
                  <span className={row.green ? 'font-semibold text-[#22C55E]' : 'text-[#718076]'}>
                    {row.right}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="relative shrink-0 overflow-hidden rounded-2xl border border-[#E6ECE3] bg-white p-3 shadow-sm">
            <div className="relative z-10">
              <h3 className="font-display text-xs font-bold text-[#1C2721]">
                Thông tin ứng dụng
              </h3>
              <p className="mt-0.5 text-[10px] text-[#718076]">
                Phiên bản 2.1.0 · Cập nhật: 18/05/2024
              </p>
              <button
                type="button"
                onClick={handleCheckUpdate}
                className="mt-2 flex items-center gap-1.5 rounded-full border border-[#D5E5D8] bg-[#F8FAF7] px-3 py-1.5 text-[10px] font-bold text-[#1E4D38] hover:bg-[#E2EFE5]"
              >
                <span>↑</span>
                <span>Kiểm tra cập nhật</span>
              </button>
            </div>
          </div>
        </div>
      </div>
      )}
    </TabletScreen>
  )
}
