import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  ThermometerIcon,
  UsersIcon,
  WaterDropletIcon,
  ZapIcon,
} from "@/assets/icons/HomemateIcons";
import { fetchAmbient } from "@/api/ambient";
import {
  BulbIcon,
  CameraIcon,
  CurtainIcon,
  DropletIcon,
  FanIcon,
  FlameIcon,
  LockIcon,
  PlugIcon,
  SnowflakeIcon,
  SpeakerIcon,
  TvIcon,
} from "@/assets/icons/HomeMindIcons";
import { TabletScreen } from "@/components/layout/TabletScreen";
import { ROUTES } from "@/config/routes";
import { useDevices } from "@/context/DevicesContext";
import { useSession } from "@/context/SessionContext";
import { useToast } from "@/context/ToastContext";
import { useEnergy } from "@/hooks/useEnergy";
import { useSchedules } from "@/hooks/useSchedules";
import { updateSchedule } from "@/api/schedules";
import type { AmbientSnapshot } from "@/types/ambient";
import type { Device, DeviceIconKind } from "@/types/device";
import { formatDeviceStatus } from "@/utils/deviceStatus";

function deviceIcon(kind: DeviceIconKind) {
  const className = "h-3 w-3";
  switch (kind) {
    case "bulb": return <BulbIcon className={className} />;
    case "snowflake": return <SnowflakeIcon className={className} />;
    case "flame": return <FlameIcon className={className} />;
    case "lock": return <LockIcon className={className} />;
    case "curtain": return <CurtainIcon className={className} />;
    case "speaker": return <SpeakerIcon className={className} />;
    case "tv": return <TvIcon className={className} />;
    case "fan": return <FanIcon className={className} />;
    case "plug": return <PlugIcon className={className} />;
    case "camera": return <CameraIcon className={className} />;
    case "droplet": return <DropletIcon className={className} />;
  }
}

function Toggle({ on, onToggle }: { on: boolean; onToggle: () => void }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${
        on ? "bg-[#2D6A4F]" : "bg-gray-300"
      }`}
    >
      <span
        className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition ${
          on ? "translate-x-4" : "translate-x-0"
        }`}
      />
    </button>
  );
}

export function RoomScreen() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { showToast } = useToast();
  const { rooms, homeLoading } = useSession();
  const { devices, loading: devicesLoading, error: devicesError, applyAction } = useDevices();
  const [ambient, setAmbient] = useState<AmbientSnapshot | null>(null);

  const requestedRoomId = searchParams.get("room");
  const selectedRoom = useMemo(
    () =>
      rooms.find((room) => room.id === requestedRoomId) ??
      rooms.find((room) => room.id === "living") ??
      rooms[0],
    [requestedRoomId, rooms],
  );
  const roomDeviceCount = devices.filter(
    (device) => device.room === selectedRoom?.id,
  ).length;
  const roomDevices = useMemo(
    () => devices.filter((device) => device.room === selectedRoom?.id),
    [devices, selectedRoom?.id],
  );
  const { data: roomEnergy } = useEnergy("today", { roomId: selectedRoom?.id });
  const roomAmbient = ambient?.rooms.find((room) => room.id === selectedRoom?.id);

  useEffect(() => {
    let active = true;
    const loadAmbient = async () => {
      try {
        const snapshot = await fetchAmbient();
        if (active) setAmbient(snapshot);
      } catch {
        // The card renders unavailable values when the ambient API cannot be reached.
      }
    };

    void loadAmbient();
    const timer = window.setInterval(() => void loadAmbient(), 60_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (!selectedRoom || requestedRoomId === selectedRoom.id) return;
    setSearchParams({ room: selectedRoom.id }, { replace: true });
  }, [requestedRoomId, selectedRoom, setSearchParams]);

  const selectRoom = (roomId: string) => {
    setSearchParams({ room: roomId });
  };

  const { data: schedules, loading: schedulesLoading, error: schedulesError, reload: reloadSchedules } = useSchedules({ roomId: selectedRoom?.id });

  const toggleSchedule = async (id: string, enabled: boolean) => {
    try {
      await updateSchedule(id, { enabled: !enabled });
      await reloadSchedules();
    } catch (cause) {
      showToast(cause instanceof Error ? cause.message : "Không cập nhật được lịch", "error");
    }
  };

  const toggleApiDevice = async (device: Device) => {
    const next = !device.state.power;
    const updated = await applyAction(device.id, "power", next);
    if (updated) {
      showToast(`${device.name}: ${next ? "Đã bật" : "Đã tắt"}`, next ? "success" : "info");
    }
  };

  const roomEnergyMax = Math.max(0.001, ...(roomEnergy?.timeseries ?? []).map((item) => item.kwh));
  const hourlyBars = Array.from({ length: 24 }, (_, hour) => {
    const marker = `T${String(hour).padStart(2, "0")}:`;
    return roomEnergy?.timeseries.find((item) => item.bucket.includes(marker))?.kwh ?? 0;
  });

  return (
    <TabletScreen>
      <div className="grid h-full min-h-0 grid-rows-[minmax(0,1.15fr)_minmax(0,0.85fr)] gap-2.5">
        {/* Top: visual + environment/devices */}
        <div className="grid min-h-0 grid-cols-1 gap-2.5 lg:grid-cols-12">
          <div className="relative min-h-0 overflow-hidden rounded-2xl border border-[#E6ECE3] bg-white shadow-sm lg:col-span-7">
            <div className="relative h-full min-h-[140px] w-full">
              <img
                src="/assets/images/room_living.png"
                alt={selectedRoom?.label ?? "Phòng"}
                className="h-full w-full object-cover"
              />
              <div className="absolute top-3 left-3 z-10 rounded-xl bg-white/90 p-1.5 shadow-sm backdrop-blur-sm">
                <label htmlFor="room-picker" className="sr-only">
                  Chọn phòng
                </label>
                <select
                  id="room-picker"
                  value={selectedRoom?.id ?? ""}
                  onChange={(event) => selectRoom(event.target.value)}
                  disabled={homeLoading || rooms.length === 0}
                  className="min-w-36 rounded-lg border border-[#D7E3D8] bg-white px-2.5 py-1.5 text-xs font-bold text-[#1C2721] outline-none focus:border-[#2D6A4F] disabled:opacity-60"
                >
                  {rooms.length === 0 ? (
                    <option value="">Chưa có phòng</option>
                  ) : (
                    rooms.map((room) => (
                      <option key={room.id} value={room.id}>
                        {room.label}
                      </option>
                    ))
                  )}
                </select>
                {selectedRoom && (
                  <p className="px-1 pt-1 text-[9px] text-[#5A6860]">
                    {roomDeviceCount} thiết bị
                  </p>
                )}
              </div>
            </div>
          </div>

          <div className="flex min-h-0 flex-col gap-2 lg:col-span-5">
            <div className="shrink-0 rounded-2xl border border-[#E6ECE3] bg-white p-3 shadow-sm">
              <h3 className="font-display text-xs font-bold text-[#1C2721]">
                Môi trường
              </h3>
              <div className="mt-2 grid grid-cols-3 gap-1.5">
                {[
                  {
                    icon: (
                      <ThermometerIcon className="mx-auto h-3.5 w-3.5 text-[#2D6A4F]" />
                    ),
                    value: roomAmbient?.indoor_temp_c != null
                      ? `${roomAmbient.indoor_temp_c.toFixed(1)}°C`
                      : "—",
                    label: "Nhiệt độ",
                  },
                  {
                    icon: (
                      <WaterDropletIcon className="mx-auto h-3.5 w-3.5 text-blue-500" />
                    ),
                    value: roomAmbient?.indoor_humidity != null
                      ? `${roomAmbient.indoor_humidity.toFixed(0)}%`
                      : "—",
                    label: "Độ ẩm",
                  },
                  {
                    icon: (
                      <UsersIcon className="mx-auto h-3.5 w-3.5 text-purple-600" />
                    ),
                    value: roomAmbient ? (roomAmbient.occupied ? "Có" : "Không") : "—",
                    label: "Hiện diện",
                  },
                ].map((stat) => (
                  <div
                    key={stat.label}
                    className="rounded-xl bg-[#F8FAF7] p-1.5 text-center"
                  >
                    {stat.icon}
                    <p className="mt-0.5 font-display text-[10px] font-bold text-[#1C2721]">
                      {stat.value}
                    </p>
                    <p className="text-[8px] text-[#718076]">{stat.label}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex min-h-0 flex-1 flex-col rounded-2xl border border-[#E6ECE3] bg-white p-3 shadow-sm">
              <div className="mb-1.5 flex shrink-0 items-center justify-between">
                <h3 className="font-display text-xs font-bold text-[#1C2721]">
                  Thiết bị
                </h3>
                <button
                  type="button"
                  onClick={() => navigate(ROUTES.devices)}
                  className="text-[10px] font-semibold text-[#1E4D38] hover:underline"
                >
                  Tất cả ›
                </button>
              </div>
              <div className="min-h-0 flex-1 space-y-1 overflow-y-auto text-[11px]">
                {devicesLoading ? (
                  <p className="px-2 py-3 text-center text-[10px] text-[#718076]">Đang tải thiết bị…</p>
                ) : devicesError ? (
                  <p className="px-2 py-3 text-center text-[10px] text-red-600">{devicesError}</p>
                ) : roomDevices.length === 0 ? (
                  <p className="px-2 py-3 text-center text-[10px] text-[#718076]">Phòng này chưa có thiết bị.</p>
                ) : roomDevices.map((device) => {
                  const hasPowerToggle = device.controls.some(
                    (control) => control.type === "toggle" && control.key === "power",
                  );
                  return (
                  <div
                    key={device.id}
                    className="flex items-center justify-between rounded-lg bg-[#F8FAF7] px-2 py-1.5"
                  >
                    <div className="flex min-w-0 items-center gap-2">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-[#E2EFE5] text-[#1E4D38]">
                        {deviceIcon(device.kind)}
                      </span>
                      <div className="min-w-0">
                        <p className="truncate font-semibold text-[#1C2721]">
                          {device.name}
                        </p>
                        <p className="truncate text-[9px] text-[#718076]">
                          {selectedRoom?.label} · {formatDeviceStatus(device)}
                        </p>
                      </div>
                    </div>
                    {!hasPowerToggle ? (
                      <button
                        type="button"
                        onClick={() => navigate(`${ROUTES.devices}?device=${encodeURIComponent(device.id)}`)}
                        className="text-[10px] font-bold text-[#1E4D38]"
                      >
                        ›
                      </button>
                    ) : (
                      <Toggle
                        on={device.state.power === true}
                        onToggle={() => void toggleApiDevice(device)}
                      />
                    )}
                  </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* Bottom: energy + schedule */}
        <div className="grid min-h-0 grid-cols-1 gap-2.5 lg:grid-cols-12">
          <div className="flex min-h-0 flex-col rounded-2xl border border-[#E6ECE3] bg-white p-3 shadow-sm lg:col-span-8">
            <h3 className="font-display text-xs font-bold text-[#1C2721]">
              Điện năng hôm nay
            </h3>
            <div className="mt-2 grid grid-cols-2 gap-1.5 text-[10px]">
              <div className="rounded-lg bg-[#F8FAF7] p-2">
                <p className="flex items-center gap-1 text-[9px] text-[#718076]">
                  <ZapIcon className="h-2.5 w-2.5 text-[#2D6A4F]" /> Tiêu thụ
                </p>
                <p className="mt-0.5 font-display text-xs font-bold text-[#1C2721]">
                  {(roomEnergy?.total_kwh ?? 0).toFixed(2)} kWh
                </p>
              </div>
              <div className="rounded-lg bg-[#F8FAF7] p-2">
                <p className="text-[9px] text-[#718076]">Chi phí ước tính</p>
                <p className="mt-0.5 font-display text-xs font-bold text-[#1C2721]">
                  {Math.round(roomEnergy?.estimated_cost ?? 0).toLocaleString("vi-VN")} đ
                </p>
              </div>
            </div>
            <div className="mt-2 flex min-h-0 flex-1 flex-col">
              <div className="flex min-h-12 flex-1 items-end gap-px">
                {hourlyBars.map((val, idx) => (
                  <div
                    key={idx}
                    className="group relative flex h-full flex-1 items-end"
                    title={`${String(idx).padStart(2, "0")}:00: ${val.toFixed(3)} kWh`}
                  >
                    <div
                      className="w-full rounded-t-xs bg-[#2D6A4F] transition-all group-hover:bg-[#1E4D38]"
                      style={{ height: `${Math.max(2, val / roomEnergyMax * 100)}%` }}
                    />
                    <div className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-1 hidden -translate-x-1/2 whitespace-nowrap rounded-md bg-[#1C2721] px-1.5 py-1 text-[8px] font-semibold text-white shadow-lg group-hover:block">
                      <span>{String(idx).padStart(2, "0")}:00</span>
                      <span className="ml-1 text-[#B7DFC1]">{val.toFixed(3)} kWh</span>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-1 flex justify-between text-[8px] text-[#88968E]">
                <span>00:00</span>
                <span>12:00</span>
                <span>24:00</span>
              </div>
            </div>
          </div>

          <div className="flex min-h-0 flex-col rounded-2xl border border-[#E6ECE3] bg-white p-3 shadow-sm lg:col-span-4">
            <div className="mb-1.5 flex shrink-0 items-center justify-between">
              <h3 className="font-display text-xs font-bold text-[#1C2721]">
                Lịch tự động
              </h3>
              <button
                type="button"
                onClick={() => navigate(ROUTES.schedules)}
                className="text-[10px] font-semibold text-[#1E4D38] hover:underline"
              >
                Tất cả ›
              </button>
            </div>
            <div className="min-h-0 flex-1 space-y-1.5 overflow-y-auto text-[10px]">
              {schedulesLoading ? <p className="p-2 text-center text-[#718076]">Đang tải lịch…</p> : schedulesError ? <p className="p-2 text-center text-red-600">{schedulesError}</p> : schedules.length === 0 ? <p className="p-2 text-center text-[#718076]">Phòng này chưa có lịch.</p> : schedules.slice(0, 4).map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between rounded-xl bg-[#F8FAF7] p-2"
                >
                  <div className="min-w-0">
                    <p className="font-bold text-[#1C2721]">
                      {item.next_run_at ? new Date(item.next_run_at).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" }) : "—"}{" "}
                      <span className="font-normal text-[#5A6860]">
                        {item.name}
                      </span>
                    </p>
                    <p className="text-[9px] text-[#88968E]">{item.schedule_type === "once" ? "Một lần" : "Lặp lại"}</p>
                  </div>
                  <Toggle
                    on={item.enabled}
                    onToggle={() => void toggleSchedule(item.id, item.enabled)}
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </TabletScreen>
  );
}
