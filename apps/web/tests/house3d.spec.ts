import { test, expect } from '@playwright/test'

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
