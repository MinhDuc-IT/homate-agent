import { test, expect, type Page } from '@playwright/test'

test.use({ permissions: ['microphone'], launchOptions: { args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'] } })

const conversationId = '2d52fdd8-2762-49a8-914a-7ef82ece3207'
const planId = 'c10a897b-36fa-43fc-8f23-6b37d9b54512'
const replacementId = '687b132d-c88f-4a6f-884c-7bc34197c30a'
const action = (id = planId, version = 2) => ({
  id, kind: 'plan', tool: 'execute_plan', plan_version: version, conversation_id: conversationId,
  summary: 'Kế hoạch đèn và quạt', status: 'pending', expires_at: new Date(Date.now() + 120_000).toISOString(),
  arguments: { review: ['1. Tắt đèn phòng khách', '2. Bật quạt phòng ngủ'] },
  steps: [{ ordinal: 0, summary: 'Tắt đèn phòng khách', status: 'pending' },
    { ordinal: 1, summary: 'Bật quạt phòng ngủ', status: 'pending' }],
})

async function login(page: Page) {
  await page.goto('/login')
  await page.getByRole('button', { name: /Minh Đức/ }).click()
  await page.getByPlaceholder('••••').fill('1234')
  await page.getByRole('button', { name: /Đăng nhập vào không gian sống/ }).click()
  await expect(page).toHaveURL(/dashboard/)
  await page.getByRole('navigation').getByRole('link', { name: 'Trợ lý', exact: true }).click()
}

async function send(page: Page, text: string) {
  await page.getByRole('textbox', { name: 'Tin nhắn cho HomeMate' }).fill(text)
  await page.getByRole('button', { name: 'Gửi', exact: true }).click()
}

test('refresh after chat 401 retries the identical request body and request_id', async ({ page }) => {
  const bodies: Record<string, unknown>[] = []
  await page.route('**/api/ai/chat', async route => {
    bodies.push(route.request().postDataJSON())
    if (bodies.length === 1) {
      await route.fulfill({ status: 401, json: { detail: 'Access expired during tool call' } })
      return
    }
    await route.fulfill({ json: {
      reply: 'Đã nhận yêu cầu sau khi làm mới phiên.', trace: [], pending_actions: [],
      conversation_id: conversationId, conversation_version: 1,
    } })
  })
  await login(page)
  await send(page, 'bật đèn và mở rèm phòng khách')
  await expect(page.getByText('Đã nhận yêu cầu sau khi làm mới phiên.', { exact: true })).toBeVisible()
  expect(bodies).toHaveLength(2)
  expect(bodies[1]).toEqual(bodies[0])
  expect(bodies[0].request_id).toEqual(expect.any(String))
})

test('interrupted plan requires manual acknowledgement before closing', async ({ page }) => {
  const interrupted = { ...action(), status: 'executing', recovery_required: true,
    steps: [{ ordinal: 0, summary: 'Tắt đèn phòng khách', status: 'running' }] }
  await page.route('**/api/ai/chat', route => route.fulfill({ json: {
    reply: 'Kiểm tra kế hoạch bị gián đoạn.', pending_actions: [interrupted], trace: [],
    conversation_id: conversationId, conversation_version: 1,
  } }))
  await page.route(`**/api/dashboard/agent/plans/${planId}/recover`, async route => {
    expect(route.request().postDataJSON()).toEqual({ version: 2, acknowledged: true })
    await route.fulfill({ json: { ...interrupted, status: 'failed', recovery_required: false,
      steps: [{ ordinal: 0, summary: 'Tắt đèn phòng khách', status: 'failed', result: { message: 'Kết quả chưa xác định.' } }] } })
  })
  await page.route(`**/api/ai/plans/${planId}/summary`, route => route.fulfill({ json: { reply: 'Đã đóng, không chạy lại thao tác.' } }))
  await login(page)
  await send(page, 'Kiểm tra kế hoạch')
  const close = page.getByRole('button', { name: 'Đóng kế hoạch gián đoạn' })
  await expect(close).toBeDisabled()
  await page.getByRole('checkbox', { name: /Tôi đã kiểm tra thiết bị/ }).check()
  await close.click()
  await expect(page.getByText('Đã đóng, không chạy lại thao tác.', { exact: true })).toBeVisible()
  await expect(close).toHaveCount(0)
})

test('clarification and correction send conversation versions and show partial execution', async ({ page }) => {
  let turn = 0
  await page.route('**/api/ai/chat', async route => {
    const request = route.request().postDataJSON()
    turn++
    if (turn === 1) {
      expect(request.conversation_id).toBeUndefined()
      await route.fulfill({ json: { reply: 'Bạn muốn tắt đèn phòng nào?', pending_actions: [], trace: [],
        conversation_id: conversationId, conversation_version: 1, dialogue_state: 'clarifying' } })
    } else {
      expect(request.conversation_id).toBe(conversationId)
      expect(request.conversation_version).toBe(turn - 1)
      await route.fulfill({ json: { reply: 'Vui lòng xác nhận kế hoạch.', pending_actions: [action(turn === 2 ? planId : replacementId, turn)],
        trace: [], conversation_id: conversationId, conversation_version: turn,
        invalidated_plan_ids: turn === 3 ? [planId] : [], invalidated_status: 'superseded' } })
    }
  })
  await page.route(`**/api/dashboard/agent/plans/${replacementId}/decision`, async route => {
    expect(route.request().postDataJSON()).toEqual({ approved: true, version: 3 })
    await route.fulfill({ json: { ...action(replacementId, 3), status: 'failed', steps: [
      { ordinal: 0, summary: 'Tắt đèn phòng khách', status: 'succeeded' },
      { ordinal: 1, summary: 'Bật quạt phòng ngủ', status: 'failed', result: { message: 'Thiết bị chưa phản hồi.' } },
      { ordinal: 2, summary: 'Đóng rèm', status: 'skipped' },
    ] } })
  })
  await page.route(`**/api/ai/plans/${replacementId}/summary`, route => route.fulfill({ json: { reply: 'Đèn đã tắt; quạt chưa thực hiện được và rèm bị bỏ qua.' } }))
  await login(page)
  await send(page, 'Tắt đèn rồi bật quạt')
  await expect(page.getByText('Bạn muốn tắt đèn phòng nào?', { exact: true })).toBeVisible()
  await send(page, 'Phòng khách')
  await expect(page.getByText(/Kế hoạch phiên bản 2/)).toBeVisible()
  await send(page, 'Sửa kế hoạch')
  await expect(page.getByText('Đã thay bằng kế hoạch mới', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Xác nhận', exact: true })).toHaveCount(1)
  await page.getByRole('button', { name: 'Xác nhận', exact: true }).click()
  await expect(page.getByText('Đèn đã tắt; quạt chưa thực hiện được và rèm bị bỏ qua.', { exact: true })).toBeVisible()
  const steps = page.getByRole('list', { name: 'Kết quả từng bước' }).last()
  await expect(steps).toContainText('Thành công')
  await expect(steps).toContainText('Thiết bị chưa phản hồi.')
  await expect(steps).toContainText('Đã bỏ qua')
})

test('reload restores server conversation and new chat cancels the previous plan', async ({ page }) => {
  let deleted = false
  await page.route(`**/api/dashboard/agent/conversations/${conversationId}`, async route => {
    if (route.request().method() === 'DELETE') {
      deleted = true
      await route.fulfill({ json: { status: 'cancelled' } })
    } else await route.fulfill({ json: { id: conversationId, version: 2, status: 'pending', expired: false,
      messages: [{ role: 'user', content: 'Tắt đèn' }, { role: 'assistant', content: 'Kế hoạch đã lưu.' }], plan: action() } })
  })
  await page.route('**/api/ai/chat', route => route.fulfill({ json: {
    reply: 'Kế hoạch đã lưu.', conversation_id: conversationId, conversation_version: 2, pending_actions: [action()], trace: [],
  } }))
  await login(page)
  await send(page, 'Tắt đèn')
  await expect(page.getByText(/Kế hoạch phiên bản 2/)).toBeVisible()
  await page.reload()
  await expect(page.getByText('Kế hoạch đã lưu.', { exact: true })).toBeVisible()
  await expect(page.getByText(/Kế hoạch phiên bản 2/)).toBeVisible()
  await page.getByRole('button', { name: 'Cuộc trò chuyện mới', exact: true }).click()
  await page.getByRole('button', { name: 'Bắt đầu mới', exact: true }).click()
  await expect.poll(() => deleted).toBe(true)
  await expect(page.getByText('Kế hoạch đã lưu.', { exact: true })).toHaveCount(0)
  expect(await page.evaluate(() => localStorage.getItem('homate.agent.minh-duc.chat'))).toBeNull()
})

test.describe('Aura workflow', () => {
  test('voice follow-up keeps its own conversation and confirms a plan version', async ({ page }) => {
    let turn = 0
    let spoken = 0
    await page.route('**/api/ai/speech/transcribe', route => route.fulfill({ json: { text: turn === 0 ? 'Tắt đèn' : 'Phòng khách' } }))
    const wav = Buffer.alloc(32044)
    wav.write('RIFF'); wav.writeUInt32LE(wav.length - 8, 4); wav.write('WAVEfmt ', 8)
    wav.writeUInt32LE(16, 16); wav.writeUInt16LE(1, 20); wav.writeUInt16LE(1, 22)
    wav.writeUInt32LE(16000, 24); wav.writeUInt32LE(32000, 28); wav.writeUInt16LE(2, 32); wav.writeUInt16LE(16, 34)
    wav.write('data', 36); wav.writeUInt32LE(32000, 40)
    await page.route('**/api/ai/speech/synthesize', route => { spoken++; return route.fulfill({ contentType: 'audio/wav', body: wav }) })
    await page.route('**/api/ai/chat', async route => {
      const request = route.request().postDataJSON()
      turn++
      if (turn === 2) {
        expect(request.conversation_id).toBe(conversationId)
        expect(request.conversation_version).toBe(1)
      }
      await route.fulfill({ json: { reply: turn === 1 ? 'Bạn muốn chọn phòng nào?' : 'Vui lòng xác nhận kế hoạch.',
        conversation_id: conversationId, conversation_version: turn, trace: [], pending_actions: turn === 1 ? [] : [action()] } })
    })
    await page.route(`**/api/dashboard/agent/plans/${planId}/decision`, async route => {
      expect(route.request().postDataJSON()).toEqual({ approved: true, version: 2 })
      await route.fulfill({ json: { ...action(), status: 'executed', steps: action().steps.map(step => ({ ...step, status: 'succeeded' })) } })
    })
    await page.route(`**/api/ai/plans/${planId}/summary`, route => route.fulfill({ json: { reply: 'Đã thực hiện kế hoạch.' } }))
    await login(page)
    for (let index = 0; index < 2; index++) {
      const start = page.getByRole('button', { name: 'Bắt đầu nói với HomeMate' })
      await expect(start).toBeEnabled()
      await start.click()
      await page.getByRole('button', { name: 'Dừng và gửi lệnh giọng nói' }).click()
      await expect.poll(() => turn).toBe(index + 1)
      await expect.poll(() => spoken).toBeGreaterThanOrEqual(index + 1)
    }
    const panel = page.getByRole('region', { name: 'Hội thoại giọng nói' })
    await expect(panel).toContainText('Phòng khách')
    await panel.getByRole('button', { name: 'Xác nhận', exact: true }).click()
    await expect(panel).toContainText('Đã thực hiện kế hoạch.')
    expect(await page.evaluate(() => localStorage.getItem('homate.agent.minh-duc.chat'))).toBeNull()
    expect(await page.evaluate(() => localStorage.getItem('homate.agent.minh-duc.voice'))).toBe(conversationId)
  })
})
