import { useEffect, useState } from 'react'
import { createSchedule, deleteSchedule, fetchSchedules, updateSchedule, type Schedule, type ScheduleWrite } from '@/api/schedules'
import { fetchScenes, type Scene } from '@/api/scenes'
import { TabletScreen } from '@/components/layout/TabletScreen'
import { useDevices } from '@/context/DevicesContext'
import { useSession } from '@/context/SessionContext'
import { useToast } from '@/context/ToastContext'

const DAYS = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']
const emptyForm: ScheduleWrite = { name: '', schedule_type: 'recurring', target_type: 'device_action', action: 'turn_on', recurrence_rule: { frequency: 'daily', time: '07:00', days_of_week: [] }, enabled: true }

function whenLabel(schedule: Schedule): string {
  if (schedule.schedule_type === 'once') return schedule.run_at ? new Date(schedule.run_at).toLocaleString('vi-VN') : '—'
  const rule = schedule.recurrence_rule
  if (!rule) return '—'
  const days = rule.frequency === 'daily' ? 'Hằng ngày' : rule.days_of_week.map((day) => DAYS[day]).join(', ')
  return `${rule.time} · ${days}`
}

export function ScheduleScreen() {
  const { devices } = useDevices()
  const { isAdmin } = useSession()
  const { showToast } = useToast()
  const [items, setItems] = useState<Schedule[]>([])
  const [scenes, setScenes] = useState<Scene[]>([])
  const [form, setForm] = useState<ScheduleWrite>(emptyForm)
  const [editing, setEditing] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)

  const load = async () => {
    const [schedules, sceneItems] = await Promise.all([fetchSchedules(), fetchScenes()])
    setItems(schedules); setScenes(sceneItems)
  }
  // eslint-disable-next-line react-hooks/set-state-in-effect -- initial API fetch
  useEffect(() => { void load().catch((e: unknown) => showToast(e instanceof Error ? e.message : 'Không tải được lịch', 'error'))
    const onExecuted = () => void load()
    window.addEventListener('schedule.executed', onExecuted)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- initial API fetch
    return () => window.removeEventListener('schedule.executed', onExecuted)
  }, [])

  const save = async () => {
    try {
      const payload = { ...form }
      if (payload.schedule_type === 'once') payload.recurrence_rule = null
      else payload.run_at = null
      if (payload.target_type === 'scene') { payload.device_id = null; payload.action = null }
      else payload.scene_id = null
      if (editing) await updateSchedule(editing, payload); else await createSchedule(payload)
      await load(); setShowForm(false); setEditing(null); showToast('Đã lưu lịch tự động', 'success')
    } catch (e) { showToast(e instanceof Error ? e.message : 'Không lưu được lịch', 'error') }
  }
  const edit = (item: Schedule) => {
    setEditing(item.id); setForm({ name:item.name,schedule_type:item.schedule_type,target_type:item.target_type,device_id:item.device_id,action:item.action,parameters:item.parameters,scene_id:item.scene_id,timezone:item.timezone,run_at:item.run_at?.slice(0,16),recurrence_rule:item.recurrence_rule,enabled:item.enabled }); setShowForm(true)
  }

  return <TabletScreen>
    <div className="flex h-full min-h-0 flex-col gap-2.5">
      <div className="flex items-center justify-between"><div><h2 className="font-display text-base font-bold">Lịch tự động</h2><p className="text-[10px] text-[#718076]">Lệnh một lần, lịch lặp và lịch chạy kịch bản</p></div>{isAdmin && <button onClick={() => { setForm(emptyForm); setEditing(null); setShowForm(true) }} className="rounded-lg bg-[#1E4D38] px-3 py-1.5 text-[10px] font-bold text-white">+ Thêm lịch</button>}</div>
      {showForm && <div className="grid shrink-0 grid-cols-2 gap-2 rounded-2xl border border-[#D5E5D8] bg-white p-3 text-[10px] lg:grid-cols-4">
        <input value={form.name} onChange={e=>setForm(f=>({...f,name:e.target.value}))} placeholder="Tên lịch" className="rounded-lg border p-2" />
        <select value={form.schedule_type} onChange={e=>setForm(f=>({...f,schedule_type:e.target.value as ScheduleWrite['schedule_type']}))} className="rounded-lg border p-2"><option value="once">Một lần</option><option value="recurring">Lặp lại</option></select>
        <select value={form.target_type} onChange={e=>setForm(f=>({...f,target_type:e.target.value as ScheduleWrite['target_type']}))} className="rounded-lg border p-2"><option value="device_action">Thiết bị</option><option value="scene">Kịch bản</option></select>
        {form.target_type === 'device_action' ? <><select value={form.device_id ?? ''} onChange={e=>setForm(f=>({...f,device_id:e.target.value}))} className="rounded-lg border p-2"><option value="">Chọn thiết bị</option>{devices.map(d=><option key={d.id} value={d.id}>{d.name}</option>)}</select><select value={form.action ?? 'turn_on'} onChange={e=>setForm(f=>({...f,action:e.target.value}))} className="rounded-lg border p-2"><option value="turn_on">Bật</option><option value="turn_off">Tắt</option></select></> : <select value={form.scene_id ?? ''} onChange={e=>setForm(f=>({...f,scene_id:e.target.value}))} className="rounded-lg border p-2"><option value="">Chọn kịch bản</option>{scenes.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select>}
        {form.schedule_type === 'once' ? <input type="datetime-local" value={form.run_at ?? ''} onChange={e=>setForm(f=>({...f,run_at:e.target.value}))} className="rounded-lg border p-2" /> : <><input type="time" value={form.recurrence_rule?.time ?? '07:00'} onChange={e=>setForm(f=>({...f,recurrence_rule:{...(f.recurrence_rule ?? {frequency:'daily',days_of_week:[]}),time:e.target.value}}))} className="rounded-lg border p-2" /><select value={form.recurrence_rule?.frequency ?? 'daily'} onChange={e=>setForm(f=>({...f,recurrence_rule:{...(f.recurrence_rule ?? {time:'07:00',days_of_week:[]}),frequency:e.target.value as 'daily'|'weekly'}}))} className="rounded-lg border p-2"><option value="daily">Hằng ngày</option><option value="weekly">Theo tuần</option></select>{form.recurrence_rule?.frequency === 'weekly' && <div className="col-span-2 flex flex-wrap gap-1 lg:col-span-4">{DAYS.map((day,index)=><button type="button" key={day} onClick={()=>setForm(f=>{const rule=f.recurrence_rule ?? {frequency:'weekly' as const,time:'07:00',days_of_week:[]};const selected=rule.days_of_week.includes(index);return {...f,recurrence_rule:{...rule,days_of_week:selected?rule.days_of_week.filter(d=>d!==index):[...rule.days_of_week,index]}}})} className={`rounded-md px-2 py-1 ${form.recurrence_rule?.days_of_week.includes(index)?'bg-[#1E4D38] text-white':'bg-[#EEF3EC]'}`}>{day}</button>)}</div>}</>}
        <div className="col-span-2 flex justify-end gap-2 lg:col-span-4"><button onClick={()=>setShowForm(false)} className="px-3 py-1.5">Hủy</button><button disabled={!form.name || (form.target_type==='device_action'?!form.device_id:!form.scene_id) || (form.schedule_type==='once'&&!form.run_at) || (form.recurrence_rule?.frequency==='weekly'&&!form.recurrence_rule.days_of_week.length)} onClick={()=>void save()} className="rounded-lg bg-[#1E4D38] px-3 py-1.5 font-bold text-white disabled:opacity-50">Lưu</button></div>
      </div>}
      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto">{items.length === 0 ? <p className="rounded-2xl border bg-white p-6 text-center text-[#718076]">Chưa có lịch tự động.</p> : items.map(item=><div key={item.id} className="flex items-center justify-between rounded-2xl border border-[#E6ECE3] bg-white p-3"><div><p className="font-bold">{item.name}</p><p className="text-[10px] text-[#718076]">{item.scene_name ?? item.device_name} · {whenLabel(item)}</p><p className="text-[9px] text-[#88968E]">Lần tới: {item.next_run_at ? new Date(item.next_run_at).toLocaleString('vi-VN') : '—'}</p></div><div className="flex gap-1">{isAdmin && <><button onClick={()=>void updateSchedule(item.id,{enabled:!item.enabled}).then(load)} className={`rounded-lg px-2 py-1 text-[9px] font-bold ${item.enabled?'bg-[#E8F5EB] text-[#2E7D32]':'bg-gray-100 text-gray-500'}`}>{item.enabled?'Đang bật':'Đã tắt'}</button><button onClick={()=>edit(item)} className="rounded-lg border px-2 py-1 text-[9px]">Sửa</button><button onClick={()=>window.confirm(`Xóa “${item.name}”?`)&&void deleteSchedule(item.id).then(load)} className="rounded-lg border border-red-200 px-2 py-1 text-[9px] text-red-600">Xóa</button></>}</div></div>)}</div>
    </div>
  </TabletScreen>
}
