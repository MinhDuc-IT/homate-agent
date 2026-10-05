import type { Device, DeviceIconKind, DeviceStateValue } from "@/types/device";

export type SceneActionOption = {
  action: string;
  label: string;
  parameters: Record<string, unknown>;
};

type ApplyAction = (
  deviceId: string,
  key: string,
  value?: DeviceStateValue | null,
) => Promise<Device | null>;

function hasPowerToggle(device: Device): boolean {
  return device.controls.some(
    (control) => control.type === "toggle" && control.key === "power",
  );
}

function levelOffControl(device: Device) {
  return device.controls.find((control) => control.type === "level");
}

export function resolveTurnOnOff(
  device: Device,
  action: string,
): [string, DeviceStateValue] | null {
  if (action !== "turn_on" && action !== "turn_off") return null;
  if (hasPowerToggle(device)) {
    return ["power", action === "turn_on"];
  }
  const control = levelOffControl(device);
  if (!control || control.type !== "level") return null;
  if (action === "turn_off") return [control.key, 0];
  const positive = Math.min(...control.levels.filter((level) => level > 0));
  return [control.key, positive];
}

export async function executeSceneStep(
  applyAction: ApplyAction,
  device: Device | undefined,
  action: string,
  parameters: Record<string, unknown>,
): Promise<boolean> {
  if (!device) return false;

  if (action === "turn_on" || action === "turn_off") {
    const mapped = resolveTurnOnOff(device, action);
    if (!mapped) return false;
    return (await applyAction(device.id, mapped[0], mapped[1])) !== null;
  }

  if (action === "set_brightness") {
    await applyAction(device.id, "power", true);
    return (
      (await applyAction(
        device.id,
        "brightness",
        Number(parameters.brightness ?? 60),
      )) !== null
    );
  }

  if (action === "set_temperature") {
    await applyAction(device.id, "power", true);
    return (
      (await applyAction(
        device.id,
        "temperature",
        Number(parameters.temperature ?? 26),
      )) !== null
    );
  }

  if (action === "unlock" || action === "lock") {
    return (await applyAction(device.id, action, true)) !== null;
  }

  if (action === "open") {
    const preset = await applyAction(device.id, "preset", "open");
    const position = await applyAction(device.id, "position", 100);
    return preset !== null || position !== null;
  }

  if (action === "close") {
    const preset = await applyAction(device.id, "preset", "closed");
    const position = await applyAction(device.id, "position", 0);
    return preset !== null || position !== null;
  }

  if (action === "set_speed") {
    return (
      (await applyAction(
        device.id,
        "speed",
        Number(parameters.speed ?? 1),
      )) !== null
    );
  }

  return (await applyAction(device.id, action, true)) !== null;
}

export async function executeSceneSteps(
  steps: Array<{
    sort_order: number;
    device_id: string;
    action: string;
    parameters: Record<string, unknown>;
  }>,
  devices: Device[],
  applyAction: ApplyAction,
): Promise<{ ok: number; fail: number }> {
  const deviceById = Object.fromEntries(devices.map((device) => [device.id, device]));
  let ok = 0;
  let fail = 0;

  for (const step of [...steps].sort((a, b) => a.sort_order - b.sort_order)) {
    const success = await executeSceneStep(
      applyAction,
      deviceById[step.device_id],
      step.action,
      step.parameters,
    );
    if (success) ok += 1;
    else fail += 1;
    await new Promise((resolve) => window.setTimeout(resolve, 120));
  }

  return { ok, fail };
}

export function actionsForDevice(device: Device): SceneActionOption[] {
  const options: SceneActionOption[] = [];
  const hasPower = device.controls.some(
    (c) => c.type === "toggle" && c.key === "power",
  );
  if (hasPower) {
    options.push({ action: "turn_on", label: "Bật", parameters: {} });
    options.push({ action: "turn_off", label: "Tắt", parameters: {} });
  }
  const brightness = device.controls.find(
    (c) => c.type === "range" && c.key === "brightness",
  );
  if (brightness && brightness.type === "range") {
    options.push({
      action: "set_brightness",
      label: "Độ sáng",
      parameters: { brightness: 60 },
    });
  }
  const temperature = device.controls.find(
    (c) => c.type === "step" && c.key === "temperature",
  );
  if (temperature && temperature.type === "step") {
    options.push({
      action: "set_temperature",
      label: "Nhiệt độ",
      parameters: { temperature: 26 },
    });
  }
  const level = device.controls.find((c) => c.type === "level");
  if (level) {
    options.push({ action: "open", label: "Mở / kéo lên", parameters: {} });
    options.push({
      action: "close",
      label: "Đóng / kéo xuống",
      parameters: {},
    });
  }
  for (const control of device.controls) {
    if (control.type === "action") {
      const label =
        control.key === "lock"
          ? "Khóa"
          : control.key === "unlock"
            ? "Mở khóa"
            : control.label;
      options.push({ action: control.key, label, parameters: {} });
    }
  }
  if (options.length === 0) {
    options.push({ action: "turn_on", label: "Bật", parameters: {} });
  }
  return options;
}

export function formatSceneStepLabel(
  deviceName: string,
  action: string,
  parameters: Record<string, unknown>,
): string {
  if (action === "turn_on") return `${deviceName} → bật`;
  if (action === "turn_off") return `${deviceName} → tắt`;
  if (action === "set_brightness") {
    return `${deviceName} → độ sáng ${String(parameters.brightness ?? "")}%`;
  }
  if (action === "set_temperature") {
    return `${deviceName} → ${String(parameters.temperature ?? "")}°C`;
  }
  if (action === "open") return `${deviceName} → mở`;
  if (action === "close") return `${deviceName} → đóng`;
  if (action === "lock") return `${deviceName} → khóa`;
  if (action === "unlock") return `${deviceName} → mở khóa`;
  return `${deviceName} → ${action}`;
}

export function isDeviceKind(kind: string): kind is DeviceIconKind {
  return [
    "bulb",
    "snowflake",
    "flame",
    "lock",
    "curtain",
    "speaker",
    "tv",
    "fan",
    "plug",
    "camera",
    "droplet",
  ].includes(kind);
}
