import { test, expect } from '@playwright/test';
import { mockAPIResponses } from '../fixtures/api-mocks';

/**
 * 任务调度器 - 任务操作测试
 * 测试删除任务、清空队列、定时任务操作
 */
test.describe('任务调度器 - 任务操作', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');
    await mockAPIResponses(page);
  });

  test('删除队列任务', async ({ page }) => {
    // Mock 包含任务的数据
    await page.route('**/api/tasks', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            items: [
              {
                id: 'task-1',
                prompt: '要删除的任务',
                working_dir: '/test',
                created_at: '2024-01-01T10:00:00',
              },
            ],
          }),
        });
      } else if (route.request().method() === 'DELETE') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true }),
        });
      }
    });

    await page.waitForLoadState('networkidle');

    // 点击删除按钮
    const deleteBtn = page.locator('button:has-text("🗑 删除")');
    await expect(deleteBtn).toBeVisible();
    await deleteBtn.click();

    // 验证确认对话框（使用 page.on('dialog')）
    page.on('dialog', async dialog => {
      expect(dialog.type()).toBe('confirm');
      expect(dialog.message()).toContain('确定要删除这个任务吗？');
      await dialog.accept();
    });

    // 验证成功通知
    await expect(page.locator('.notification-success')).toContainText('任务已删除');
  });

  test('取消删除任务', async ({ page }) => {
    await page.route('**/api/tasks', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            items: [
              {
                id: 'task-1',
                prompt: '测试任务',
                working_dir: '/test',
                created_at: '2024-01-01T10:00:00',
              },
            ],
          });
        });
      }
    });

    await page.waitForLoadState('networkidle');

    page.on('dialog', async dialog => {
      await dialog.dismiss();
    });

    await page.click('button:has-text("🗑 删除")');

    // 验证没有删除成功通知
    await expect(page.locator('.notification-success')).not.toBeVisible();
  });

  test('清空任务队列', async ({ page }) => {
    await page.route('**/api/tasks', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            items: [
              { id: 'task-1', prompt: '任务 1', working_dir: null, created_at: '2024-01-01T10:00:00' },
              { id: 'task-2', prompt: '任务 2', working_dir: null, created_at: '2024-01-01T10:01:00' },
            ],
          });
        });
      } else if (route.request().method() === 'DELETE') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true }),
        });
      }
    });

    await page.waitForLoadState('networkidle');

    page.on('dialog', async dialog => {
      expect(dialog.message()).toContain('确定要清空任务队列吗？');
      await dialog.accept();
    });

    await page.click('#scheduler-clear-queue-btn');

    await expect(page.locator('.notification-success')).toContainText('队列已清空');
  });

  test('切换定时任务启用状态', async ({ page }) => {
    await page.click('.scheduler-tab[data-tab="scheduled"]');

    await page.route('**/api/scheduled-tasks', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            items: [
              {
                id: 'scheduled-1',
                name: '测试任务',
                cron_expression: '0 9 * * *',
                next_run: '2024-01-02T09:00:00',
                enabled: true,
              },
            ],
          });
        });
      } else if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true }),
        });
      }
    });

    await page.waitForLoadState('networkidle');

    await page.click('button:has-text("禁用")');

    await expect(page.locator('.notification-success')).toContainText('状态已更新');
  });

  test('立即执行定时任务', async ({ page }) => {
    await page.click('.scheduler-tab[data-tab="scheduled"]');

    await page.route('**/api/scheduled-tasks', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            items: [
              {
                id: 'scheduled-1',
                name: '测试任务',
                cron_expression: '0 9 * * *',
                next_run: '2024-01-02T09:00:00',
                enabled: true,
              },
            ],
          });
        });
      }
    });

    await page.route('**/api/scheduled-tasks/*/run', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      });
    });

    await page.waitForLoadState('networkidle');

    page.on('dialog', async dialog => {
      expect(dialog.message()).toContain('确定要立即执行这个定时任务吗？');
      await dialog.accept();
    });

    await page.click('button:has-text("▶ 执行")');

    await expect(page.locator('.notification-success')).toContainText('任务已加入队列');
  });

  test('删除定时任务', async ({ page }) => {
    await page.click('.scheduler-tab[data-tab="scheduled"]');

    await page.route('**/api/scheduled-tasks', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            items: [
              {
                id: 'scheduled-1',
                name: '测试任务',
                cron_expression: '0 9 * * *',
                next_run: '2024-01-02T09:00:00',
                enabled: true,
              },
            ],
          });
        });
      } else if (route.request().method() === 'DELETE') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true }),
        });
      }
    });

    await page.waitForLoadState('networkidle');

    page.on('dialog', async dialog => {
      await dialog.accept();
    });

    await page.click('button:has-text("🗑")');

    await expect(page.locator('.notification-success')).toContainText('定时任务已删除');
  });

  test('编辑定时任务', async ({ page }) => {
    await page.click('.scheduler-tab[data-tab="scheduled"]');

    const testTask = {
      id: 'scheduled-1',
      name: '原始任务名',
      cron_expression: '0 9 * * *',
      next_run: '2024-01-02T09:00:00',
      enabled: true,
      prompt: '原始描述',
      working_dir: '/test',
      timeout: 600000,
      auto_approve: false,
      tools: 'Read,Write',
    };

    await page.route('**/api/scheduled-tasks', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: [testTask] }),
        });
      }
    });

    await page.waitForLoadState('networkidle');

    // 点击编辑按钮
    await page.click('button:has-text("✎ 编辑")');

    // 验证对话框标题
    await expect(page.locator('#scheduled-dialog-title')).toHaveText('编辑定时任务');

    // 验证表单已填充
    await expect(page.locator('#scheduled-name')).toHaveValue('原始任务名');
    await expect(page.locator('#scheduled-cron')).toHaveValue('0 9 * * *');
    await expect(page.locator('#scheduled-prompt')).toHaveValue('原始描述');
    await expect(page.locator('#scheduled-working-dir')).toHaveValue('/test');
    await expect(page.locator('#scheduled-timeout')).toHaveValue('600');
  });

  test('重试失败任务', async ({ page }) => {
    await page.click('.scheduler-tab[data-tab="failed"]');

    const failedTask = {
      id: 'task-1',
      prompt: '失败的任务',
      status: 'failed',
      error: 'Something went wrong',
      started_at: '2024-01-01T10:00:00',
      ended_at: '2024-01-01T10:01:00',
      working_dir: '/test',
      timeout: 600000,
      tools: 'Read',
      auto_approve: false,
    };

    await page.route('**/api/tasks/failed', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [failedTask],
          total: 1,
        }),
      });
    });

    await page.route('**/api/tasks/task-1', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(failedTask),
      });
    });

    await page.route('**/api/tasks', async route => {
      if (route.request().method() === 'POST') {
        const data = route.request().postDataJSON();
        expect(data.prompt).toBe('失败的任务');
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ id: 'new-task' }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: [] }),
        });
      }
    });

    await page.waitForLoadState('networkidle');

    // 点击重试按钮
    await page.click('button:has-text("重试")');

    await expect(page.locator('.notification-success')).toContainText('任务已重新加入队列');
  });
});
