import { UnityViewport } from '@/components/layout/UnityViewport'

export function House3DScreen() {
  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <header>
        <h1 className="text-xl font-semibold text-[#1E4D38]">Nhà 3D</h1>
        <p className="mt-1 text-sm text-[#66746A]">Đèn, rèm, TV, loa, camera và quạt hút bếp hiển thị theo trạng thái thiết bị. Chọn Bật âm thanh nếu muốn nghe nhạc từ loa.</p>
        <p className="mt-1 text-xs text-[#66746A]">Chọn phòng để chuyển nhanh góc nhìn. Kéo chuột để nhìn quanh, cuộn để phóng to hoặc thu nhỏ.</p>
      </header>
      <UnityViewport />
    </div>
  )
}
