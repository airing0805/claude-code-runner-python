import { test, expect } from '@playwright/test';

/**
 * 导航测试
 * 测试从主页导航到任务调度视图
 */
test.describe('导航', () => {
  test('应显示主页面', async ({ page }) => {
    await page.goto('/');

    // 验证页面标题
    await expect(page).toHaveTitle(/Claude Code Runner/);

    // 验证导航菜单存在
    await expect(page.locator('.nav-menu')).toBeVisible();

    // 验证默认在当前会话视图
    await expect(page.locator('.nav-item[data-view="current-session"]')).toHaveClass(/active/);
  });

  test('应点击任务调度导航进入调度视图', async ({ page }) => {
    await page.goto('/');

    // 点击任务调度菜单项
    await page.click('.nav-item[data-view="scheduler"]');

    // 验证菜单高亮
    await expect(page.locator('.nav-item[data-view="scheduler"]')).toHaveClass(/active/);
    await expect(page.locator('.nav-item[data-view="current-session"]')).not.toHaveClass(/active/);

    // 验证调度视图显示
    await expect(page.locator('#view-scheduler')).toBeVisible();
    await expect(page.locator('#view-current-session')).not.toBeVisible();
  });

  test('应能在不同视图间切换', async ({ page }) => {
    await page.goto('/');

    // 切换到历史记录
    await page.click('.nav-item[data-view="history"]');
    await expect(page.locator('.nav-item[data-view="history"]')).toHaveClass(/active/);

    // 切换到示例任务
    await page.click('.nav-item[data-view="examples"]');
    await expect(page.locator('.nav-item[data-view="examples"]')).toHaveClass(/active/);

    // 切换到任务调度
    await page.click('.nav-item[data-view="scheduler"]');
    await expect(page.locator('.nav-item[data-view="scheduler"]')).toHaveClass(/active/);

    // 返回当前会话
    await page.click('.nav-item[data-view="current-session"]');
    await expect(page.locator('.nav-item[data-view="current-session"]')).toHaveClass(/active/);
  });

  test('任务调度视图应有完整的界面元素', async ({ page }) => {
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');

    // 验证调度器状态区域
    await expect(page.locator('#scheduler-status-icon')).toBeVisible();
    await expect(page.locator('#scheduler-status-text')).toBeVisible();

    // 验证控制按钮
    await expect(page.locator('#scheduler-start-btn')).toBeVisible();
    await expect(page.locator('#scheduler-stop-btn')).toBeVisible();
    await expect(page.locator('#scheduler-refresh-btn')).toBeVisible();

    // 验证标签页
    await expect(page.locator('#scheduler-tabs')).toBeVisible();

    // 验证统计信息
    await expect(page.locator('#scheduler-queue-count')).toBeVisible();
    await expect(page.locator('#scheduler-scheduled-count')).toBeVisible();
    await expect(page.locator('#scheduler-running-count')).toBeVisible();

    // 验证操作按钮
    await expect(page.locator('#scheduler-add-task-btn')).toBeVisible();
    await expect(page.locator('#scheduler-add-scheduled-btn')).toBeVisible();
  });
});
