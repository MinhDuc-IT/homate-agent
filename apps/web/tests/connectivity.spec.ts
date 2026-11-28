import { test, expect } from '@playwright/test'

test('device connectivity updates separately from its power state', async ({ page }) => {
  let status = 'online'
  await page.route('**/api/dashboard/device-connectivity', route => route.fulfill({ json: {
    'light-living': { adapter: 'mqtt', status, last_seen_at: 1700000000 },
  } }))
  await page.goto('/login')
  await page.getByRole('button', { name: /Minh Đức/ }).click()
  await page.getByPlaceholder('••••').fill('1234')
  await page.getByRole('button', { name: /Đăng nhập vào không gian sống/ }).click()
  await expect(page).toHaveURL(/dashboard/)
  await page.goto('/devices')
  await expect(page.getByText('Đã kết nối', { exact: true }).first()).toBeVisible()
  status = 'offline'
  await expect(page.getByText('Mất kết nối', { exact: false }).first()).toBeVisible({ timeout: 10000 })
  await expect(page.getByText(/Trạng thái hiển thị là lần ghi nhận gần nhất/).first()).toBeVisible()
  status = 'online'
  await expect(page.getByText('Đã kết nối', { exact: true }).first()).toBeVisible({ timeout: 10000 })
  await expect(page.getByText(/Trạng thái hiển thị là lần ghi nhận gần nhất/)).toHaveCount(0)
})
