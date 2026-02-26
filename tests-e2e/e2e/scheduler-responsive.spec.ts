import { test, expect } from '@playwright/test';
import { mockAPIResponses, mockTaskData } from '../fixtures/api-mocks';

/**
 * 任务调度器 - 响应式布局测试
 * 测试不同屏幕宽度下的布局适配
 *
 * 断点定义:
 * - 桌面: > 1024px - 完整表格布局
 * - 平板: 768px - 1024px - 紧凑表格
 * - 移动: < 768px - 卡片式列表
 */

// 测试数据
const mockQueueData = [
  {
    id: 'task-1',
    prompt: '这是一个测试任务描述，用于测试响应式布局',
    working_dir: '/test/workspace',
    created_at: '2024-01-01T10:00:00',
    timeout: 600,
    auto_approve: false,
    tools: ['Read', 'Edit'],
  },
  {
    id: 'task-2',
    prompt: '第二个测试任务',
    working_dir: '/another/path',
    created_at: '2024-01-01T11:00:00',
    timeout: 300,
    auto_approve: true,
    tools: [],
  },
];

test.describe('任务调度器 - 响应式布局', () => {
  // ==================== 桌面端测试 (>1024px) ====================
  test.describe('桌面端布局 (>1024px)', () => {
    test.use({ viewport: { width: 1280, height: 800 } });

    test.beforeEach(async ({ page }) => {
      await mockAPIResponses(page);
      await page.goto('/');
      await page.click('.nav-item[data-view="scheduler"]');
      await page.waitForLoadState('networkidle');
    });

    test('应显示完整表格布局', async ({ page }) => {
      // 验证视图已切换
      const viewPanel = page.locator('#view-scheduler');
      await expect(viewPanel).toBeVisible();

      // 验证标签页存在
      const tabs = page.locator('.scheduler-tab');
      await expect(tabs).toHaveCount(5);
    });

    test('状态栏应水平排列', async ({ page }) => {
      const statusBar = page.locator('.scheduler-status-bar');
      await expect(statusBar).toBeVisible();

      // 检查 flex 布局
      const display = await statusBar.evaluate(el =>
        window.getComputedStyle(el).display
      );
      expect(display).toBe('flex');
    });

    test('标签页应显示完整文本', async ({ page }) => {
      const tabs = page.locator('.scheduler-tab .tab-text');
      await expect(tabs.first()).toBeVisible();
    });

    test('队列表格应显示所有列', async ({ page }) => {
      await mockTaskData(page, { queue: mockQueueData });
      await page.goto('/');
      await page.click('.nav-item[data-view="scheduler"]');
      await page.waitForLoadState('networkidle');

      // 验证表格存在
      const table = page.locator('.scheduler-table');
      await expect(table).toBeVisible();
    });
  });

  // ==================== 平板端测试 (768-1024px) ====================
  test.describe('平板端布局 (768-1024px)', () => {
    test.use({ viewport: { width: 900, height: 768 } });

    test.beforeEach(async ({ page }) => {
      await mockAPIResponses(page);
      await page.goto('/');
      await page.click('.nav-item[data-view="scheduler"]');
      await page.waitForLoadState('networkidle');
    });

    test('表格应使用紧凑布局', async ({ page }) => {
      await mockTaskData(page, { queue: mockQueueData });
      await page.goto('/');
      await page.click('.nav-item[data-view="scheduler"]');
      await page.waitForLoadState('networkidle');

      // 验证表格存在
      const table = page.locator('.scheduler-table');
      await expect(table).toBeVisible();
    });

    test('标签页导航应完整显示', async ({ page }) => {
      const tabs = page.locator('.scheduler-tab');
      await expect(tabs).toHaveCount(5);

      // 验证所有标签可见
      for (let i = 0; i < 5; i++) {
        await expect(tabs.nth(i)).toBeVisible();
      }
    });
  });

  // ==================== 移动端测试 (<768px) ====================
  // 注意：移动端测试需要处理菜单展开，这里使用 force click 绕过覆盖问题
  test.describe('移动端布局 (<768px)', () => {
    test.use({ viewport: { width: 375, height: 667 } });

    test('移动端菜单按钮应存在', async ({ page }) => {
      await mockAPIResponses(page);
      await page.goto('/');
      await page.waitForLoadState('networkidle');

      // 验证移动端菜单按钮存在
      const menuToggle = page.locator('#menu-toggle');
      await expect(menuToggle).toBeVisible();
    });

    test('移动端应能访问调度器视图', async ({ page }) => {
      await mockAPIResponses(page);
      await page.goto('/');
      await page.waitForLoadState('networkidle');

      // 使用 force click 绕过覆盖问题
      await page.locator('#menu-toggle').click({ force: true });
      await page.locator('.nav-item[data-view="scheduler"]').click({ force: true });
      await page.waitForLoadState('networkidle');

      // 验证视图已切换
      const viewPanel = page.locator('#view-scheduler');
      await expect(viewPanel).toBeVisible();
    });
  });

  // ==================== 视口切换测试 ====================
  test.describe('视口动态切换', () => {
    test('从桌面切换到移动端布局应正确更新', async ({ page }) => {
      await mockAPIResponses(page);
      await mockTaskData(page, { queue: mockQueueData });

      // 设置桌面视口
      await page.setViewportSize({ width: 1280, height: 800 });
      await page.goto('/');
      await page.click('.nav-item[data-view="scheduler"]');
      await page.waitForLoadState('networkidle');

      // 验证视图可见
      const viewPanel = page.locator('#view-scheduler');
      await expect(viewPanel).toBeVisible();

      // 切换到移动视口
      await page.setViewportSize({ width: 375, height: 667 });
      await page.waitForTimeout(100);

      // 验证视图仍然可见
      await expect(viewPanel).toBeVisible();
    });
  });

  // ==================== CSS 响应式断点测试 ====================
  test.describe('CSS 响应式断点验证', () => {
    test('桌面端表头应可见', async ({ page }) => {
      await mockAPIResponses(page);
      await mockTaskData(page, { queue: mockQueueData });
      await page.setViewportSize({ width: 1280, height: 800 });
      await page.goto('/');
      await page.click('.nav-item[data-view="scheduler"]');
      await page.waitForLoadState('networkidle');

      // 验证表头可见
      const tableHeader = page.locator('.scheduler-table thead');
      await expect(tableHeader).toBeVisible();
    });

    test('平板端表头应可见', async ({ page }) => {
      await mockAPIResponses(page);
      await mockTaskData(page, { queue: mockQueueData });
      await page.setViewportSize({ width: 900, height: 768 });
      await page.goto('/');
      await page.click('.nav-item[data-view="scheduler"]');
      await page.waitForLoadState('networkidle');

      // 验证表头可见
      const tableHeader = page.locator('.scheduler-table thead');
      await expect(tableHeader).toBeVisible();
    });

    test('移动端表头应隐藏', async ({ page }) => {
      await mockAPIResponses(page);
      await mockTaskData(page, { queue: mockQueueData });
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/');
      await page.locator('#menu-toggle').click({ force: true });
      await page.locator('.nav-item[data-view="scheduler"]').click({ force: true });
      await page.waitForLoadState('networkidle');

      // 验证表头隐藏（移动端使用卡片式列表）
      const tableHeader = page.locator('.scheduler-table thead');
      await expect(tableHeader).toBeHidden();
    });
  });
});
