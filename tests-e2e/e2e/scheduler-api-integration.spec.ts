import { test, expect } from '@playwright/test';

/**
 * 任务调度器 - API 集成测试
 * 测试前端与后端 API 的集成
 */
test.describe('任务调度器 - API 集成', () => {
  test('获取调度器状态', async ({ page }) => {
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');

    // Mock 状态 API
    await page.route('**/api/scheduler/status', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          is_running: true,
          last_check_time: '2024-01-01T10:00:00',
        }),
      });
    });

    // 等待状态加载
    await page.waitForResponse('**/api/scheduler/status');

    // 验证状态显示
    const statusIcon = page.locator('#scheduler-status-icon');
    await expect(statusIcon).toHaveText('▶');
    await expect(statusIcon).toHaveClass(/running/);

    const statusText = page.locator('#scheduler-status-text');
    await expect(statusText).toHaveText('运行中');

    // 验证按钮状态
    await expect(page.locator('#scheduler-start-btn')).not.toBeVisible();
    await expect(page.locator('#scheduler-stop-btn')).toBeVisible();
  });

  test('获取任务队列', async ({ page }) => {
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');

    // Mock 队列 API
    await page.route('**/api/tasks', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'task-1',
              prompt: '测试任务 1',
              working_dir: '/test/dir1',
              created_at: '2024-01-01T10:00:00',
            },
            {
              id: 'task-2',
              prompt: '测试任务 2',
              working_dir: null,
              created_at: '2024-01-01T10:01:00',
            },
          ],
        }),
      });
    });

    // 等待队列加载
    await page.waitForResponse('**/api/tasks');

    // 验证队列显示
    const table = page.locator('#scheduler-queue-list .scheduler-table');
    await expect(table).toBeVisible();

    const rows = table.locator('tbody tr');
    await expect(rows).toHaveCount(2);

    await expect(rows.nth(0)).toContainText('测试任务 1');
    await expect(rows.nth(0)).toContainText('/test/dir1');
    await expect(rows.nth(1)).toContainText('测试任务 2');
    await expect(rows.nth(1)).toContainText('默认');
  });

  test('空队列显示空状态', async ({ page }) => {
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');

    // Mock 空队列
    await page.route('**/api/tasks', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [] }),
      });
    });

    await page.waitForResponse('**/api/tasks');

    await expect(page.locator('#scheduler-queue-list .empty-state')).toBeVisible();
    await expect(page.locator('#scheduler-queue-list .empty-state')).toHaveText('队列为空');
  });

  test('获取定时任务列表', async ({ page }) => {
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');
    await page.click('.scheduler-tab[data-tab="scheduled"]');

    // Mock 定时任务 API
    await page.route('**/api/scheduled-tasks', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'scheduled-1',
              name: '每日备份',
              cron_expression: '0 9 * * *',
              next_run: '2024-01-02T09:00:00',
              enabled: true,
            },
            {
              id: 'scheduled-2',
              name: '定时报告',
              cron_expression: '*/30 * * * *',
              next_run: '2024-01-01T10:30:00',
              enabled: false,
            },
          ],
        }),
      });
    });

    await page.waitForResponse('**/api/scheduled-tasks');

    const table = page.locator('#scheduler-scheduled-list .scheduler-table');
    await expect(table).toBeVisible();

    const rows = table.locator('tbody tr');
    await expect(rows).toHaveCount(2);

    await expect(rows.nth(0)).toContainText('每日备份');
    await expect(rows.nth(0)).toContainText('0 9 * * *');
    await expect(rows.nth(0)).toContainText('✓ 启用');

    await expect(rows.nth(1)).toContainText('定时报告');
    await expect(rows.nth(1)).toContainText('✗ 禁用');
  });

  test('添加任务到队列', async ({ page }) => {
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');

    // Mock 添加任务 API
    await page.route('**/api/tasks', async route => {
      if (route.request().method() === 'POST') {
        const data = route.request().postDataJSON();
        expect(data.prompt).toBe('新任务');
        expect(data.working_dir).toBe('/test');
        expect(data.timeout).toBe(300000); // 300 秒 = 300000 毫秒
        expect(data.auto_approve).toBe(true);

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ id: 'new-task-1' }),
        });
      } else {
        // GET 请求
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: [] }),
        });
      }
    });

    // 打开对话框并填写表单
    await page.click('#scheduler-add-task-btn');
    await page.fill('#task-prompt', '新任务');
    await page.fill('#task-working-dir', '/test');
    await page.fill('#task-timeout', '300');
    await page.check('#task-auto-approve');
    await page.click('#confirm-add-task-btn');

    // 验证成功通知
    await expect(page.locator('.notification-success')).toContainText('任务已添加到队列');
  });

  test('启动调度器', async ({ page }) => {
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');

    // Mock 状态 - 初始停止
    await page.route('**/api/scheduler/status', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          is_running: false,
          last_check_time: null,
        }),
      });
    });

    await page.waitForLoadState('networkidle');

    // Mock 启动 API
    await page.route('**/api/scheduler/start', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      });
    });

    await page.click('#scheduler-start-btn');

    // 验证成功通知
    await expect(page.locator('.notification-success')).toContainText('调度器已启动');
  });

  test('停止调度器', async ({ page }) => {
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');

    // Mock 状态 - 初始运行
    await page.route('**/api/scheduler/status', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ is_running: true },
      });
    });

    await page.waitForLoadState('networkidle');

    // Mock 停止 API
    await page.route('**/api/scheduler/stop', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      });
    });

    await page.click('#scheduler-stop-btn');

    await expect(page.locator('.notification-success')).toContainText('调度器已停止');
  });

  test('刷新按钮重新加载数据', async ({ page }) => {
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');

    let callCount = 0;
    await page.route('**/api/tasks', async route => {
      callCount++;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: `task-${callCount}`,
              prompt: `任务 ${callCount}`,
              working_dir: null,
              created_at: '2024-01-01T10:00:00',
            },
          ],
        }),
      });
    });

    await page.waitForResponse('**/api/tasks');

    // 记录初始调用次数
    const initialCount = callCount;
    expect(initialCount).toBeGreaterThan(0);

    // 点击刷新按钮
    await page.click('#scheduler-refresh-btn');

    // 等待新的响应
    await page.waitForResponse('**/api/tasks');

    // 验证 API 被再次调用
    expect(callCount).toBeGreaterThan(initialCount);
  });
});
