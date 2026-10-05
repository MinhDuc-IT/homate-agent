import { Link } from 'react-router-dom'

export function AiPending() {
  return <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 rounded-2xl bg-[#F8FAF7] p-8 text-center text-[#1E4D38]">
    <h1 className="text-xl font-semibold">Trợ lý HomeMate</h1>
    <p>Tính năng AI và điều khiển bằng giọng nói sẽ được tích hợp ở giai đoạn tiếp theo.</p>
    <Link to="/dashboard" className="rounded-full bg-[#1E4D38] px-5 py-2 text-white">Về trang chủ</Link>
  </div>
}
