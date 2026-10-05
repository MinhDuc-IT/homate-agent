import { test, expect } from '@playwright/test'

test('original HomeMate screens work after PIN login', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto('/login')
  await page.getByRole('button', { name: /Minh Đức/ }).click()
  await page.getByPlaceholder('••••').fill('1234')
  await page.getByRole('button', { name: /Đăng nhập vào không gian sống/ }).click()
  await expect(page).toHaveURL(/dashboard/)
  for (const route of ['room', 'devices', 'camera', 'energy', 'scenes', 'schedules', 'settings']) {
    await page.goto(`/${route}`)
    await expect(page).toHaveURL(new RegExp(route))
    await expect(page.getByRole('navigation').getByRole('link', { name: 'Trang chủ', exact: true })).toBeVisible()
    await page.waitForLoadState('networkidle')
    await expect(page.locator('body')).not.toContainText('Failed to fetch')
    await page.screenshot({ path: `test-results/${route}.png`, fullPage: true })
  }
  await expect(page.getByRole('button', { name: /Thêm thành viên/ })).toBeVisible()
  await page.goto('/voice-agent')
  await expect(page.getByText(/Tính năng AI và điều khiển bằng giọng nói/)).toBeVisible()
  expect(errors).toEqual([])
})

test('manual device control persists in PostgreSQL', async ({ page }) => {
  await page.goto('/login')
  await page.getByRole('button', { name: /Minh Đức/ }).click()
  await page.getByPlaceholder('••••').fill('1234')
  await page.getByRole('button', { name: /Đăng nhập vào không gian sống/ }).click()
  await expect(page).toHaveURL(/dashboard/)
  await page.goto('/devices')
  await page.getByRole('button', { name: /Đèn phòng khách/ }).click()
  const toggle = page.getByRole('button', { name: /^(Bật|Tắt) thiết bị$/ })
  const previous = await toggle.getAttribute('aria-label')
  const response = page.waitForResponse(r => r.url().includes('/devices/light-living/actions') && r.request().method() === 'POST')
  await toggle.click()
  expect((await response).status()).toBe(200)
  const next = previous === 'Bật thiết bị' ? 'Tắt thiết bị' : 'Bật thiết bị'
  await expect(toggle).toHaveAttribute('aria-label', next)
  await page.reload()
  await page.getByRole('button', { name: /Đèn phòng khách/ }).click()
  await expect(toggle).toHaveAttribute('aria-label', next)
  await toggle.click()
  await expect(toggle).toHaveAttribute('aria-label', previous!)
})
