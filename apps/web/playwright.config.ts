import { defineConfig } from '@playwright/test'

const port = Number(process.env.PLAYWRIGHT_PORT ?? 5173)
const baseURL = `http://127.0.0.1:${port}`

export default defineConfig({
  testDir: './tests',
  timeout: 45_000,
  workers: 1,
  use: { baseURL, channel: 'msedge', headless: true },
  webServer: { command: `npm run dev -- --port ${port} --strictPort`, url: baseURL, reuseExistingServer: !process.env.CI },
})
