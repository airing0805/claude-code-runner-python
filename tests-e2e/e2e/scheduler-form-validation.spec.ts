import { test, expect } from '@playwright/test';
import { mockAPIResponses } from '../fixtures/api-mocks';

/**
 * 任务调度器 - 表单验证测试
 * 测试必填字段验证、Cron 表达式验证
 */
test.describe('任务调度器 - 表单验证', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');
    await mockAPIResponses(page);
  });

  test('验证任务表单必填字段 - 缺少提示', async ({ page }) => {
    await page.click('#scheduler-add-task-btn');
    await expect(page.locator('#add-task-dialog')).toBeVisible();

    // 不填写任何内容直接提交
    await page.click('#confirm-add-task-btn');

    // 验证错误通知显示
    const notification = page.locator('.notification-error');
    await expect(notification).toBeVisible();
    await expect(notification).toContainText('请输入任务描述');
  });

  test('验证任务表单必填字段 - 只有提示', async ({ page }) => {
    await page.click('#scheduler-add-task-btn');

    // 只填写提示文本
    await page.fill('#task-prompt', '这是一个测试任务');
    await page.click('#confirm-add-task-btn');

    // 验证错误通知不显示
    await expect(page.locator('.notification-error')).not.toBeVisible();

    // 验证成功通知
    await expect(page.locator('.notification-success')).toContainText('任务已添加到队列');
  });

  test('验证定时任务表单必填字段', async ({ page }) => {
    await page.click('.scheduler-tab[data-tab="scheduled"]');
    await page.click('#scheduler-add-scheduled-btn');

    // 测试缺少名称
    await page.click('#confirm-add-scheduled-btn');
    await expect(page.locator('.notification-error')).toContainText('请输入任务名称');

    // 填写名称，测试缺少 Cron
    await page.fill('#scheduled-name', '测试定时任务');
    await page.click('#confirm-add-scheduled-btn');
    await expect(page.locator('.notification-error')).toContainText('请输入 Cron 表达式');

    // 填写 Cron，测试缺少提示
    await page.fill('#scheduled-cron', '0 9 * * *');
    await page.click('#confirm-add-scheduled-btn');
    await expect(page.locator('.notification-error')).toContainText('请输入任务描述');

    // 填写完整表单
    await page.fill('#scheduled-prompt', '这是一个定时任务');
    await page.click('#confirm-add-scheduled-btn');
    await expect(page.locator('.notification-success')).toContainText('定时任务已创建');
  });

  test('验证 Cron 表达式 - 有效表达式', async ({ page }) => {
    await page.click('.scheduler-tab[data-tab="scheduled"]');
    await page.click('#scheduler-add-scheduled-btn');

    // Mock 验证 API
    await page.route('**/api/scheduler/validate-cron', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          valid: true,
          next_run: '2024-01-02T09:00:00',
        }),
      });
    });

    // 输入有效的 Cron 表达式
    const cronInput = page.locator('#scheduled-cron');
    await cronInput.fill('0 9 * * *');

    // 等待防抖（300ms）
    await page.waitForTimeout(500);

    // 验证预览显示
    await expect(page.locator('#cron-preview')).toBeVisible();
    await expect(page.locator('#cron-error')).not.toBeVisible();
  });

  test('验证 Cron 表达式 - 无效表达式', async ({ page }) => {
    await page.click('.scheduler-tab[data-tab="scheduled"]');
    await page.click('#scheduler-add-scheduled-btn');

    // Mock 验证 API - 返回无效
    await page.route('**/api/scheduler/validate-cron', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          valid: false,
          error: 'Invalid cron expression',
        }),
      });
    });

    const cronInput = page.locator('#scheduled-cron');
    await cronInput.fill('invalid cron');

    // 等待防抖
    await page.waitForTimeout(500);

    // 验证错误显示
    await expect(page.locator('#cron-preview')).not.toBeVisible();
    await expect(page.locator('#cron-error')).toBeVisible();
    await expect(page.locator('#cron-error')).toContainText('Invalid cron expression');
  });

  test('验证 Cron 表达式 - 网络错误', async ({ page }) => {
    await page.click('.scheduler-tab[data-tab="scheduled"]');
    await page.click('#scheduler-add-scheduled-btn');

    // Mock 验证 API - 返回错误
    await page.route('**/api/scheduler/validate-cron', async route => {
      await route.abort('failed');
    });

    const cronInput = page.locator('#scheduled-cron');
    await cronInput.fill('0 9 * * *');

    // 等待防抖
    await page.waitForTimeout(500);

    // 验证错误显示
    await expect(page.locator('#cron-error')).toBeVisible();
    await expect(page.locator('#cron-error')).toContainText('验证失败');
  });

  test('清空 Cron 表达式后隐藏预览和错误', async ({ page }) => {
    await page.click('.scheduler-tab[data-tab="scheduled"]');
    await page.click('#scheduler-add-scheduled-btn');

    await page.route('**/api/scheduler/validate-cron', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ valid: true }),
      });
    });

    // 输入表达式
    await page.fill('#scheduled-cron', '0 9 * * *');
    await page.waitForTimeout(500);
    await expect(page.locator('#cron-preview')).toBeVisible();

    // 清空表达式
    await page.fill('#scheduled-cron', '');
    await page.waitForTimeout(500);

    // 验证预览和错误都隐藏
    await expect(page.locator('#cron-preview')).not.toBeVisible();
    await expect(page.locator('#cron-error')).not.toBeVisible();
  });

  test('任务超时字段默认值', async ({ page }) => {
    await page.click('#scheduler-add-task-btn');

    // 验证默认超时值为 600 秒（10 分钟）
    await expect(page.locator('#task-timeout')).toHaveValue('600');
  });

  test('定时任务超时字段默认值', async ({ page }) => {
    await page.click('.scheduler-tab[data-tab="scheduled"]');
    await page.click('#scheduler-add-scheduled-btn');

    // 验证默认超时值为 600 秒
    await expect(page.locator('#scheduled-timeout')).toHaveValue('600');
  });

  test('自动批准复选框默认状态', async ({ page }) => {
    await page.click('#scheduler-add-task-btn');

    // 验证默认未选中
    await expect(page.locator('#task-auto-approve')).not.toBeChecked();
  });

  test('定时任务启用复选框默认状态', async ({ page }) => {
    await page.click('.scheduler-tab[data-tab="scheduled"]');
    await page.click('#scheduler-add-scheduled-btn');

    // 验证默认选中
    await expect(page.locator('#scheduled-enabled')).toBeChecked();
  });
});
