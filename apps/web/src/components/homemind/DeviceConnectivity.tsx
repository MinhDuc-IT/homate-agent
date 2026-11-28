import { useDevices } from '@/context/DevicesContext'

export function DeviceConnectivity({ deviceId }: { deviceId: string }) {
  const { connectivity } = useDevices()
  const connection = connectivity[deviceId]
  if (!connection || connection.adapter === 'simulator') return null
  const label = { online: 'Đã kết nối', offline: 'Mất kết nối', unknown: 'Chưa rõ kết nối' }[connection.status]
  const seen = connection.last_seen_at ? new Date(connection.last_seen_at * 1000).toLocaleString('vi-VN') : 'Chưa có'
  return <span role="status" title={`Lần cuối liên lạc: ${seen}`} className={`block text-xs ${connection.status === 'online' ? 'text-green-700' : 'text-amber-700'}`}>
    {label}{connection.status !== 'online' && <span className="block">Lần cuối: {seen}. Trạng thái hiển thị là lần ghi nhận gần nhất.</span>}
  </span>
}
