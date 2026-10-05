/** Capability-based device control schema for HomeMind Hub. */

export type DeviceIconKind =
  | "bulb"
  | "snowflake"
  | "flame"
  | "lock"
  | "curtain"
  | "speaker"
  | "tv"
  | "fan"
  | "plug"
  | "camera"
  | "droplet";

export type DeviceStateValue = boolean | number | string;

export type DeviceState = Record<string, DeviceStateValue>;

/** Show control only when state matches all entries. */
export type ControlWhen = Record<string, DeviceStateValue>;

type ControlBase = {
  key: string;
  label: string;
  when?: ControlWhen;
};

export type ToggleControl = ControlBase & {
  type: "toggle";
};

export type RangeControl = ControlBase & {
  type: "range";
  min: number;
  max: number;
  step?: number;
  unit?: string;
};

export type StepControl = ControlBase & {
  type: "step";
  min: number;
  max: number;
  step?: number;
  unit?: string;
};

export type EnumOption = {
  value: string;
  label: string;
};

export type EnumControl = ControlBase & {
  type: "enum";
  options: EnumOption[];
};

export type LevelControl = ControlBase & {
  type: "level";
  /** Discrete levels, e.g. [0, 1, 2, 3] */
  levels: number[];
  labels: string[];
};

export type ActionControl = ControlBase & {
  type: "action";
  variant?: "primary" | "danger";
  /** Triggers HITL / confirmation flow */
  sensitive?: boolean;
};

export type DeviceControl =
  | ToggleControl
  | RangeControl
  | StepControl
  | EnumControl
  | LevelControl
  | ActionControl;

export type RoomId =
  | "living"
  | "bed"
  | "kitchen"
  | "bath"
  | "office"
  | "balcony";

export interface Device {
  id: string;
  name: string;
  room: RoomId;
  kind: DeviceIconKind;
  state: DeviceState;
  controls: DeviceControl[];
}
