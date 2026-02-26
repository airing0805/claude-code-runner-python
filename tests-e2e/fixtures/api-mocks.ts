import { Page } from '@playwright/test';

/**
 * API Mock 工具函数
 * 用于模拟后端 API 响应
 */

/**
 * 设置通用的 API Mock 响应
 */
export async function mockAPIResponses(page: Page) {
  // 调度器状态
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

  // 任务队列
  await page.route('**/api/tasks', async route => {
    const method = route.request().method();

    if (method === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [] }),
      });
    } else if (method === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: 'new-task-id' }),
      });
    } else if (method === 'DELETE') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      });
    }
  });

  // 定时任务
  await page.route('**/api/scheduled-tasks', async route => {
    const method = route.request().method();

    if (method === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [] }),
      });
    } else if (method === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: 'scheduled-id' }),
      });
    } else if (method === 'PATCH') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      });
    } else if (method === 'DELETE') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      });
    }
  });

  // 运行中任务
  await page.route('**/api/tasks/running', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items: [] }),
    });
  });

  // 已完成任务
  await page.route('**/api/tasks/completed', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [],
        total: 0,
      }),
    });
  });

  // 失败任务
  await page.route('**/api/tasks/failed', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [],
        total: 0,
      }),
    });
  });

  // Cron 验证
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
}

/**
 * Mock 特定的任务数据
 */
export async function mockTaskData(page: Page, data: {
  queue?: any[];
  scheduled?: any[];
  running?: any[];
  completed?: any[];
  failed?: any[];
}) {
  if (data.queue !== undefined) {
    await page.route('**/api/tasks', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: data.queue }),
        });
      }
    });
  }

  if (data.scheduled !== undefined) {
    await page.route('**/api/scheduled-tasks', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: data.scheduled }),
        });
      }
    });
  }

  if (data.running !== undefined) {
    await page.route('**/api/tasks/running', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: data.running }),
      });
    });
  }

  if (data.completed !== undefined) {
    await page.route('**/api/tasks/completed', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: data.completed,
          total: data.completed.length,
        }),
      });
    });
  }

  if (data.failed !== undefined) {
    await page.route('**/api/tasks/failed', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: data.failed,
          total: data.failed.length,
        }),
      });
    });
  }
}
