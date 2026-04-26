import { test, expect } from '@playwright/test'
import { fileURLToPath } from 'url'
import path from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

test.describe('CodeReview Pro — 核心用户流程', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('首页加载正常，显示上传区域', async ({ page }) => {
    await expect(page.getByText('上传代码项目')).toBeVisible()
    await expect(page.getByText('点击或拖拽文件到此区域上传')).toBeVisible()
  })

  test('侧边栏导航可用', async ({ page }) => {
    await page.getByText('上传项目').click()
    await expect(page).toHaveURL(/\/upload/)
    await page.getByText('AI 配置').click()
    await expect(page).toHaveURL(/\/settings/)
    await page.getByText('首页').click()
    await expect(page).toHaveURL(/\/$/)
  })

  test('上传项目并查看项目概览', async ({ page }) => {
    const zipPath = path.resolve(__dirname, '../e2e-test-project.zip')

    await page.setInputFiles('input[type="file"]', zipPath)

    await expect(page.getByRole('button', { name: '开始上传并解析' })).toBeVisible()
    await page.getByRole('button', { name: '开始上传并解析' }).click()

    await expect(page).toHaveURL(/\/projects\//, { timeout: 15_000 })
    await expect(page.getByText('calculator')).toBeVisible({ timeout: 10_000 })
  })

  test('查看 AI 配置列表', async ({ page }) => {
    await page.getByText('AI 配置').click()
    await expect(page).toHaveURL(/\/settings/)

    await expect(page.getByText('AI 模型配置')).toBeVisible()
    await expect(page.getByRole('cell', { name: 'GLM-4.6 (智谱)' })).toBeVisible()
  })

  test('测试 AI 连接', async ({ page }) => {
    await page.getByText('AI 配置').click()
    await expect(page.getByText('AI 模型配置')).toBeVisible()

    const testBtn = page.locator('button:has-text("测试")').first()
    await testBtn.click()

    await expect(page.getByText(/连接成功/)).toBeVisible({ timeout: 60_000 })
  })
})
