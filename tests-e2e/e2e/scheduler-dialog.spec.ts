import { test, expect } from '@playwright/test';
import { mockAPIResponses } from '../fixtures/api-mocks';

/**
 * 任务调度器 - 对话框交互测试
 * 测试添加任务、添加定时任务、Cron 帮助对话框的交互
 */
test.describe('任务调度器 - 对话框交互', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');
    await mockAPIResponses(page);
  });

  test('显示添加任务对话框', async ({ page }) => {
    // 点击添加任务按钮
    await page.click('#scheduler-add-task-btn');

    // 验证对话框显示
    const dialog = page.locator('#add-task-dialog');
    await expect(dialog).toBeVisible();
    await expect(dialog).toHaveClass(/active/);

    // 验证表单字段存在
    await expect(page.locator('#task-prompt')).toBeVisible();
    await expect(page.locator('#task-working-dir')).toBeVisible();
    await expect(page.locator('#task-timeout')).toBeVisible();
    await expect(page.locator('#task-auto-approve')).toBeVisible();

    // 验证表单已重置
    await expect(page.locator('#task-prompt')).toHaveValue('');
    await expect(page.locator('#task-timeout')).toHaveValue('600');
  });

  test('关闭添加任务对话框', async ({ page }) => {
    await page.click('#scheduler-add-task-btn');
    await expect(page.locator('#add-task-dialog')).toBeVisible();

    // 点击关闭按钮
    await page.click('#close-add-task-dialog');

    // 验证对话框隐藏
    await expect(page.locator('#add-task-dialog')).not.toHaveClass(/active/);
  });

  test('点击对话框外部关闭', async ({ page }) => {
    await page.click('#scheduler-add-task-btn');
    await expect(page.locator('#add-task-dialog')).toBeVisible();

    // 点击对话框背景（外部区域）
    const dialog = page.locator('#add-task-dialog');
    await dialog.click({ position: { x: 10, y: 10 } });

    await expect(dialog).not.toHaveClass(/active/);
  });

  test('点击取消按钮关闭对话框', async ({ page }) => {
    await page.click('#scheduler-add-task-btn');
    await expect(page.locator('#add-task-dialog')).toBeVisible();

    await page.click('#cancel-add-task-btn');
    await expect(page.locator('#add-task-dialog')).not.toHaveClass(/active/);
  });

  test('显示添加定时任务对话框', async ({ page }) => {
    await page.click('#scheduler-add-scheduled-btn');

    const dialog = page.locator('#add-scheduled-dialog');
    await expect(dialog).toBeVisible();
    await expect(dialog).toHaveClass(/active/);

    // 验证表单字段
    await expect(page.locator('#scheduled-name')).toBeVisible();
    await expect(page.locator('#scheduled-cron')).toBeVisible();
    await expect(page.locator('#scheduled-prompt')).toBeVisible();
    await expect(page.locator('#scheduled-working-dir')).toBeVisible();
    await expect(page.locator('#scheduled-timeout')).toBeVisible();
    await expect(page.locator('#scheduled-enabled')).toBeVisible();

    // 验证默认标题
    await expect(page.locator('#scheduled-dialog-title')).toHaveText('添加定时任务');
  });

  test('显示 Cron 帮助对话框', async ({ page }) => {
    // 切换到定时任务标签页
    await page.click('.scheduler-tab[data-tab="scheduled"]');
    await page.click('#cron-help-btn');

    const dialog = page.locator('#cron-help-dialog');
    await expect(dialog).toBeVisible();
    await expect(dialog).toHaveClass(/active/);

    // 验证 Cron 示例列表
    const examples = page.locator('.cron-example-item');
    await expect(examples.first()).toBeVisible();

    // 验证第一个示例
    await expect(examples.nth(0)).toContainText('0 9 * * *');
    await expect(examples.nth(0)).toContainText('每天上午 9:00');
  });

  test('选择 Cron 示例并填充到表单', async ({ page }) => {
    await page.click('.scheduler-tab[data-tab="scheduled"]');
    await page.click('#cron-help-btn');

    // 等待对话框显示
    await expect(page.locator('#cron-help-dialog')).toBeVisible();

    // 点击第一个示例
    await page.click('.cron-example-item[data-expression="0 9 * * *"]');

    // 验证对话框关闭
    await expect(page.locator('#cron-help-dialog')).not.toHaveClass(/active/);

    // 验证 Cron 表达式已填充
    await expect(page.locator('#scheduled-cron')).toHaveValue('0 9 * * *');
  });

  test('显示任务详情对话框', async ({ page }) => {
    // 先切换到已完成标签页
    await page.click('.scheduler-tab[data-tab="completed"]');

    // Mock 任务详情 API
    await page.route('**/api/tasks/task-1', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'task-1',
          prompt: '测试任务',
          status: 'completed',
          started_at: '2024-01-01T10:00:00',
          ended_at: '2024-01-01T10:01:00',
          duration_ms: 60000,
          working_dir: '/test',
          tools_used: ['Read', 'Write'],
          files_changed: ['/test/file.py'],
          output: '任务输出内容',
          error: null,
        }),
      });
    });

    // 点击详情按钮
    await page.click('button:has-text("详情")');

    // 验证对话框显示
    await expect(page.locator('#task-detail-dialog')).toBeVisible();

    // 验证详情内容
    await expect(page.locator('#detail-task-prompt')).toContainText('测试任务');
    await expect(page.locator('#detail-task-status')).toHaveText('已完成');
    await expect(page.locator('#detail-task-duration')).toContainText('1m 0s');
  });
});
