import { test, expect } from '@playwright/test'

test.use({ permissions: ['microphone'], launchOptions: { args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'] } })

test('header Aura sends speech to agent and automatically plays the reply', async ({ page }) => {
  let chats = 0
  let decisions = 0
  const action = { id: 'voice-action', tool: 'control_device', summary: 'Tắt đèn phòng khách', status: 'pending', arguments: {}, expires_at: new Date(Date.now() + 120_000).toISOString() }
  await page.route('**/api/dashboard/agent/actions/voice-action/decision', async route => {
    expect(route.request().postDataJSON().approved).toBe(true)
    decisions++
    await route.fulfill({ json: { ...action, status: 'executed' } })
  })
  await page.route('**/api/ai/chat', async route => {
    chats++
    await route.fulfill({ json: { reply: 'Xin chào bạn.', pending_actions: [action], trace: [] } })
  })
  await page.route('**/api/ai/speech/transcribe', async route => {
    const request = route.request()
    expect(request.headers().authorization).toMatch(/^Bearer /)
    expect(request.headers()['content-type']).toBe('audio/wav')
    expect(request.postDataBuffer()?.subarray(0, 4).toString()).toBe('RIFF')
    await route.fulfill({ json: { text: 'Tắt đèn phòng khách' } })
  })
  const wav = Buffer.alloc(32044)
  wav.write('RIFF'); wav.writeUInt32LE(wav.length - 8, 4); wav.write('WAVEfmt ', 8)
  wav.writeUInt32LE(16, 16); wav.writeUInt16LE(1, 20); wav.writeUInt16LE(1, 22)
  wav.writeUInt32LE(16000, 24); wav.writeUInt32LE(32000, 28); wav.writeUInt16LE(2, 32); wav.writeUInt16LE(16, 34)
  wav.write('data', 36); wav.writeUInt32LE(32000, 40)
  await page.route('**/api/ai/speech/synthesize', async route => {
    expect(route.request().headers().authorization).toMatch(/^Bearer /)
    expect(route.request().postDataJSON().text).toMatch(/Xin chào bạn|Tắt đèn phòng khách/)
    await route.fulfill({ contentType: 'audio/wav', body: wav })
  })
  await page.goto('/login')
  await page.getByRole('button', { name: /Minh Đức/ }).click()
  await page.getByPlaceholder('••••').fill('1234')
  await page.getByRole('button', { name: /Đăng nhập vào không gian sống/ }).click()
  await expect(page).toHaveURL(/dashboard/)
  await page.getByRole('navigation').getByRole('link', { name: 'Trợ lý', exact: true }).click()
  const speech = page.waitForResponse('**/api/ai/speech/synthesize')
  await page.getByRole('button', { name: 'Bắt đầu nói với HomeMate' }).click()
  await page.getByRole('button', { name: 'Dừng và gửi lệnh giọng nói' }).click()
  expect((await speech).ok()).toBeTruthy()
  expect(chats).toBe(1)
  await expect(page.getByRole('region', { name: 'Hội thoại giọng nói' })).toContainText('Tắt đèn phòng khách')
  await expect(page.getByRole('region', { name: 'Hội thoại giọng nói' })).toContainText('Xin chào bạn.')
  await expect(page.getByLabel('Tin nhắn cho HomeMate')).toHaveValue('')
  await expect(page.getByRole('log', { name: 'Cuộc trò chuyện với HomeMate' })).not.toContainText('Xin chào bạn.')
  await expect(page.locator('header').getByRole('log', { name: 'Nội dung giọng nói' })).toContainText('Xin chào bạn.')
  await expect(page.getByRole('button', { name: 'Đóng hội thoại giọng nói' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Nghe phản hồi' })).toHaveCount(0)
  expect(decisions).toBe(0)
  const panel = page.getByRole('region', { name: 'Hội thoại giọng nói' })
  await panel.getByRole('button', { name: 'Xác nhận', exact: true }).click()
  await expect(panel).toContainText('Đã thực thi')
  expect(decisions).toBe(1)
})
