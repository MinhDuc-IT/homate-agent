import { useEffect, useMemo, useState, type ReactNode } from "react";
import { CloseIcon } from "@/assets/icons/CommonIcons";
import {
  BulbIcon,
  CameraIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  CurtainIcon,
  DropletIcon,
  FanIcon,
  FlameIcon,
  LockIcon,
  PlusIcon,
  PlugIcon,
  SnowflakeIcon,
  SpeakerIcon,
  TvIcon,
} from "@/assets/icons/HomeMindIcons";
import {
  createScene,
  deleteScene,
  fetchScenes,
  updateScene,
  type Scene,
} from "@/api/scenes";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import {
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
} from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { useDevices } from "@/context/DevicesContext";
import { useToast } from "@/context/ToastContext";
import type { Device, DeviceIconKind } from "@/types/device";
import { cn } from "@/utils/cn";
import {
  actionsForDevice,
  formatSceneStepLabel,
  isDeviceKind,
} from "@/utils/sceneSteps";

type DraftStep = {
  key: string;
  device_id: string;
  action: string;
  parameters: Record<string, unknown>;
};

function newKey() {
  return crypto.randomUUID();
}

function deviceIcon(kind: string, className = "h-4 w-4"): ReactNode {
  const k: DeviceIconKind = isDeviceKind(kind) ? kind : "plug";
  switch (k) {
    case "bulb":
      return <BulbIcon className={className} />;
    case "snowflake":
      return <SnowflakeIcon className={className} />;
    case "flame":
      return <FlameIcon className={className} />;
    case "lock":
      return <LockIcon className={className} />;
    case "curtain":
      return <CurtainIcon className={className} />;
    case "speaker":
      return <SpeakerIcon className={className} />;
    case "tv":
      return <TvIcon className={className} />;
    case "fan":
      return <FanIcon className={className} />;
    case "plug":
      return <PlugIcon className={className} />;
    case "camera":
      return <CameraIcon className={className} />;
    case "droplet":
      return <DropletIcon className={className} />;
  }
}

function sceneToDraft(scene: Scene): DraftStep[] {
  return scene.steps.map((step) => ({
    key: step.id,
    device_id: step.device_id,
    action: step.action,
    parameters: { ...step.parameters },
  }));
}

export function SceneManager() {
  const { showToast } = useToast();
  const { devices } = useDevices();
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [draftSteps, setDraftSteps] = useState<DraftStep[]>([]);
  const [saving, setSaving] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [newName, setNewName] = useState("");

  const expanded = scenes.find((s) => s.id === expandedId) ?? null;
  const deviceById = useMemo(
    () => Object.fromEntries(devices.map((d) => [d.id, d])),
    [devices],
  );

  const load = async (preferId?: string | null) => {
    setLoading(true);
    try {
      const data = await fetchScenes();
      setScenes(data);
      const nextId =
        preferId !== undefined
          ? (preferId ?? data[0]?.id ?? null)
          : (expandedId ?? data[0]?.id ?? null);
      setExpandedId(nextId);
      const scene = data.find((s) => s.id === nextId);
      if (scene) {
        setName(scene.name);
        setDraftSteps(sceneToDraft(scene));
      }
    } catch (err) {
      showToast(
        err instanceof Error ? err.message : "Không tải được kịch bản",
        "error",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- initial fetch
  }, []);

  const selectScene = (scene: Scene) => {
    setExpandedId(scene.id);
    setName(scene.name);
    setDraftSteps(sceneToDraft(scene));
  };

  const addStep = () => {
    const device = devices[0];
    if (!device) {
      showToast("Chưa có thiết bị", "error");
      return;
    }
    const option = actionsForDevice(device)[0];
    setDraftSteps((prev) => [
      ...prev,
      {
        key: newKey(),
        device_id: device.id,
        action: option.action,
        parameters: { ...option.parameters },
      },
    ]);
  };

  const changeStepDevice = (key: string, deviceId: string) => {
    const device = deviceById[deviceId];
    if (!device) return;
    const option = actionsForDevice(device)[0];
    setDraftSteps((prev) =>
      prev.map((step) =>
        step.key === key
          ? {
              ...step,
              device_id: deviceId,
              action: option.action,
              parameters: { ...option.parameters },
            }
          : step,
      ),
    );
  };

  const changeStepAction = (key: string, action: string, device: Device) => {
    const option = actionsForDevice(device).find((o) => o.action === action);
    setDraftSteps((prev) =>
      prev.map((step) =>
        step.key === key
          ? {
              ...step,
              action,
              parameters: { ...(option?.parameters ?? {}) },
            }
          : step,
      ),
    );
  };

  const saveExpanded = async () => {
    if (!expanded) return;
    setSaving(true);
    try {
      const title = name.trim();
      const updated = await updateScene(expanded.id, {
        name: title,
        voice_keyword: title,
        is_enabled: expanded.is_enabled,
        steps: draftSteps.map((step) => ({
          device_id: step.device_id,
          action: step.action,
          parameters: step.parameters,
        })),
      });
      setScenes((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
      setDraftSteps(sceneToDraft(updated));
      showToast("Đã lưu kịch bản", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Lưu thất bại", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleCreate = async () => {
    if (!newName.trim()) {
      showToast("Nhập tên kịch bản", "error");
      return;
    }
    setSaving(true);
    try {
      const title = newName.trim();
      const created = await createScene({
        name: title,
        voice_keyword: title,
        steps: [],
      });
      setCreateOpen(false);
      setNewName("");
      await load(created.id);
      showToast("Đã tạo kịch bản", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Tạo thất bại", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!expanded) return;
    if (!window.confirm(`Xóa kịch bản “${expanded.name}”?`)) return;
    setSaving(true);
    try {
      await deleteScene(expanded.id);
      showToast("Đã xóa kịch bản", "success");
      setExpandedId(null);
      await load(null);
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Xóa thất bại", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <div className="mb-3 flex items-center justify-between gap-3">
          <p className="font-display text-[15px] font-bold text-text-primary">
            Kịch bản
          </p>
          <Button
            size="sm"
            leftIcon={<PlusIcon className="h-3.5 w-3.5" />}
            onClick={() => setCreateOpen(true)}
          >
            Tạo kịch bản
          </Button>
        </div>

        {loading && scenes.length === 0 ? (
          <div className="flex justify-center py-10">
            <LoadingSpinner />
          </div>
        ) : scenes.length === 0 ? (
          <p className="py-8 text-center text-sm text-text-muted">
            Chưa có kịch bản
          </p>
        ) : (
          <div>
            {scenes.map((scenario, index) => {
              const isOpen = expandedId === scenario.id;
              return (
                <button
                  key={scenario.id}
                  type="button"
                  onClick={() => selectScene(scenario)}
                  className={cn(
                    "flex w-full items-center justify-between px-1 py-2.5 text-left",
                    index < scenes.length - 1 &&
                      "border-b border-sidebar-border",
                  )}
                >
                  <div>
                    <p className="text-sm font-medium text-text-primary">
                      {scenario.name}
                    </p>
                    <p className="mt-0.5 text-xs text-text-secondary">
                      {scenario.steps.length} hành động
                    </p>
                  </div>
                  {isOpen ? (
                    <ChevronDownIcon className="h-4 w-4 text-text-secondary" />
                  ) : (
                    <ChevronRightIcon className="h-4 w-4 text-text-secondary" />
                  )}
                </button>
              );
            })}
          </div>
        )}
      </Card>

      {expanded && (
        <Card>
          <p className="mb-2.5 text-sm text-text-secondary">
            Đang sửa: {expanded.name}
          </p>
          <FormField className="mb-3" label="Tên kịch bản">
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Đón khách"
            />
          </FormField>
          <div className="mb-3.5 flex flex-col gap-2">
            {draftSteps.map((step, index) => {
              const device = deviceById[step.device_id];
              const options = device ? actionsForDevice(device) : [];
              const kind = device?.kind ?? "plug";
              const label = formatSceneStepLabel(
                device?.name ?? step.device_id,
                step.action,
                step.parameters,
              );
              return (
                <div
                  key={step.key}
                  className="rounded-lg border border-sidebar-border bg-surface-subtle px-3 py-2.5"
                >
                  <div className="mb-2 flex items-center gap-2">
                    <span className="flex h-5 w-6 shrink-0 items-center justify-center text-xs text-text-muted">
                      {index + 1}
                    </span>
                    <p
                      className="min-w-0 flex-1 truncate text-xs text-text-muted"
                      title={label}
                    >
                      {label}
                    </p>
                  </div>
                  <div className="grid grid-cols-[1.5rem_minmax(0,1fr)] items-center gap-x-2 gap-y-2">
                    <span className="flex h-10 items-center justify-center text-text-secondary">
                      {deviceIcon(kind)}
                    </span>
                    <Select
                      className="w-full min-w-0"
                      value={step.device_id}
                      onChange={(e) =>
                        changeStepDevice(step.key, e.target.value)
                      }
                      aria-label="Thiết bị"
                    >
                      {devices.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name}
                        </option>
                      ))}
                    </Select>

                    <button
                      type="button"
                      className="flex h-10 items-center justify-center rounded-lg text-text-muted hover:bg-elevated hover:text-text-primary"
                      aria-label="Xóa hành động"
                      onClick={() =>
                        setDraftSteps((prev) =>
                          prev.filter((s) => s.key !== step.key),
                        )
                      }
                    >
                      <CloseIcon className="h-3.5 w-3.5" />
                    </button>
                    <div className="flex min-w-0 flex-wrap items-center gap-2">
                      <Select
                        className="min-w-0 flex-1"
                        value={step.action}
                        onChange={(e) =>
                          device &&
                          changeStepAction(step.key, e.target.value, device)
                        }
                        aria-label="Hành động"
                      >
                        {options.map((opt) => (
                          <option key={opt.action} value={opt.action}>
                            {opt.label}
                          </option>
                        ))}
                        {options.every((o) => o.action !== step.action) ? (
                          <option value={step.action}>{step.action}</option>
                        ) : null}
                      </Select>
                      {step.action === "set_brightness" ? (
                        <Input
                          type="number"
                          className="w-[5.5rem] shrink-0"
                          min={1}
                          max={100}
                          value={Number(step.parameters.brightness ?? 60)}
                          onChange={(e) =>
                            setDraftSteps((prev) =>
                              prev.map((s) =>
                                s.key === step.key
                                  ? {
                                      ...s,
                                      parameters: {
                                        brightness: Number(e.target.value),
                                      },
                                    }
                                  : s,
                              ),
                            )
                          }
                          aria-label="Độ sáng"
                        />
                      ) : null}
                      {step.action === "set_temperature" ? (
                        <Input
                          type="number"
                          className="w-[5.5rem] shrink-0"
                          min={16}
                          max={30}
                          value={Number(step.parameters.temperature ?? 26)}
                          onChange={(e) =>
                            setDraftSteps((prev) =>
                              prev.map((s) =>
                                s.key === step.key
                                  ? {
                                      ...s,
                                      parameters: {
                                        temperature: Number(e.target.value),
                                      },
                                    }
                                  : s,
                              ),
                            )
                          }
                          aria-label="Nhiệt độ"
                        />
                      ) : null}
                    </div>
                  </div>
                </div>
              );
            })}
            <Button
              variant="outline"
              size="sm"
              className="self-start"
              leftIcon={<PlusIcon className="h-3.5 w-3.5" />}
              onClick={addStep}
            >
              Thêm hành động
            </Button>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2.5 border-t border-sidebar-border pt-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => void handleDelete()}
              disabled={saving}
            >
              Xóa
            </Button>
            <Button
              size="sm"
              onClick={() => void saveExpanded()}
              disabled={saving}
            >
              {saving ? "Đang lưu…" : "Lưu"}
            </Button>
          </div>
        </Card>
      )}

      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        maxWidth="sm"
      >
        <ModalHeader
          onClose={() => setCreateOpen(false)}
          title="Tạo kịch bản"
        />
        <ModalBody>
          <div className="flex flex-col gap-2.5">
            <FormField
              label="Tên kịch bản"
              hint="Nói tên này để kích hoạt kịch bản"
            >
              <Input
                placeholder="Đón khách"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
            </FormField>
          </div>
        </ModalBody>
        <ModalFooter>
          <Button variant="outline" onClick={() => setCreateOpen(false)}>
            Hủy
          </Button>
          <Button onClick={() => void handleCreate()} disabled={saving}>
            Tạo
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  );
}
