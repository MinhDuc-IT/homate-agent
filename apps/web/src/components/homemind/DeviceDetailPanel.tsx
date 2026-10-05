import type { ReactNode } from 'react'
import {
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
} from '@/components/ui/Modal'
import { Button } from '@/components/ui/Button'
import { DeviceControlList } from '@/components/homemind/DeviceControlList'
import { Badge } from '@/components/ui/Badge'
import { useSession } from '@/context/SessionContext'
import type { Device, DeviceStateValue } from '@/types/device'
import { formatDeviceStatus, isDeviceActive, visibleControls } from '@/utils/deviceStatus'

interface DeviceDetailPanelProps {
  device: Device | null
  open: boolean
  onClose: () => void
  onChange: (deviceId: string, key: string, value: DeviceStateValue) => void
  onAction: (device: Device, key: string, sensitive?: boolean) => void
  icon: ReactNode
}

export function DeviceDetailPanel({
  device,
  open,
  onClose,
  onChange,
  onAction,
  icon,
}: DeviceDetailPanelProps) {
  const { rooms } = useSession()
  if (!device) return null

  const roomLabel = rooms.find((r) => r.id === device.room)?.label ?? device.room
  const active = isDeviceActive(device)
  const controls = visibleControls(device)

  return (
    <Modal open={open} onClose={onClose} maxWidth="sm">
      <ModalHeader onClose={onClose}>
        <div className="flex min-w-0 items-center gap-3 pr-2">
          <span
            className={
              active ? 'text-homemind' : 'text-text-secondary'
            }
          >
            {icon}
          </span>
          <div className="min-w-0">
            <h2 className="truncate text-base font-semibold text-text-primary">{device.name}</h2>
            <p className="text-xs text-text-muted">{roomLabel}</p>
          </div>
        </div>
      </ModalHeader>
      <ModalBody>
        <div className="mb-4 flex items-center justify-between gap-2">
          <p className="text-sm text-text-secondary">{formatDeviceStatus(device)}</p>
          <Badge variant={active ? 'success' : 'neutral'} showDot={false}>
            {active ? 'Hoạt động' : 'Tắt / chờ'}
          </Badge>
        </div>
        {controls.length > 0 ? (
          <DeviceControlList
            device={device}
            controls={controls}
            onChange={(key, value) => onChange(device.id, key, value)}
            onAction={(key, sensitive) => onAction(device, key, sensitive)}
          />
        ) : (
          <p className="text-sm text-text-muted">Thiết bị không có điều khiển trực tiếp.</p>
        )}
      </ModalBody>
      <ModalFooter>
        <Button variant="outline" onClick={onClose}>
          Đóng
        </Button>
      </ModalFooter>
    </Modal>
  )
}
