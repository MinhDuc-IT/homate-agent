import { test, expect } from '@playwright/test'

test('selecting a model exposes real device controls and sends actions through the device API', async ({ page }) => {
  test.setTimeout(60000)
  let power = false
  const commands: unknown[] = []
  const device = () => ({ id: 'tv-living', name: 'TV phòng khách', room: 'living', kind: 'tv', state: { power },
    controls: [{ type: 'toggle', key: 'power', label: 'Nguồn' }] })
  await page.route('**/api/dashboard/devices', route => route.fulfill({ json: [device()] }))
  await page.routeWebSocket('**/ws/devices?*', socket => socket.send(JSON.stringify({ type: 'snapshot', devices: [device()] })))
  await page.route('**/api/dashboard/devices/tv-living/actions', route => {
    const body = route.request().postDataJSON()
    commands.push(body)
    power = body.value
    return route.fulfill({ json: { device: device(), changed_key: 'power', previous_value: !power, new_value: power } })
  })
  await page.route('**/unity/build-status.json', route => route.fulfill({ json: { ready: true, deviceSync: true, views: [],
    focusDevices: [{ id: 'tv-living', label: 'TV phòng khách' }] } }))
  await page.route('**/unity/index.html', route => route.fulfill({ contentType: 'text/html', body: `
    <button onclick="parent.postMessage({type:'homate:device-selected',deviceId:'tv-living'},location.origin)">Pick TV</button>
    <pre id="zoom"></pre><script>addEventListener('message', e => {
      if(e.data.type==='homate:request-ready') parent.postMessage({type:'homate:ready'},location.origin);
      if(e.data.type==='homate:zoom') document.querySelector('#zoom').textContent=e.data.direction;
    });</script>` }))
  await page.goto('/login')
  await page.getByRole('button', { name: /Minh Đức/ }).click()
  await page.getByPlaceholder('••••').fill('1234')
  await page.getByRole('button', { name: /Đăng nhập vào không gian sống/ }).click()
  await expect(page).toHaveURL(/dashboard/)
  await page.goto('/house-3d')
  const panel = page.getByRole('complementary', { name: 'Điều khiển thiết bị 3D' })
  await page.evaluate(() => window.postMessage({ type: 'homate:device-selected', deviceId: 'tv-living' }, location.origin))
  await expect(panel).toHaveCount(0)
  await page.frameLocator('iframe').getByRole('button', { name: 'Pick TV' }).click()
  await expect(panel.getByRole('heading', { name: 'TV phòng khách' })).toBeVisible()
  await panel.getByRole('button', { name: 'Nguồn', exact: true }).click()
  await expect.poll(() => commands.length).toBe(1)
  await expect(panel.locator('fieldset')).toHaveAttribute('aria-busy', 'false')
  expect(commands).toEqual([{ key: 'power', value: true }])
  await page.getByRole('button', { name: 'Phóng to', exact: true }).click()
  await expect(page.frameLocator('iframe').locator('#zoom')).toHaveText('in')
  await page.getByRole('button', { name: 'Thu nhỏ', exact: true }).click()
  await expect(page.frameLocator('iframe').locator('#zoom')).toHaveText('out')
  await page.getByRole('button', { name: 'Đóng điều khiển thiết bị' }).click()
  await expect(panel).toHaveCount(0)
})

test('3D screen handles a missing build and retries when a build is ready', async ({ page }) => {
  let ready = false
  await page.route('**/unity/build-status.json', route => ready
    ? route.fulfill({ json: { ready: true, deviceSync: false, views: [
      { id: 'overview', label: 'Toàn cảnh' }, { id: 'living', label: 'Phòng khách' },
    ] } })
    : route.fulfill({ status: 404, body: 'Not found' }))
  await page.route('**/unity/index.html', route => route.fulfill({ contentType: 'text/html', body: `<p>Preview fixture</p>
    <button onclick="parent.postMessage({type:'homate:ready'}, location.origin)">Initialize</button>
    <script>addEventListener('message', event => {
      if (event.data.type === 'homate:set-view') parent.postMessage({type:'homate:view-changed', viewId:event.data.viewId}, location.origin);
    });</script>` }))
  await page.goto('/login')
  await page.getByRole('button', { name: /Minh Đức/ }).click()
  await page.getByPlaceholder('••••').fill('1234')
  await page.getByRole('button', { name: /Đăng nhập vào không gian sống/ }).click()
  await expect(page).toHaveURL(/dashboard/)
  await page.getByRole('link', { name: 'Nhà 3D', exact: true }).click()
  await expect(page).toHaveURL(/house-3d/)
  await expect(page.getByRole('heading', { name: 'Mô hình 3D chưa sẵn sàng' })).toBeVisible()
  await expect(page.locator('iframe')).toHaveCount(0)
  ready = true
  await page.getByRole('button', { name: 'Kiểm tra lại' }).click()
  await expect(page.frameLocator('iframe[title="Mô hình nhà 3D"]').getByText('Preview fixture')).toBeVisible()
  const living = page.getByRole('button', { name: 'Phòng khách', exact: true })
  const overview = page.getByRole('button', { name: 'Toàn cảnh', exact: true })
  await expect(living).toBeDisabled()
  await page.frameLocator('iframe').getByRole('button', { name: 'Initialize' }).click()
  await expect(living).toBeEnabled()
  await living.click()
  await expect(living).toHaveAttribute('aria-pressed', 'true')
  // Messages from another window must not change the selected camera.
  await page.evaluate(() => window.postMessage({ type: 'homate:view-changed', viewId: 'overview' }, location.origin))
  await expect(living).toHaveAttribute('aria-pressed', 'true')
  await overview.click()
  await expect(overview).toHaveAttribute('aria-pressed', 'true')
})

test('Unity receives latest reported state on load, updates and reconnect', async ({ page }) => {
  test.setTimeout(60000)
  let power = false
  let position = 0
  let recording = false
  let volume = 35
  let speed = 0
  const devices = () => [
    { id: 'light-living', name: 'Light', room: 'living', kind: 'bulb', state: { power, brightness: 60 }, controls: [] },
    { id: 'curtain', name: 'Curtain', room: 'bed', kind: 'curtain', state: { position }, controls: [] },
    { id: 'cam-living', name: 'Camera', room: 'living', kind: 'camera', state: { recording }, controls: [] },
    { id: 'speaker-living', name: 'Speaker', room: 'living', kind: 'speaker', state: { power, volume }, controls: [] },
    { id: 'tv-living', name: 'TV', room: 'living', kind: 'tv', state: { power }, controls: [] },
    { id: 'fan-kitchen', name: 'Extractor', room: 'kitchen', kind: 'fan', state: { speed }, controls: [] },
    { id: 'ac-living', name: 'AC', room: 'living', kind: 'snowflake', state: { power: true }, controls: [] },
  ]
  let sendUpdate = () => {}
  let disconnect = () => {}
  await page.route('**/api/dashboard/devices', route => route.fulfill({ json: devices() }))
  await page.routeWebSocket('**/ws/devices?*', socket => {
    socket.send(JSON.stringify({ type: 'snapshot', devices: devices() }))
    sendUpdate = () => socket.send(JSON.stringify({ type: 'snapshot', devices: devices() }))
    disconnect = () => socket.close()
  })
  await page.route('**/unity/build-status.json', route => route.fulfill({ json: { ready: true, deviceSync: true, views: [],
    focusDevices: [{ id: 'cam-living', label: 'Camera' }], speakerAudio: ['audio/track-1.mp3'] } }))
  await page.route('**/unity/index.html', route => route.fulfill({ contentType: 'text/html', body: `<pre id="state"></pre><script>
    addEventListener('message', e => {
      if (e.data.type === 'homate:request-ready') parent.postMessage({type:'homate:ready'}, location.origin);
      if (e.data.type === 'homate:device-snapshot') document.querySelector('#state').textContent=JSON.stringify(e.data.devices);
      if (e.data.type === 'homate:focus-device') parent.postMessage({type:'homate:device-focused',deviceId:e.data.deviceId},location.origin);
    });
    window.homateSetAudioEnabled=enabled=>parent.postMessage({type:'homate:audio-state',enabled},location.origin);
    </script>` }))
  await page.goto('/login')
  await page.getByRole('button', { name: /Minh Đức/ }).click()
  await page.getByPlaceholder('••••').fill('1234')
  await page.getByRole('button', { name: /Đăng nhập vào không gian sống/ }).click()
  await expect(page).toHaveURL(/dashboard/)
  await page.goto('/house-3d')
  await expect(page.getByRole('heading', { name: 'Nhà 3D', exact: true })).toBeVisible({ timeout: 20000 })
  const state = page.frameLocator('iframe').locator('#state')
  await expect(state).toContainText('"power":false')
  await expect(state).not.toContainText('ac-living')
  await expect(state).toContainText('cam-living')
  await expect(state).toContainText('speaker-living')
  await expect(state).toContainText('tv-living')
  await expect(state).toContainText('fan-kitchen')
  await page.getByLabel('Xem thiết bị').selectOption('cam-living')
  await expect(page.getByLabel('Xem thiết bị')).toHaveValue('cam-living')
  await page.getByRole('button', { name: 'Bật âm thanh', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Tắt âm thanh', exact: true })).toHaveAttribute('aria-pressed', 'true')
  await page.getByRole('button', { name: 'Tắt âm thanh', exact: true }).click()
  power = true
  position = 70
  recording = true
  volume = 75
  speed = 3
  sendUpdate()
  await expect(state).toContainText('"power":true')
  await expect(state).toContainText('"position":70')
  await expect(state).toContainText('"recording":true')
  await expect(state).toContainText('"volume":75')
  await expect(state).toContainText('"speed":3')
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Nhà 3D', exact: true })).toBeVisible({ timeout: 20000 })
  await expect(state).toContainText('"position":70')
  position = 25
  disconnect()
  await expect(state).toContainText('"position":25', { timeout: 15000 })
})
