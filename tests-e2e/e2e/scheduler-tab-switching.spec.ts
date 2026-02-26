import { test, expect } from '@playwright/test';
import { mockAPIResponses } from '../fixtures/api-mocks';

/**
 * 任务调度器 - 标签页切换测试
 * 测试各个标签页（queue, scheduled, running, completed, failed）的切换和显示
 */
test.describe('任务调度器 - 标签页切换', () => {
  test.beforeEach(async ({ page }) => {
    // 导航到任务调度视图
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');

    // Mock API 响应
    await mockAPIResponses(page);
  });

  test('应显示任务调度视图', async ({ page }) => {
    // 验证视图已切换
    const viewPanel = page.locator('#view-scheduler');
    await expect(viewPanel).toBeVisible();

    // 验证标签页存在
    const tabs = page.locator('.scheduler-tab');
    await expect(tabs).toHaveCount(5);

    // 验证标签页文本
    await expect(tabs.nth(0)).toContainText('队列');
    await expect(tabs.nth(1)).toContainText('定时任务');
    await expect(tabs.nth(2)).toContainText('运行中');
    await expect(tabs.nth(3)).toContainText('已完成');
    await expect(tabs.nth(4)).toContainText('失败');
  });

  test('默认应显示队列标签页', async ({ page }) => {
    // 验证队列标签页为激活状态
    const queueTab = page.locator('.scheduler-tab[data-tab="queue"]');
    await expect(queueTab).toHaveClass(/active/);

    // 验证队列内容区域可见
    const queuePane = page.locator('#scheduler-tab-queue');
    await expect(queuePane).toBeVisible();
  });

  test('切换到定时任务标签页', async ({ page }) => {
    // 点击定时任务标签
    await page.click('.scheduler-tab[data-tab="scheduled"]');

    // 验证标签高亮
    const scheduledTab = page.locator('.scheduler-tab[data-tab="scheduled"]');
    await expect(scheduledTab).toHaveClass(/active/);
    await expect(page.locator('.scheduler-tab[data-tab="queue"]')).not.toHaveClass(/active/);

    // 验证内容区域切换
    const scheduledPane = page.locator('#scheduler-tab-scheduled');
    await expect(scheduledPane).toBeVisible();
    await expect(page.locator('#scheduler-tab-queue')).not.toBeVisible();
  });

  test('切换到运行中标签页', async ({ page }) => {
    await page.click('.scheduler-tab[data-tab="running"]');

    const runningTab = page.locator('.scheduler-tab[data-tab="running"]');
    await expect(runningTab).toHaveClass(/active/);
    await expect(page.locator('#scheduler-tab-running')).toBeVisible();
  });

  test('切换到已完成标签页', async ({ page }) => {
    await page.click('.scheduler-tab[data-tab="completed"]');

    const completedTab = page.locator('.scheduler-tab[data-tab="completed"]');
    await expect(completedTab).toHaveClass(/active/);
    await expect(page.locator('#scheduler-tab-completed')).toBeVisible();
  });

  test('切换到失败标签页', async ({ page }) => {
    await page.click('.scheduler-tab[data-tab="failed"]');

    const failedTab = page.locator('.scheduler-tab[data-tab="failed"]');
    await expect(failedTab).toHaveClass(/active/);
    await expect(page.locator('#scheduler-tab-failed')).toBeVisible();
  });

  test('在多个标签页之间切换', async ({ page }) => {
    const tabs = ['queue', 'scheduled', 'running', 'completed', 'failed'];

    for (const tab of tabs) {
      await page.click(`.scheduler-tab[data-tab="${tab}"]`);
      await expect(page.locator(`.scheduler-tab[data-tab="${tab}"]`)).toHaveClass(/active/);
      await expect(page.locator(`#scheduler-tab-${tab}`)).toBeVisible();
    }

    // 回到队列标签
    await page.click('.scheduler-tab[data-tab="queue"]');
    await expect(page.locator('.scheduler-tab[data-tab="queue"]')).toHaveClass(/active/);
  });
});
