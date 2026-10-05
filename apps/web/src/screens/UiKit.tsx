import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Card } from '@/components/ui/Card'
import { Checkbox } from '@/components/ui/Checkbox'
import { FormField } from '@/components/ui/FormField'
import { FormGrid } from '@/components/ui/FormGrid'
import { Input } from '@/components/ui/Input'
import {
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
} from '@/components/ui/Modal'
import { PageHeader } from '@/components/ui/PageHeader'
import { Pill } from '@/components/ui/Pill'
import { ProgressBar } from '@/components/ui/ProgressBar'
import { SearchInput } from '@/components/ui/SearchInput'
import { SectionTitle } from '@/components/ui/SectionTitle'
import { Select } from '@/components/ui/Select'
import { Tab, TabList, TabPanel, Tabs } from '@/components/ui/Tabs'
import { useToast } from '@/context/ToastContext'
import { trackLoading } from '@/utils/loadingTracker'

export function UiKit() {
  const { showToast } = useToast()
  const [tab, setTab] = useState('controls')
  const [modalOpen, setModalOpen] = useState(false)
  const [room, setRoom] = useState('all')

  return (
    <div>
      <PageHeader
        title="UI Kit"
        description="Các component base theo phong cách template — dùng để tham chiếu khi build trang."
        actions={
          <Button
            variant="outline"
            onClick={() => {
              void trackLoading(
                new Promise((resolve) => {
                  window.setTimeout(resolve, 1200)
                }),
              )
              showToast('Đã kích hoạt loading bar + toast', 'info')
            }}
          >
            Demo toast / loading
          </Button>
        }
      />

      <Tabs value={tab} onChange={setTab}>
        <TabList>
          <Tab value="controls">Controls</Tab>
          <Tab value="feedback">Feedback</Tab>
          <Tab value="layout">Layout</Tab>
        </TabList>

        <TabPanel value="controls">
          <Card>
            <SectionTitle className="mt-0">Buttons & badges</SectionTitle>
            <div className="mb-4 flex flex-wrap gap-2">
              <Button>Primary</Button>
              <Button variant="outline">Outline</Button>
              <Button variant="ghost">Ghost</Button>
              <Button variant="danger">Danger</Button>
              <Button loading>Loading</Button>
            </div>
            <div className="mb-6 flex flex-wrap gap-2">
              <Badge variant="success">Hoàn thành</Badge>
              <Badge variant="warning">Cần xác nhận</Badge>
              <Badge variant="pending">Đang xử lý</Badge>
              <Badge variant="error">Lỗi</Badge>
              <Badge variant="neutral">Thành viên</Badge>
            </div>

            <SectionTitle>Form</SectionTitle>
            <FormGrid columns={2}>
              <FormField label="Tên thành viên" required>
                <Input placeholder="Đức" />
              </FormField>
              <FormField label="Vai trò" hint="Admin hoặc thành viên">
                <Select defaultValue="member">
                  <option value="member">Thành viên</option>
                  <option value="admin">Quản trị</option>
                </Select>
              </FormField>
              <FormField label="Tìm thiết bị">
                <SearchInput placeholder="Đèn, điều hòa…" />
              </FormField>
              <FormField label="Ghi nhớ">
                <label className="flex h-10 items-center gap-2 text-sm text-text-secondary">
                  <Checkbox defaultChecked />
                  Lưu phiên đăng nhập
                </label>
              </FormField>
            </FormGrid>
          </Card>
        </TabPanel>

        <TabPanel value="feedback">
          <Card>
            <SectionTitle className="mt-0">Progress & pills</SectionTitle>
            <ProgressBar value={62} color="homemind" showLabel className="mb-4 max-w-md" />
            <div className="mb-6 flex flex-wrap gap-2">
              {(['all', 'living', 'bed', 'kitchen'] as const).map((id) => (
                <Pill key={id} active={room === id} onClick={() => setRoom(id)}>
                  {id === 'all'
                    ? 'Tất cả'
                    : id === 'living'
                      ? 'Phòng khách'
                      : id === 'bed'
                        ? 'Phòng ngủ'
                        : 'Bếp'}
                </Pill>
              ))}
            </div>

            <SectionTitle>Modal</SectionTitle>
            <Button onClick={() => setModalOpen(true)}>Mở modal HITL mẫu</Button>
            <Modal open={modalOpen} onClose={() => setModalOpen(false)} maxWidth="md">
              <ModalHeader title="Cần xác nhận" onClose={() => setModalOpen(false)} />
              <ModalBody>
                <p className="text-sm text-text-secondary">
                  Mở khóa cửa chính? Yêu cầu sẽ hết hạn sau 30 giây nếu không phản hồi.
                </p>
                <ProgressBar value={60} color="error" className="mt-4" />
              </ModalBody>
              <ModalFooter>
                <Button variant="outline" onClick={() => setModalOpen(false)}>
                  Hủy
                </Button>
                <Button
                  variant="danger"
                  onClick={() => {
                    setModalOpen(false)
                    showToast('Đã xác nhận mở khóa', 'success')
                  }}
                >
                  Đồng ý
                </Button>
              </ModalFooter>
            </Modal>
          </Card>
        </TabPanel>

        <TabPanel value="layout">
          <div className="grid gap-4 sm:grid-cols-3">
            {['Đèn phòng khách', 'Điều hòa', 'Cửa chính'].map((name) => (
              <Card key={name} padding="sm">
                <p className="text-sm font-semibold text-text-primary">{name}</p>
                <p className="mt-1 text-xs text-text-muted">Trạng thái mẫu · Card component</p>
              </Card>
            ))}
          </div>
        </TabPanel>
      </Tabs>
    </div>
  )
}
