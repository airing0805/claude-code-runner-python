import { test, expect } from '@playwright/test';
import { mockAPIResponses } from '../fixtures/api-mocks';

/**
 * 任务调度器 - 任务详情测试
 * 测试任务详情对话框的显示和功能
 */
test.describe('任务调度器 - 任务详情', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');
    await mockAPIResponses(page);
  });

  test('显示已完成任务详情', async ({ page }) => {
    await page.click('.scheduler-tab[data-tab="completed"]');

    await page.route('**/api/tasks/completed', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'task-1',
              prompt: '测试任务',
              status: 'completed',
              started_at: '2024-01-01T10:00:00',
              ended_at: '2024-01-01T10:01:30',
              duration_ms: 90000,
              working_dir: '/test/project',
              tools_used: ['Read', 'Write', 'Edit'],
              files_changed: ['/test/file1.py', '/test/file2.js'],
              output: '任务执行成功\n输出内容...',
              error: null,
            },
          ],
          total: 1,
        }),
      });
    });

    await page.route('**/api/tasks/task-1', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'task-1',
          prompt: '测试任务',
          status: 'completed',
          started_at: '2024-01-01T10:00:00',
          ended_at: '2024-01-01T10:01:30',
          duration_ms: 90000,
          working_dir: '/test/project',
          tools_used: ['Read', 'Write', 'Edit'],
          files_changed: ['/test/file1.py', '/test/file2.js'],
          output: '任务执行成功\n输出内容...',
          error: null,
        }),
      });
    });

    await page.waitForLoadState('networkidle');

    // 点击详情按钮
    await page.click('button:has-text("详情")');

    // 验证对话框显示
    const dialog = page.locator('#task-detail-dialog');
    await expect(dialog).toBeVisible();

    // 验证任务描述
    await expect(page.locator('#detail-task-prompt')).toHaveText('测试任务');

    // 验证状态
    await expect(page.locator('#detail-task-status')).toHaveText('已完成');
    await expect(page.locator('#detail-task-status')).toHaveClass(/status-completed/);

    // 验证时间
    await expect(page.locator('#detail-task-started')).toBeVisible();
    await expect(page.locator('#detail-task-ended')).toBeVisible();

    // 验证耗时
    await expect(page.locator('#detail-task-duration')).toHaveText('1m 30s');

    // 验证工作目录
    await expect(page.locator('#detail-task-working-dir')).toHaveText('/test/project');

    // 验证工具使用
    const toolsEl = page.locator('#detail-task-tools');
    await expect(toolsEl.locator('.tool-tag')).toHaveCount(3);
    await expect(toolsEl).toContainText('Read');
    await expect(toolsEl).toContainText('Write');
    await expect(toolsEl).toContainText('Edit');

    // 验证文件变更
    const filesEl = page.locator('#detail-task-files');
    await expect(filesEl.locator('.file-item')).toHaveCount(2);
  });

  test('显示失败任务详情', async ({ page }) => {
    await page.click('.scheduler-tab[data-tab="failed"]');

    await page.route('**/api/tasks/failed', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'task-1',
              prompt: '失败任务',
              status: 'failed',
              error: 'Error: Connection failed',
              started_at: '2024-01-01T10:00:00',
              ended_at: '2024-01-01T10:00:30',
              duration_ms: 30000,
              working_dir: '/test',
              tools_used: ['Bash'],
              files_changed: [],
              output: 'Starting task...',
            },
          ],
          total: 1,
        }),
      });
    });

    await page.route('**/api/tasks/task-1', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'task-1',
          prompt: '失败任务',
          status: 'failed',
          error: 'Error: Connection failed',
          started_at: '2024-01-01T10:00:00',
          ended_at: '2024-01-01T10:00:30',
          duration_ms: 30000,
          working_dir: '/test',
          tools_used: ['Bash'],
          files_changed: [],
          output: 'Starting task...',
        }),
      });
    });

    await page.waitForLoadState('networkidle');

    await page.click('button:has-text("详情")');

    // 验证状态显示失败
    await expect(page.locator('#detail-task-status')).toHaveText('失败');
    await expect(page.locator('#detail-task-status')).toHaveClass(/status-failed/);

    // 验证错误信息显示
    await expect(page.locator('#detail-error-section')).toBeVisible();
    await expect(page.locator('#detail-task-error')).toHaveText('Error: Connection failed');
  });

  test '显示运行中任务详情', async ({ page }) => {
    await page.click('.scheduler-tab[data-tab="running")');

    await page.route('**/api/tasks/running', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'task-1',
              prompt: '运行中任务',
              status: 'running',
              started_at: new Date(Date.now() - 60000).toISOString(),
              working_dir: '/test',
            },
          ],
        }),
      });
    });

    await page.route('**/api/tasks/task-1', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'task-1',
          prompt: '运行中任务',
          status: 'running',
          started_at: new Date(Date.now() - 60000).toISOString(),
          working_dir: '/test',
          tools_used: ['Read'],
          files_changed: [],
          output: 'Processing...',
        }),
      });
    });

    await page.waitForLoadState('networkidle');

    await page.click('button:has-text("详情")');

    await expect(page.locator('#detail-task-status')).toHaveText('运行中');
    await expect(page.locator('#detail-task-status')).toHaveClass(/status-running/);
  });

  test('关闭任务详情对话框', async ({ page }) => {
    await page.click('.scheduler-tab[data-tab="completed")');

    await page.route('**/api/tasks/completed', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'task-1',
              prompt: '测试任务',
              status: 'completed',
              started_at: '2024-01-01T10:00:00',
              ended_at: '2024-01-01T10:01:00',
              duration_ms: 60000,
              working_dir: '/test',
              tools_used: [],
              files_changed: [],
              output: 'Done',
            },
          ],
          total: 1,
        }),
      });
    });

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
          tools_used: [],
          files_changed: [],
          output: 'Done',
        }),
      });
    });

    await page.waitForLoadState('networkidle');

    await page.click('button:has-text("详情")');
    await expect(page.locator('#task-detail-dialog')).toBeVisible();

    // 点击关闭按钮
    await page.click('#close-detail-btn');

    await expect(page.locator('#task-detail-dialog')).not.toHaveClass(/active/);
  });

  test('点击对话框外部关闭', async ({ page }) => {
    await page.click('.scheduler-tab[data-tab="completed")');

    await page.route('**/api/tasks/completed', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'task-1',
              prompt: '测试任务',
              status: 'completed',
              started_at: '2024-01-01T10:00:00',
              ended_at: '2024-01-01T10:01:00',
              duration_ms: 60000,
              working_dir: '/test',
              tools_used: [],
              files_changed: [],
              output: 'Done',
            },
          ],
          total: 1,
        }),
      });
    });

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
          tools_used: [],
          files_changed: [],
          output: 'Done',
        }),
      });
    });

    await page.waitForLoadState('networkidle');

    await page.click('button:has-text("详情")');
    await expect(page.locator('#task-detail-dialog')).toBeVisible();

    const dialog = page.locator('#task-detail-dialog');
    await dialog.click({ position: { x: 10, y: 10 } });

    await expect(dialog).not.toHaveClass(/active/);
  });

  test('折叠/展开输出日志', async ({ page }) => {
    await page.click('.scheduler-tab[data-tab="completed")');

    await page.route('**/api/tasks/completed', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'task-1',
              prompt: '测试任务',
              status: 'completed',
              started_at: '2024-01-01T10:00:00',
              ended_at: '2024-01-01T10:01:00',
              duration_ms: 60000,
              working_dir: '/test',
              tools_used: [],
              files_changed: [],
              output: 'Line 1\nLine 2\nLine 3',
            },
          ],
          total: 1,
        }),
      });
    });

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
          tools_used: [],
          files_changed: [],
          output: 'Line 1\nLine 2\nLine 3',
        }),
      });
    });

    await page.waitForLoadState('networkidle');

    await page.click('button:has-text("详情")');

    const outputToggle = page.locator('#detail-output-toggle');
    const outputContent = page.locator('#detail-task-output');

    // 点击折叠
    await outputToggle.click();
    await expect(outputContent).toHaveClass(/collapsed/);
    await expect(outputToggle.locator('.collapse-icon')).toHaveText('▶');

    // 点击展开
    await outputToggle.click();
    await expect(outputContent).not.toHaveClass(/collapsed/);
    await expect(outputToggle.locator('.collapse-icon')).toHaveText('▼');
  });

  test('复制任务日志', async ({ page }) => {
    await page.click('.scheduler-tab[data-tab="completed")');

    const testOutput = 'Test output content\nLine 2\nLine 3';

    await page.route('**/api/tasks/completed', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'task-1',
              prompt: '测试任务',
              status: 'completed',
              started_at: '2024-01-01T10:00:00',
              ended_at: '2024-01-01T10:01:00',
              duration_ms: 60000,
              working_dir: '/test',
              tools_used: [],
              files_changed: [],
              output: testOutput,
            },
          ],
          total: 1,
        }),
      });
    });

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
          tools_used: [],
          files_changed: [],
          output: testOutput,
        }),
      });
    });

    await page.waitForLoadState('networkidle');

    await page.click('button:has-text("详情")');

    // 模拟剪贴板 API
    const clipboardText = await page.evaluate(async () => {
      const text = document.getElementById('detail-task-output')?.textContent || '';
      return text;
    });

    await page.click('#copy-task-log-btn');

    await expect(page.locator('.notification-success')).toContainText('日志已复制');
  });
});
