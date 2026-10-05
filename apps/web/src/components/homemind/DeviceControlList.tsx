import type { Device, DeviceControl, DeviceStateValue } from '@/types/device'
import { Button } from '@/components/ui/Button'
import { ToggleSwitch } from '@/components/homemind/ToggleSwitch'
import { Pill } from '@/components/ui/Pill'
import { cn } from '@/utils/cn'

type DeviceControlTheme = 'default' | 'green'

interface DeviceControlListProps {
  device: Device
  controls: DeviceControl[]
  onChange: (key: string, value: DeviceStateValue) => void
  onAction: (key: string, sensitive?: boolean) => void
  theme?: DeviceControlTheme
}

const greenTheme = {
  label: 'text-[10px] font-semibold text-[#5A6860]',
  value: 'text-[10px] font-semibold tabular-nums text-[#1E4D38]',
  valueLarge: 'font-display text-2xl font-extrabold text-[#1C2721]',
  valueUnit: 'text-sm font-normal text-[#718076]',
  rowGap: 'gap-2',
  stackGap: 'gap-1.5',
  listGap: 'gap-3',
  toggleOn: 'bg-[#2D6A4F]',
  toggleOff: 'bg-[#CBD5CE]',
  range: 'accent-[#2D6A4F]',
  optionActive:
    'border border-[#2D6A4F] bg-[#E8F5EB] text-[#1E4D38]',
  optionInactive:
    'border border-transparent bg-[#F8FAF7] text-[#5A6860] hover:bg-[#EDF3EB]',
  stepBtn:
    'flex h-8 w-8 items-center justify-center rounded-full bg-white text-sm font-bold text-[#1C2721] shadow-sm transition hover:bg-[#E2EFE5] disabled:opacity-50',
  actionPrimary:
    'w-full bg-[#1E4D38] text-white hover:bg-[#153828] border-transparent',
  levelBarActive: 'bg-[#2D6A4F]',
  levelBarInactive: 'bg-[#D5E5D8]',
}

export function DeviceControlList({
  device,
  controls,
  onChange,
  onAction,
  theme = 'default',
}: DeviceControlListProps) {
  const isGreen = theme === 'green'

  return (
    <div className={cn('flex flex-col', isGreen ? greenTheme.listGap : 'gap-4')}>
      {controls.map((control) => (
        <ControlRow
          key={`${control.type}-${control.key}`}
          control={control}
          value={device.state[control.key]}
          onChange={onChange}
          onAction={onAction}
          theme={theme}
        />
      ))}
    </div>
  )
}

function ControlRow({
  control,
  value,
  onChange,
  onAction,
  theme,
}: {
  control: DeviceControl
  value: DeviceStateValue | undefined
  onChange: (key: string, value: DeviceStateValue) => void
  onAction: (key: string, sensitive?: boolean) => void
  theme: DeviceControlTheme
}) {
  const isGreen = theme === 'green'

  switch (control.type) {
    case 'toggle':
      return (
        <div
          className={cn(
            'flex items-center justify-between',
            isGreen ? greenTheme.rowGap : 'gap-3',
          )}
        >
          <span
            className={
              isGreen ? greenTheme.label : 'text-sm font-medium text-text-primary'
            }
          >
            {control.label}
          </span>
          <button
            type="button"
            onClick={() => onChange(control.key, !(value === true))}
            className="rounded-md p-0.5"
            aria-label={control.label}
          >
            {isGreen ? (
              <span
                className={cn(
                  'relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 border-transparent transition-colors',
                  value === true ? greenTheme.toggleOn : greenTheme.toggleOff,
                )}
              >
                <span
                  className={cn(
                    'inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition',
                    value === true ? 'translate-x-4' : 'translate-x-0',
                  )}
                />
              </span>
            ) : (
              <ToggleSwitch checked={value === true} />
            )}
          </button>
        </div>
      )

    case 'range': {
      const num = typeof value === 'number' ? value : control.min
      return (
        <div
          className={cn(
            'flex flex-col',
            isGreen ? greenTheme.stackGap : 'gap-2',
          )}
        >
          <div className="flex items-center justify-between">
            <span
              className={
                isGreen ? greenTheme.label : 'text-sm font-medium text-text-primary'
              }
            >
              {control.label}
            </span>
            {isGreen ? (
              <div className="text-center">
                <span className={greenTheme.valueLarge}>{num}</span>
                {control.unit ? (
                  <span className={greenTheme.valueUnit}>{control.unit}</span>
                ) : null}
              </div>
            ) : (
              <span className="text-sm tabular-nums text-text-secondary">
                {num}
                {control.unit ?? ''}
              </span>
            )}
          </div>
          {isGreen ? (
            <div className="flex items-center justify-center gap-3">
              <button
                type="button"
                className={greenTheme.stepBtn}
                onClick={() =>
                  onChange(
                    control.key,
                    Math.max(control.min, num - (control.step ?? 1)),
                  )
                }
                disabled={num <= control.min}
              >
                −
              </button>
              <input
                type="range"
                min={control.min}
                max={control.max}
                step={control.step ?? 1}
                value={num}
                onChange={(e) => onChange(control.key, Number(e.target.value))}
                className={cn('h-1.5 w-full cursor-pointer', greenTheme.range)}
              />
              <button
                type="button"
                className={greenTheme.stepBtn}
                onClick={() =>
                  onChange(
                    control.key,
                    Math.min(control.max, num + (control.step ?? 1)),
                  )
                }
                disabled={num >= control.max}
              >
                +
              </button>
            </div>
          ) : (
            <input
              type="range"
              min={control.min}
              max={control.max}
              step={control.step ?? 1}
              value={num}
              onChange={(e) => onChange(control.key, Number(e.target.value))}
              className="h-2 w-full cursor-pointer accent-homemind"
            />
          )}
        </div>
      )
    }

    case 'step': {
      const num = typeof value === 'number' ? value : control.min
      const step = control.step ?? 1
      return (
        <div
          className={cn(
            'flex items-center justify-between',
            isGreen ? greenTheme.rowGap : 'gap-3',
          )}
        >
          <span
            className={
              isGreen ? greenTheme.label : 'text-sm font-medium text-text-primary'
            }
          >
            {control.label}
          </span>
          <div className="flex items-center gap-2">
            {isGreen ? (
              <>
                <button
                  type="button"
                  className={greenTheme.stepBtn}
                  onClick={() =>
                    onChange(control.key, Math.max(control.min, num - step))
                  }
                  disabled={num <= control.min}
                >
                  −
                </button>
                <span className={cn('min-w-14 text-center', greenTheme.value)}>
                  {num}
                  {control.unit ?? ''}
                </span>
                <button
                  type="button"
                  className={greenTheme.stepBtn}
                  onClick={() =>
                    onChange(control.key, Math.min(control.max, num + step))
                  }
                  disabled={num >= control.max}
                >
                  +
                </button>
              </>
            ) : (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8 w-8 px-0"
                  onClick={() =>
                    onChange(control.key, Math.max(control.min, num - step))
                  }
                  disabled={num <= control.min}
                >
                  −
                </Button>
                <span className="min-w-14 text-center text-sm font-semibold tabular-nums text-text-primary">
                  {num}
                  {control.unit ?? ''}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8 w-8 px-0"
                  onClick={() =>
                    onChange(control.key, Math.min(control.max, num + step))
                  }
                  disabled={num >= control.max}
                >
                  +
                </Button>
              </>
            )}
          </div>
        </div>
      )
    }

    case 'enum':
      return (
        <div
          className={cn(
            'flex flex-col',
            isGreen ? greenTheme.stackGap : 'gap-2',
          )}
        >
          <span
            className={
              isGreen ? greenTheme.label : 'text-sm font-medium text-text-primary'
            }
          >
            {control.label}
          </span>
          <div
            className={cn(
              'flex flex-wrap',
              isGreen ? 'grid grid-cols-2 gap-1.5 sm:grid-cols-4' : 'gap-2',
            )}
          >
            {control.options.map((option) =>
              isGreen ? (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => onChange(control.key, option.value)}
                  className={cn(
                    'rounded-xl px-2 py-2 text-[10px] font-semibold transition',
                    value === option.value
                      ? greenTheme.optionActive
                      : greenTheme.optionInactive,
                  )}
                >
                  {option.label}
                </button>
              ) : (
                <Pill
                  key={option.value}
                  active={value === option.value}
                  onClick={() => onChange(control.key, option.value)}
                >
                  {option.label}
                </Pill>
              ),
            )}
          </div>
        </div>
      )

    case 'level': {
      const levelIndex =
        typeof value === 'number' ? control.levels.indexOf(value) : -1
      const activeBars = levelIndex >= 0 ? levelIndex + 1 : 0

      return (
        <div
          className={cn(
            'flex flex-col',
            isGreen ? greenTheme.stackGap : 'gap-2',
          )}
        >
          <span
            className={
              isGreen ? greenTheme.label : 'text-sm font-medium text-text-primary'
            }
          >
            {control.label}
          </span>
          {isGreen ? (
            <div className="flex items-center gap-2">
              <div className="flex flex-1 items-end gap-1">
                {control.levels.map((level, index) => (
                  <button
                    key={level}
                    type="button"
                    onClick={() => onChange(control.key, level)}
                    className={cn(
                      'h-4 flex-1 rounded-xs transition',
                      index < activeBars
                        ? greenTheme.levelBarActive
                        : greenTheme.levelBarInactive,
                    )}
                    aria-label={control.labels[index]}
                  />
                ))}
              </div>
              <span className={greenTheme.value}>
                {levelIndex >= 0 ? control.labels[levelIndex] : '—'}
              </span>
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {control.levels.map((level, index) => (
                <button
                  key={level}
                  type="button"
                  onClick={() => onChange(control.key, level)}
                  className={cn(
                    'min-w-10 rounded-lg border px-3 py-2 text-sm font-semibold transition-colors',
                    value === level
                      ? 'border-homemind bg-homemind text-homemind-fg'
                      : 'border-sidebar-border bg-elevated text-text-primary hover:border-homemind/40',
                  )}
                >
                  {control.labels[index]}
                </button>
              ))}
            </div>
          )}
        </div>
      )
    }

    case 'action':
      return isGreen ? (
        <button
          type="button"
          className={cn(
            'inline-flex h-8 items-center justify-center rounded-lg px-4 text-[10px] font-semibold transition',
            control.variant === 'danger'
              ? 'border border-danger/30 bg-elevated text-danger hover:bg-danger-light'
              : greenTheme.actionPrimary,
          )}
          onClick={() => onAction(control.key, control.sensitive)}
        >
          {control.label}
        </button>
      ) : (
        <Button
          variant={control.variant === 'danger' ? 'danger' : 'primary'}
          className="w-full"
          onClick={() => onAction(control.key, control.sensitive)}
        >
          {control.label}
        </Button>
      )
  }
}
