import { useState } from 'react'
import {
  BellIcon,
  DoorIcon,
  MaximizeIcon,
  MotionIcon,
  ShieldCheckIcon,
  Volume2Icon,
  VolumeXIcon,
} from '@/assets/icons/HomemateIcons'
import {
  CameraIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  MicIcon,
} from '@/assets/icons/HomeMindIcons'
import { TabletScreen } from '@/components/layout/TabletScreen'
import { useToast } from '@/context/ToastContext'

export function CameraScreen() {
  const { showToast } = useToast()
  const [selectedCam, setSelectedCam] = useState(3)
  const [isMuted, setIsMuted] = useState(true)
  const [isTalking, setIsTalking] = useState(false)

  const cameraFeeds = [
    {
      id: 'garden',
      name: 'Sân vườn',
      src: '/assets/images/camera_garden.png',
      thumb: '/assets/images/camera_garden.png',
      status: 'LIVE',
    },
    {
      id: 'living',
      name: 'Phòng khách',
      src: '/assets/images/room_living.png',
      thumb: '/assets/images/cam_living.png',
      status: 'LIVE',
    },
    {
      id: 'gate',
      name: 'Cổng trước',
      src: '/assets/images/cam_gate.png',
      thumb: '/assets/images/cam_gate.png',
      status: 'LIVE',
    },
    {
      id: 'garage',
      name: 'Nhà xe',
      src: '/assets/images/cam_garage.png',
      thumb: '/assets/images/cam_garage.png',
      status: 'LIVE',
    },
  ]

  const recentEvents = [
    {
      id: 1,
      type: 'motion',
      title: 'Phát hiện chuyển động',
      location: 'Sân vườn',
      time: '18:45',
      icon: MotionIcon,
      thumb: '/assets/images/ev_garden.png',
    },
    {
      id: 2,
      type: 'door',
      title: 'Cửa mở',
      location: 'Cổng trước',
      time: '18:32',
      icon: DoorIcon,
      thumb: '/assets/images/ev_gate.png',
    },
    {
      id: 3,
      type: 'motion',
      title: 'Phát hiện chuyển động',
      location: 'Phòng khách',
      time: '17:18',
      icon: MotionIcon,
      thumb: '/assets/images/ev_living.png',
    },
    {
      id: 4,
      type: 'bell',
      title: 'Chuông cửa',
      location: 'Cổng trước',
      time: '16:05',
      icon: BellIcon,
      thumb: '/assets/images/ev_doorbell.png',
    },
    {
      id: 5,
      type: 'motion',
      title: 'Phát hiện chuyển động',
      location: 'Nhà xe',
      time: '15:47',
      icon: MotionIcon,
      thumb: '/assets/images/ev_garage.png',
    },
  ]

  const currentCamera = cameraFeeds[selectedCam]

  const handleSnapshot = () => {
    showToast(`Đã lưu ảnh chụp nhanh từ ${currentCamera.name}`, 'success')
  }

  const handleToggleTalk = () => {
    const next = !isTalking
    setIsTalking(next)
    showToast(
      next
        ? `Đang đàm thoại hai chiều tới ${currentCamera.name}…`
        : 'Đã dừng đàm thoại',
      'info',
    )
  }

  return (
    <TabletScreen>
      <div className="grid h-full min-h-0 grid-cols-1 gap-2.5 lg:grid-cols-12">
        <div className="flex min-h-0 flex-col lg:col-span-7">
          <div className="flex h-full min-h-0 flex-col rounded-2xl border border-[#E6ECE3] bg-white p-3 shadow-sm">
            <div className="mb-2 shrink-0">
              <h2 className="font-display text-xs font-bold text-[#1C2721]">
                Camera
              </h2>
              <p className="text-[10px] text-[#718076]">
                Giám sát ngôi nhà của bạn mọi lúc, mọi nơi.
              </p>
            </div>

            <div className="relative min-h-0 flex-1 overflow-hidden rounded-xl bg-black">
              <img
                src={currentCamera.src}
                alt={currentCamera.name}
                className="h-full w-full object-cover"
              />
              <div className="absolute top-2 right-2 left-2 flex items-center justify-between">
                <div className="flex items-center gap-1 rounded-md bg-[#22C55E]/90 px-2 py-0.5 text-[9px] font-bold text-white">
                  <span className="h-1.5 w-1.5 animate-ping rounded-full bg-white" />
                  LIVE
                </div>
                <div className="flex items-center gap-1 rounded-lg bg-black/50 px-2 py-0.5 text-[10px] font-semibold text-white backdrop-blur-xs">
                  <span>{currentCamera.name}</span>
                  <ChevronDownIcon className="h-3 w-3" />
                </div>
              </div>
              <div className="absolute right-2 bottom-2 left-2 flex items-center justify-end gap-1.5 rounded-lg bg-black/40 px-3 py-1.5 text-white backdrop-blur-xs">
                <button
                  type="button"
                  onClick={() => setIsMuted((m) => !m)}
                  className="flex h-6 w-6 items-center justify-center rounded-md transition-colors hover:bg-white/20"
                  title={isMuted ? 'Bật âm thanh' : 'Tắt âm thanh'}
                >
                  {isMuted ? (
                    <VolumeXIcon className="h-3.5 w-3.5" />
                  ) : (
                    <Volume2Icon className="h-3.5 w-3.5" />
                  )}
                </button>
                <button
                  type="button"
                  onClick={handleSnapshot}
                  className="flex h-6 w-6 items-center justify-center rounded-md transition-colors hover:bg-white/20"
                  title="Chụp ảnh màn hình"
                >
                  <CameraIcon className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={handleToggleTalk}
                  className={`flex h-6 w-6 items-center justify-center rounded-md transition-colors ${
                    isTalking ? 'bg-red-500 text-white' : 'hover:bg-white/20'
                  }`}
                  title="Đàm thoại hai chiều"
                >
                  <MicIcon className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => showToast('Đã mở toàn màn hình', 'info')}
                  className="flex h-6 w-6 items-center justify-center rounded-md transition-colors hover:bg-white/20"
                  title="Toàn màn hình"
                >
                  <MaximizeIcon className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>

            <div className="mt-2 grid shrink-0 grid-cols-2 gap-1.5 sm:grid-cols-4">
              {cameraFeeds.map((cam, idx) =>
                idx === selectedCam ? null : (
                <button
                  key={cam.id}
                  type="button"
                  onClick={() => setSelectedCam(idx)}
                  className={`relative overflow-hidden rounded-xl border-2 text-left transition ${
                    selectedCam === idx
                      ? 'border-[#1E4D38]'
                      : 'border-transparent hover:border-[#2D6A4F]'
                  }`}
                >
                  <div className="relative aspect-4/3 w-full bg-black">
                    <img
                      src={cam.thumb}
                      alt={cam.name}
                      className="h-full w-full object-cover"
                    />
                    <div className="absolute top-1 left-1 rounded-sm bg-[#22C55E]/90 px-1 py-px text-[8px] font-bold text-white">
                      LIVE
                    </div>
                  </div>
                  <div className="flex items-center justify-between bg-[#F8FAF7] p-1.5">
                    <span className="truncate text-[10px] font-bold text-[#1C2721]">
                      {cam.name}
                    </span>
                    <span className="h-1.5 w-1.5 rounded-full bg-[#22C55E]" />
                  </div>
                </button>
                ),
              )}
            </div>
          </div>
        </div>

        <div className="flex min-h-0 flex-col gap-2 lg:col-span-5">
          <div className="flex min-h-0 flex-1 flex-col rounded-2xl border border-[#E6ECE3] bg-white p-3 shadow-sm">
            <div className="mb-2 flex shrink-0 items-center justify-between">
              <h3 className="font-display text-xs font-bold text-[#1C2721]">
                Sự kiện gần đây
              </h3>
              <button
                type="button"
                className="inline-flex items-center gap-0.5 text-[10px] font-semibold text-[#1E4D38] hover:underline"
              >
                <span>Xem tất cả</span>
                <ChevronRightIcon className="h-2.5 w-2.5" />
              </button>
            </div>
            <div className="min-h-0 flex-1 space-y-1.5 overflow-y-auto text-[10px]">
              {recentEvents.map((ev) => {
                const Icon = ev.icon
                return (
                  <div
                    key={ev.id}
                    className="flex items-center justify-between rounded-xl bg-[#F8FAF7] p-2 transition hover:bg-[#EDF3EB]"
                  >
                    <div className="flex min-w-0 items-center gap-2">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-[#E2EFE5] text-[#1E4D38]">
                        <Icon className="h-3.5 w-3.5" />
                      </span>
                      <div className="min-w-0">
                        <p className="truncate font-bold text-[#1C2721]">
                          {ev.title}
                        </p>
                        <p className="truncate text-[9px] text-[#718076]">
                          {ev.location}
                        </p>
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <span className="text-[9px] font-semibold text-[#88968E]">
                        {ev.time}
                      </span>
                      <div className="h-7 w-10 overflow-hidden rounded-md bg-black">
                        <img
                          src={ev.thumb}
                          alt=""
                          className="h-full w-full object-cover"
                        />
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          <div className="relative shrink-0 overflow-hidden rounded-2xl border border-[#D5E5D8] bg-[#EAF5ED] p-3 shadow-sm">
            <div className="relative z-10 flex items-center gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#2D6A4F] text-white shadow-md">
                <ShieldCheckIcon className="h-5 w-5" />
              </div>
              <div>
                <h4 className="font-display text-xs font-bold text-[#1E4D38]">
                  Ngôi nhà của bạn luôn được bảo vệ
                </h4>
                <p className="text-[10px] text-[#3B4D42]">
                  Hệ thống đang hoạt động tốt.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </TabletScreen>
  )
}
