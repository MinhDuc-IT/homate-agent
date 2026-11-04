import { test, expect } from '@playwright/test'

async function login(page: import('@playwright/test').Page) {
  await page.goto('/login')
  await page.getByRole('button', { name: /Minh Đức/ }).click()
  await page.getByPlaceholder('••••').fill('1234')
  await page.getByRole('button', { name: /Đăng nhập vào không gian sống/ }).click()
  await expect(page).toHaveURL(/dashboard/)
  await page.getByRole('navigation').getByRole('link', { name: 'Trợ lý', exact: true }).click()
}

test('chat proposal requires a decision and persists device control', async ({ page }) => {
  let token = ''
  let original = false
  await page.route('**/api/ai/chat', async route => {
    token = route.request().headers().authorization
    const headers = { Authorization: token }
    const device = await page.request.get('http://127.0.0.1:8000/api/dashboard/devices/light-living', { headers })
    original = device.ok() && (await device.json()).state.power
    const proposal = await page.request.post('http://127.0.0.1:8000/api/dashboard/agent/tools', {
      headers, data: { request_id: crypto.randomUUID(), tool: 'control_device', arguments: {
        device_id: 'light-living', action: original ? 'turn_off' : 'turn_on', parameters: {},
      } },
    })
    expect(proposal.status()).toBe(200)
    await route.fulfill({ json: { reply: 'Vui lòng xác nhận thao tác.', pending_actions: [await proposal.json()], trace: [] } })
  })
  await login(page)
  await page.getByRole('textbox', { name: 'Tin nhắn cho HomeMate' }).fill('Đổi trạng thái đèn phòng khách')
  await page.getByRole('button', { name: 'Gửi', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Xác nhận', exact: true })).toBeVisible()
  const headers = { Authorization: token }
  const before = await page.request.get('http://127.0.0.1:8000/api/dashboard/devices/light-living', { headers })
  expect((await before.json()).state.power).toBe(original)
  await page.getByRole('button', { name: 'Xác nhận', exact: true }).click()
  await expect(page.getByText('Đã thực thi', { exact: true })).toBeVisible()
  const after = await page.request.get('http://127.0.0.1:8000/api/dashboard/devices/light-living', { headers })
  expect((await after.json()).state.power).toBe(!original)
  await page.request.post('http://127.0.0.1:8000/api/dashboard/devices/light-living/actions', { headers, data: { key: 'power', value: original } })
})

test('chat reports provider failures and keeps the message for retry', async ({ page }) => {
  await page.route('**/api/ai/chat', route => route.fulfill({ status: 503, json: { detail: 'Chưa cấu hình API key cho LLM.' } }))
  await login(page)
  const input = page.getByRole('textbox', { name: 'Tin nhắn cho HomeMate' })
  await input.fill('Thiết bị nào đang bật?')
  await page.getByRole('button', { name: 'Gửi', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Chưa cấu hình API key')
  await expect(input).toHaveValue('Thiết bị nào đang bật?')
})

test('chat suggestions, immediate messages, multiline input and new conversation', async ({ page }) => {
  let release!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/ai/chat', async route => {
    await gate
    await route.fulfill({ json: { reply: 'Đang bật: **Đèn phòng khách**.\n\n1. Độ sáng: 60%\n2. Trạng thái: bật', pending_actions: [], trace: [] } })
  })
  await login(page)
  const input = page.getByRole('textbox', { name: 'Tin nhắn cho HomeMate' })
  await page.getByRole('button', { name: /Kiểm tra thiết bị/ }).click()
  await expect(input).toBeFocused()
  await expect(input).toHaveValue('Những thiết bị nào đang bật?')
  await input.press('Shift+Enter')
  await input.press('x')
  await expect(input).toHaveValue('Những thiết bị nào đang bật?\nx')
  await input.fill('Những thiết bị nào đang bật?')
  await input.press('Enter')
  await expect(page.getByRole('article', { name: 'Tin nhắn của bạn' })).toContainText('Những thiết bị nào đang bật?')
  await expect(page.getByRole('log').getByRole('status')).toContainText('HomeMate đang xử lý')
  await expect(input).toHaveValue('')
  await input.fill('Bản nháp tiếp theo')
  release()
  await expect(page.getByRole('article', { name: 'Tin nhắn của HomeMate' }).locator('strong')).toHaveText('Đèn phòng khách')
  await expect(input).toHaveValue('Bản nháp tiếp theo')
  await page.screenshot({ path: 'test-results/assistant-conversation.png', fullPage: true })
  await page.getByRole('button', { name: 'Cuộc trò chuyện mới', exact: true }).click()
  await page.getByRole('button', { name: 'Bắt đầu mới', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Hôm nay, tôi có thể giúp gì?' })).toBeVisible()
  await expect(input).toHaveValue('')
})

test('failed messages retry without duplicating the user message', async ({ page }) => {
  const requests: { request_id: string; history: unknown[] }[] = []
  await page.route('**/api/ai/chat', async route => {
    requests.push(route.request().postDataJSON())
    await route.fulfill(requests.length === 1 ? { status: 503, json: { detail: 'Lỗi kết nối thử nghiệm' } } : { json: { reply: 'Đã kết nối lại.', pending_actions: [], trace: [] } })
  })
  await login(page)
  await page.getByRole('textbox', { name: 'Tin nhắn cho HomeMate' }).fill('Xem các kịch bản')
  await page.getByRole('button', { name: 'Gửi', exact: true }).click()
  await expect(page.getByRole('alert')).toBeVisible()
  await page.getByRole('button', { name: 'Thử lại', exact: true }).click()
  await expect(page.getByRole('article', { name: 'Tin nhắn của HomeMate' })).toContainText('Đã kết nối lại.')
  await expect(page.getByRole('article', { name: 'Tin nhắn của bạn' })).toHaveCount(1)
  await expect(page.getByRole('alert')).toHaveCount(0)
  expect(requests[1].request_id).toBe(requests[0].request_id)
  expect(requests[1].history).toEqual([])
})

test('mobile composer stays visible and confirmation expires inline', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.route('**/api/ai/chat', route => route.fulfill({ json: {
    reply: 'Vui lòng xác nhận.', trace: [], pending_actions: [{
      id: 'expired-ui-test', summary: 'Đèn phòng khách: Tắt', tool: 'control_device',
      arguments: { review: ['Tắt đèn phòng khách'] }, expires_at: new Date(Date.now() - 1000).toISOString(), status: 'pending',
    }],
  } }))
  // Login helper uses desktop navigation; resize after authentication/navigation.
  await page.setViewportSize({ width: 1280, height: 720 })
  await login(page)
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.locator('aside')).not.toBeInViewport()
  await expect(page.getByText('Xin chào Minh Đức', { exact: true })).not.toBeVisible()
  await page.screenshot({ path: 'test-results/assistant-mobile-welcome.png', fullPage: true })
  const input = page.getByRole('textbox', { name: 'Tin nhắn cho HomeMate' })
  await input.fill('Tắt đèn phòng khách')
  await page.getByRole('button', { name: 'Gửi', exact: true }).click()
  const card = page.getByRole('region', { name: 'Thao tác: Đèn phòng khách: Tắt' })
  await expect(card).toContainText('Đã hết hạn')
  await expect(page.getByRole('button', { name: 'Xác nhận', exact: true })).toHaveCount(0)
  await expect(input).toBeInViewport()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({ path: 'test-results/assistant-mobile-confirmation.png', fullPage: true })
})
