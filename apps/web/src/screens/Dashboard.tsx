import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  LeafIcon,
  MoonIcon,
  NavRoomIcon,
  ShieldCheckIcon,
  SparklesIcon,
  SunIcon,
} from "@/assets/icons/HomemateIcons";
import { TabletScreen } from "@/components/layout/TabletScreen";
import { ROUTES } from "@/config/routes";
import { useDevices } from "@/context/DevicesContext";
import { useSession } from "@/context/SessionContext";
import { useToast } from "@/context/ToastContext";
import { useEnergy } from "@/hooks/useEnergy";
import { useSchedules } from "@/hooks/useSchedules";
import { isDeviceActive } from "@/utils/deviceStatus";

export function Dashboard() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { devices } = useDevices();
  const { rooms, homeLoading } = useSession();
  const { data: energy } = useEnergy("today");
  const { data: schedules } = useSchedules();
  const [selectedCameraIndex, setSelectedCameraIndex] = useState(3);
  const [appliedAiTip, setAppliedAiTip] = useState(false);

  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const seconds = time.getSeconds();
  const minutes = time.getMinutes();
  const hours = time.getHours();

  const secondAngle = seconds * 6;
  const minuteAngle = minutes * 6 + seconds * 0.1;
  const hourAngle = (hours % 12) * 30 + minutes * 0.5;

  const dayNames = [
    "Chủ Nhật",
    "Thứ Hai",
    "Thứ Ba",
    "Thứ Tư",
    "Thứ Năm",
    "Thứ Sáu",
    "Thứ Bảy",
  ];
  const formattedDate = `${dayNames[time.getDay()]}, ${time.getDate()} Tháng ${time.getMonth() + 1}, ${time.getFullYear()}`;

  const cameras = [
    {
      name: "Sân vườn",
      src: "/assets/images/camera_garden.png",
      thumb: "/assets/images/camera_garden.png",
    },
    {
      name: "Phòng khách",
      src: "/assets/images/room_living.png",
      thumb: "/assets/images/cam_living.png",
    },
    {
      name: "Cổng trước",
      src: "/assets/images/cam_gate.png",
      thumb: "/assets/images/cam_gate.png",
    },
    {
      name: "Nhà xe",
      src: "/assets/images/cam_garage.png",
      thumb: "/assets/images/cam_garage.png",
    },
  ];

  const activeDevicesCount = devices.filter((d) => isDeviceActive(d)).length;

  const roomCards = useMemo(
    () =>
      rooms.map((room) => {
        const roomDevices = devices.filter((d) => d.room === room.id);
        const activeInRoom = roomDevices.filter((d) =>
          isDeviceActive(d),
        ).length;
        return {
          id: room.id,
          label: room.label,
          deviceCount: roomDevices.length,
          activeInRoom,
        };
      }),
    [rooms, devices],
  );

  const primaryRoom = rooms.find((r) => r.id === "living") ?? rooms[0];
  const energyTotal = energy?.total_kwh ?? 0;
  const topEnergyDevices = (energy?.by_device ?? []).slice(0, 4).map((device) => ({
    label: device.name,
    pct: energyTotal > 0 ? Math.round(device.kwh / energyTotal * 100) : 0,
  }));

  const handleApplyAi = () => {
    setAppliedAiTip(true);
    showToast(
      "Đã tăng điều hòa phòng khách lên 25°C để tiết kiệm điện năng",
      "success",
    );
  };

  return (
    <TabletScreen>
      <div className="grid h-full min-h-0 grid-rows-[minmax(0,1fr)_minmax(0,1.05fr)_minmax(0,0.85fr)] gap-2.5">
        {/* Row 1: Hero + Schedule */}
        <div className="grid min-h-0 grid-cols-1 gap-2.5 lg:grid-cols-12">
          <div className="relative min-h-0 overflow-hidden rounded-2xl bg-[#1F2E26] shadow-sm lg:col-span-7">
            <div className="relative h-full min-h-[120px] w-full">
              <img
                src="/assets/images/house_hero.png"
                alt="Home Exterior"
                className="h-full w-full object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent" />
              <div className="absolute bottom-3 left-3 text-white">
                <div className="mb-1.5 flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#22C55E]/90 text-white shadow-md">
                    <ShieldCheckIcon className="h-4 w-4" />
                  </div>
                  <h2 className="font-display text-sm font-bold tracking-tight text-white">
                    Mọi thứ ổn định
                  </h2>
                </div>
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-white/90">
                  <span>🏠 {rooms.length} phòng</span>
                  <span>⏱ {activeDevicesCount} thiết bị đang bật</span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex min-h-0 flex-col justify-between overflow-hidden rounded-2xl border border-[#E6ECE3] bg-white p-2.5 sm:p-3 shadow-sm lg:col-span-5">
            <div className="min-h-0">
              <h3 className="mb-1.5 font-display text-xs font-bold text-[#1C2721]">
                Hôm nay
              </h3>
              <div className="grid grid-cols-1 items-center gap-2 sm:grid-cols-12">
                {/* Left: Clock + Date */}
                <div className="flex flex-col items-center justify-center sm:col-span-5">
                  <div className="relative flex h-[62px] w-[62px] shrink-0 items-center justify-center rounded-full border-2 border-[#E2EAE0] bg-[#FAFCF9] shadow-inner">
                    <div className="absolute top-0.5 text-[7px] font-bold text-[#88968E]">
                      12
                    </div>
                    <div className="absolute right-1 text-[7px] font-bold text-[#88968E]">
                      3
                    </div>
                    <div className="absolute bottom-0.5 text-[7px] font-bold text-[#88968E]">
                      6
                    </div>
                    <div className="absolute left-1 text-[7px] font-bold text-[#88968E]">
                      9
                    </div>
                    <div
                      className="absolute bottom-1/2 left-1/2 h-4 w-0.5 origin-bottom -translate-x-1/2 rounded-full bg-[#1C2721]"
                      style={{ transform: `rotate(${hourAngle}deg)` }}
                    />
                    <div
                      className="absolute bottom-1/2 left-1/2 h-5 w-0.5 origin-bottom -translate-x-1/2 rounded-full bg-[#2D6A4F]"
                      style={{ transform: `rotate(${minuteAngle}deg)` }}
                    />
                    <div
                      className="absolute bottom-1/2 left-1/2 h-6 w-px origin-bottom -translate-x-1/2 bg-red-500"
                      style={{ transform: `rotate(${secondAngle}deg)` }}
                    />
                    <div className="absolute h-1.5 w-1.5 rounded-full bg-[#1E4D38] ring-1 ring-white" />
                  </div>
                  <p className="mt-1 text-center text-[9.5px] font-medium leading-tight text-[#718076]">
                    {formattedDate}
                  </p>
                </div>

                {/* Right: Schedule List */}
                <div className="space-y-1.5 sm:col-span-7">
                  {schedules.slice(0, 2).map((schedule, index) => {
                    const Icon = index === 0 ? SunIcon : MoonIcon;
                    return <div key={schedule.id} className="flex items-center gap-2 rounded-xl border border-[#EEF3EC] bg-[#F8FAF7] p-1.5">
                      <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-[#E2EFE5] text-[#1E4D38]"><Icon className="h-3 w-3" /></div>
                      <div className="min-w-0 flex-1"><p className="text-[9px] font-bold text-[#88968E]">{schedule.next_run_at ? new Date(schedule.next_run_at).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" }) : "—"}</p><p className="truncate text-[11px] font-semibold text-[#1C2721]">{schedule.name}</p><p className="truncate text-[9px] text-[#88968E]">{schedule.scene_name ?? schedule.device_name}</p></div>
                    </div>;
                  })}
                  {schedules.length === 0 && <p className="py-4 text-center text-[10px] text-[#88968E]">Chưa có lịch sắp tới.</p>}
                </div>
              </div>
            </div>

            {/* Bottom Button */}
            <button
              type="button"
              onClick={() => navigate(ROUTES.schedules)}
              className="relative mt-1.5 flex w-full items-center justify-center rounded-xl border border-[#E6ECE3]/80 bg-[#F8FAF7] px-2.5 py-1 text-[11px] font-semibold text-[#1E4D38] transition-colors hover:bg-[#EAF2E8]"
            >
              <span>Xem lịch đầy đủ</span>
              <span className="absolute right-2.5 text-xs font-bold text-[#1E4D38]">
                ›
              </span>
            </button>
          </div>
        </div>

        {/* Row 2: Camera + Energy */}
        <div className="grid min-h-0 grid-cols-1 gap-2.5 lg:grid-cols-12">
          <div className="flex min-h-0 flex-col rounded-2xl border border-[#E6ECE3] bg-white p-3.5 shadow-sm lg:col-span-7">
            <div className="mb-2 flex shrink-0 items-center justify-between">
              <h3 className="font-display text-xs font-bold text-[#1C2721]">
                Camera
              </h3>
              <button
                type="button"
                onClick={() => navigate(ROUTES.camera)}
                className="text-[10px] font-semibold text-[#1E4D38] hover:underline"
              >
                Xem tất cả ›
              </button>
            </div>
            <div className="relative min-h-0 flex-1 overflow-hidden rounded-xl bg-black">
              <img
                src={cameras[selectedCameraIndex].src}
                alt="Camera feed"
                className="h-full w-full object-cover"
              />
              <div className="absolute top-2 left-2 flex items-center gap-1 rounded-md bg-[#22C55E]/90 px-2 py-0.5 text-[9px] font-bold text-white">
                <span className="h-1.5 w-1.5 animate-ping rounded-full bg-white" />
                LIVE
              </div>
              <div className="absolute inset-0 flex items-center justify-center">
                <button
                  type="button"
                  onClick={() => navigate(ROUTES.camera)}
                  className="flex h-9 w-9 items-center justify-center rounded-full bg-black/45 text-white backdrop-blur-xs transition hover:scale-110"
                  aria-label="Play"
                >
                  <svg
                    className="ml-0.5 h-4 w-4 fill-current"
                    viewBox="0 0 24 24"
                  >
                    <polygon points="5 3 19 12 5 21 5 3" />
                  </svg>
                </button>
              </div>
            </div>
            <div className="mt-2 flex shrink-0 items-center gap-2 overflow-x-auto pb-0.5">
              {cameras.map((cam, idx) =>
                idx === selectedCameraIndex ? null : (
                <button
                  key={cam.name}
                  type="button"
                  onClick={() => setSelectedCameraIndex(idx)}
                  className="group relative h-11 w-16 shrink-0 overflow-hidden rounded-lg border-2 transition hover:border-[#1E4D38]"
                >
                  <img
                    src={cam.thumb}
                    alt={cam.name}
                    className="h-full w-full object-cover"
                  />
                  <span className="absolute bottom-0.5 left-1 text-[8px] font-semibold text-white drop-shadow-md">
                    {cam.name}
                  </span>
                </button>
                ),
              )}
              <button
                type="button"
                onClick={() => navigate(ROUTES.camera)}
                className="flex h-11 w-6 shrink-0 items-center justify-center rounded-lg bg-[#F4F6F3] text-[#718076] hover:bg-[#E2EFE5]"
                aria-label="View more cameras"
              >
                ›
              </button>
            </div>
          </div>

          <div className="flex min-h-0 flex-col justify-between overflow-hidden rounded-2xl border border-[#E6ECE3] bg-white p-2.5 sm:p-3 shadow-sm lg:col-span-5">
            <div className="flex min-h-0 flex-col">
              <div className="flex items-center gap-1.5">
                <LeafIcon className="h-3.5 w-3.5 text-[#2D6A4F]" />
                <h3 className="font-display text-xs font-bold text-[#1C2721]">
                  Điện năng hôm nay
                </h3>
              </div>
              <div className="mt-1.5 grid grid-cols-3 gap-1.5">
                <div className="rounded-xl bg-[#F8FAF7] p-1.5 text-center">
                  <p className="text-[8.5px] text-[#718076]">Tiêu thụ</p>
                  <p className="font-display text-xs sm:text-sm font-bold text-[#1C2721]">
                    {energyTotal.toFixed(2)} <span className="text-[8.5px] font-normal">kWh</span>
                  </p>
                </div>
                <div className="rounded-xl bg-[#F8FAF7] p-1.5 text-center">
                  <p className="text-[8.5px] text-[#718076]">Nguồn</p>
                  <p className="font-display text-xs sm:text-sm font-bold text-[#22C55E]">
                    {energy?.source === "estimated" ? "Ước tính" : "Đo thật"}
                  </p>
                </div>
                <div className="rounded-xl bg-[#F8FAF7] p-1.5 text-center">
                  <p className="text-[8.5px] text-[#718076]">Chi phí</p>
                  <p className="font-display text-xs sm:text-sm font-bold text-[#1C2721]">
                    {Math.round(energy?.estimated_cost ?? 0).toLocaleString("vi-VN")} <span className="text-[8.5px] font-normal">đ</span>
                  </p>
                </div>
              </div>
              <div className="mt-1.5 min-h-0">
                <p className="text-[9.5px] font-semibold text-[#5A6860]">
                  Thiết bị tiêu thụ nhiều nhất
                </p>
                <div className="mt-1 space-y-1 text-[9.5px]">
                  {topEnergyDevices.map((item) => (
                    <div key={item.label}>
                      <div className="flex justify-between font-medium leading-tight text-[#1C2721]">
                        <span className="truncate">{item.label}</span>
                        <span>{item.pct}%</span>
                      </div>
                      <div className="mt-0.5 h-1 w-full overflow-hidden rounded-full bg-[#EDF2EB]">
                        <div
                          className="h-full rounded-full bg-[#2D6A4F]"
                          style={{ width: `${item.pct}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Row 3: Rooms + AI */}
        <div className="grid min-h-0 grid-cols-1 gap-2.5 lg:grid-cols-12">
          <div className="flex min-h-0 flex-col rounded-2xl border border-[#E6ECE3] bg-white p-3.5 shadow-sm lg:col-span-7">
            <div className="mb-2 flex shrink-0 items-center justify-between">
              <h3 className="font-display text-xs font-bold text-[#1C2721]">
                Phòng
              </h3>
              <button
                type="button"
                onClick={() =>
                  navigate(
                    primaryRoom
                      ? `${ROUTES.room}?room=${encodeURIComponent(primaryRoom.id)}`
                      : ROUTES.room,
                  )
                }
                className="text-[10px] font-semibold text-[#1E4D38] hover:underline"
              >
                {primaryRoom ? `Xem ${primaryRoom.label} ›` : "Xem phòng ›"}
              </button>
            </div>
            {homeLoading ? (
              <p className="text-[10px] text-[#88968E]">Đang tải phòng…</p>
            ) : roomCards.length === 0 ? (
              <p className="text-[10px] text-[#88968E]">Chưa có phòng nào</p>
            ) : (
              <div className="flex min-h-0 gap-2 overflow-x-auto pb-0.5">
                {roomCards.map((room) => (
                  <button
                    key={room.id}
                    type="button"
                    onClick={() =>
                      navigate(
                        `${ROUTES.room}?room=${encodeURIComponent(room.id)}`,
                      )
                    }
                    className="flex min-w-[88px] shrink-0 flex-col justify-between rounded-xl border border-[#E6ECE3] bg-[#F8FAF7] p-2.5 text-left transition hover:border-[#1E4D38] hover:bg-[#EDF3EB]"
                  >
                    <div className="flex items-center justify-between">
                      <span className="flex h-6 w-6 items-center justify-center rounded-md bg-[#E2EFE5] text-[#1E4D38]">
                        <NavRoomIcon className="h-3.5 w-3.5" />
                      </span>
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          room.activeInRoom > 0
                            ? "bg-[#22C55E]"
                            : "bg-[#CBD5E1]"
                        }`}
                      />
                    </div>
                    <div className="mt-1.5">
                      <p className="text-[10px] font-bold text-[#1C2721]">
                        {room.label}
                      </p>
                      <p className="text-[9px] text-[#718076]">
                        {room.deviceCount} thiết bị
                        {room.activeInRoom > 0
                          ? ` · ${room.activeInRoom} bật`
                          : ""}
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="relative flex min-h-0 flex-col justify-between overflow-hidden rounded-2xl border border-[#D7E8DA] bg-gradient-to-br from-[#EAF5ED] to-[#F4FAF5] p-3.5 shadow-sm lg:col-span-5">
            <div className="relative z-10">
              <div className="flex items-center gap-1.5 text-[#1E4D38]">
                <SparklesIcon className="h-4 w-4 text-[#2D6A4F]" />
                <h3 className="font-display text-xs font-bold">
                  Gợi ý từ HomeMate AI
                </h3>
              </div>
              <p className="mt-1.5 text-[10px] leading-relaxed text-[#3B4D42]">
                Nhiệt độ ngoài trời đang cao. Bạn có thể tăng 1°C điều hòa phòng
                {energy?.by_device[0]?.name ?? "Thiết bị tiêu thụ cao nhất"} đang dẫn đầu mức tiêu thụ hôm nay.
              </p>
            </div>
            <div className="relative z-10 mt-2">
              <button
                type="button"
                disabled={appliedAiTip}
                onClick={handleApplyAi}
                className="rounded-full bg-[#1E4D38] px-4 py-1.5 text-[10px] font-semibold text-white shadow-sm transition hover:bg-[#153828] disabled:opacity-75"
              >
                {appliedAiTip ? "✓ Đã áp dụng" : "Áp dụng ngay"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </TabletScreen>
  );
}
