import { defineConfig, devices } from '@playwright/test';

const isHeaded = process.env.HEADED === 'true';
const slowMo = process.env.SLOWMO ? parseInt(process.env.SLOWMO) : 0;

export default defineConfig({
  testDir: '.',
  testMatch: 'e2e-smoke-test.ts',
  fullyParallel: false, // Run tests sequentially for game simulation
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
  ],
  timeout: 120000, // 2 minutes per test (Docker may be slow)
  expect: {
    timeout: 10000, // 10 seconds for assertions
  },
  use: {
    baseURL: 'http://localhost',
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
    screenshot: 'only-on-failure',
    headless: !isHeaded,
    launchOptions: {
      slowMo: slowMo,
    },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
