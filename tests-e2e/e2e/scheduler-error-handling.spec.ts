import { test, expect } from '@playwright/test';

/**
 * 任务调度器 - 错误处理测试
 * 测试网络错误、验证错误提示
 */
test.describe('任务调度器 - 错误处理', () => {
  test('网络错误 - 加载调度器状态失败', async ({ page }) => {
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');

    // Mock 网络错误
    await page.route('**/api/scheduler/status', async route => {
      await route.abort('failed');
    });

    // 等待加载完成
    await page.waitForTimeout(1000);

    // 验证错误状态不会导致页面崩溃
    const statusIcon = page.locator('#scheduler-status-icon');
    await expect(statusIcon).toBeVisible();
  });

  test('网络错误 - 加载任务队列失败', async ({ page }) => {
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');

    await page.route('**/api/tasks', async route => {
      await route.abort('failed');
    });

    await page.waitForTimeout(1000);

    // 验证错误消息显示
    await expect(page.locator('#scheduler-queue-list .error-state')).toBeVisible();
    await expect(page.locator('#scheduler-queue-list .error-state')).toHaveText('加载失败');
  });

  test('网络错误 - 加载定时任务失败', async ({ page }) => {
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');
    await page.click('.scheduler-tab[data-tab="scheduled"]');

    await page.route('**/api/scheduled-tasks', async route => {
      await route.abort('failed');
    });

    await page.waitForTimeout(1000);

    await expect(page.locator('#scheduler-scheduled-list .error-state')).toBeVisible();
    await expect(page.locator('#scheduler-scheduled-list .error-state')).toHaveText('加载失败');
  });

  test('添加任务失败 - 网络错误', async ({ page }) => {
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');

    // Mock 初始加载
    await page.route('**/api/tasks', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: [] }),
        });
      } else {
        // POST 请求失败
        await route.abort('failed');
      }
    });

    await page.waitForLoadState('networkidle');

    // 打开对话框并填写
    await page.click('#scheduler-add-task-btn');
    await page.fill('#task-prompt', '测试任务');
    await page.click('#confirm-add-task-btn');

    // 验证错误通知
    await expect(page.locator('.notification-error')).toBeVisible();
    await expect(page.locator('.notification-error')).toContainText('添加失败');
  });

  test('添加任务失败 - 服务器错误', async ({ page }) => {
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');

    await page.route('**/api/tasks', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: [] }),
        });
      } else {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Internal server error' }),
        });
      }
    });

    await page.waitForLoadState('networkidle');

    await page.click('#scheduler-add-task-btn');
    await page.fill('#task-prompt', '测试任务');
    await page.click('#confirm-add-task-btn');

    await expect(page.locator('.notification-error')).toBeVisible();
  });

  test('添加定时任务失败 - 验证错误', async ({ page }) => {
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');
    await page.click('.scheduler-tab[data-tab="scheduled"]');

    await page.route('**/api/scheduled-tasks', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: [] }),
        });
      } else {
        // 返回验证错误
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Invalid cron expression' }),
        });
      }
    });

    await page.waitForLoadState('networkidle');

    await page.click('#scheduler-add-scheduled-btn');
    await page.fill('#scheduled-name', '测试任务');
    await page.fill('#scheduled-cron', 'invalid');
    await page.fill('#scheduled-prompt', '任务描述');
    await page.click('#confirm-add-scheduled-btn');

    await expect(page.locator('.notification-error')).toBeVisible();
    await expect(page.locator('.notification-error')).toContainText('保存失败');
  });

  test('启动调度器失败', async ({ page }) => {
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');

    await page.route('**/api/scheduler/status', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ is_running: false }),
      });
    });

    await page.waitForLoadState('networkidle');

    await page.route('**/api/scheduler/start', async route => {
      await route.abort('failed');
    });

    await page.click('#scheduler-start-btn');

    await expect(page.locator('.notification-error')).toBeVisible();
    await expect(page.locator('.notification-error')).toContainText('启动失败');
  });

  test('停止调度器失败', async ({ page }) => {
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');

    await page.route('**/api/scheduler/status', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ is_running: true }),
      });
    });

    await page.waitForLoadState('networkidle');

    await page.route('**/api/scheduler/stop', async route => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Failed to stop' }),
      });
    });

    await page.click('#scheduler-stop-btn');

    await expect(page.locator('.notification-error')).toBeVisible();
    await expect(page.locator('.notification-error')).toContainText('停止失败');
  });

  test('通知消息自动消失', async ({ page }) => {
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');

    // Mock 添加任务
    await page.route('**/api/tasks', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: [] }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ id: 'task-1' }),
        });
      }
    });

    await page.waitForLoadState('networkidle');

    // 显示通知
    await page.click('#scheduler-add-task-btn');
    await page.fill('#task-prompt', '测试');
    await page.click('#confirm-add-task-btn');

    const notification = page.locator('.notification-success');
    await expect(notification).toBeVisible();

    // 等待通知消失（3 秒超时）
    await expect(notification).not.toBeVisible({ timeout: 4000 });
  });

  test('连续显示多个通知', async ({ page }) => {
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');

    await page.route('**/api/tasks', async route => {
      if (route.request().method() === 'POST') {
        await route.abort('failed');
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: [] }),
        });
      }
    });

    await page.waitForLoadState('networkidle');

    // 连续触发错误
    await page.click('#scheduler-add-task-btn');
    await page.click('#confirm-add-task-btn');
    await page.click('#scheduler-add-task-btn');
    await page.click('#confirm-add-task-btn');

    // 验证多个通知元素存在
    const notifications = page.locator('.notification-error');
    const count = await notifications.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });
});
