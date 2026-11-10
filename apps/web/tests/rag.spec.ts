import { test, expect } from '@playwright/test'

test('chat keeps RAG sources and authenticated download without a knowledge management page', async ({ page }) => {
  await page.goto('/login')
  await page.getByRole('button', { name:/Minh Đức/ }).click()
  await page.getByPlaceholder('••••').fill('1234')
  const login = page.waitForResponse('**/api/dashboard/auth/login')
  await page.getByRole('button', { name:/Đăng nhập vào không gian sống/ }).click()
  const headers = { Authorization:'Bearer '+(await (await login).json()).access_token }
  await expect(page).toHaveURL(/dashboard/)
  await expect(page.getByRole('navigation').getByRole('link', { name:'Kho kiến thức', exact:true })).toHaveCount(0)
  const created = await page.request.post('/api/rag/documents', { headers, data:{ title:'RAG source test',filename:'source-test.md',content:'HomeMate source download verification: source documents require an authenticated user.',device_ids:[] } })
  expect(created.status()).toBe(201)
  const identifier = (await created.json()).id
  try {
    await page.route('**/api/ai/chat', async route => {
      const result = await page.request.get('/api/rag/search?query=HomeMate%20source%20download%20verification', { headers })
      expect(result.ok()).toBeTruthy()
      const chunks = (await result.json()).chunks.filter((chunk: {document_id: string}) => chunk.document_id === identifier)
      expect(chunks.length).toBeGreaterThan(0)
      await route.fulfill({ json:{ reply:'Tài liệu nguồn yêu cầu đăng nhập [1].',pending_actions:[],trace:[],sources:chunks.map((chunk: object,index: number) => ({...chunk,citation:index+1})) } })
    })
    await page.getByRole('navigation').getByRole('link', { name:'Trợ lý',exact:true }).click()
    await page.getByLabel('Tin nhắn cho HomeMate').fill('How does source download work?')
    await page.getByRole('button', { name:'Gửi',exact:true }).click()
    const sources=page.locator('details').filter({hasText:'Tài liệu đã tra cứu'})
    await expect(sources).toBeVisible()
    await sources.locator('summary').click()
    await expect(sources).toContainText('RAG source test')
    const downloaded=page.waitForEvent('download')
    await sources.getByRole('button', { name:'Tải tài liệu gốc' }).first().click()
    expect((await downloaded).suggestedFilename()).toBe('source-test.md')
  } finally {
    const deleted=await page.request.delete(`/api/rag/documents/${identifier}`, {headers})
    expect(deleted.ok()).toBeTruthy()
  }
})
