import { test, expect } from '@playwright/test';
import { mockAPIResponses } from '../fixtures/api-mocks';

/**
 * 任务调度器 - 工具选择测试
 * 测试工具多选组件的交互
 */
test.describe('任务调度器 - 工具选择', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');
    await mockAPIResponses(page);
  });

  test('打开工具选择下拉框', async ({ page }) => {
    await page.click('#scheduler-add-task-btn');

    // 点击工具选择按钮
    await page.click('#task-tools-select-btn');

    // 验证下拉框显示
    const dropdown = page.locator('#task-tools-dropdown');
    await expect(dropdown).toHaveClass(/show/);

    // 验证工具列表显示
    const options = dropdown.locator('.tools-option');
    await expect(options.first()).toBeVisible();
  });

  test('默认选中工具', async ({ page }) => {
    await page.click('#scheduler-add-task-btn');
    await page.click('#task-tools-select-btn');

    const dropdown = page.locator('#task-tools-dropdown');

    // 根据 AVAILABLE_TOOLS 的配置，默认选中前 4 个工具
    const checkboxes = dropdown.locator('input[type="checkbox"]');
    await expect(checkboxes.nth(0)).toBeChecked(); // Read
    await expect(checkboxes.nth(1)).toBeChecked(); // Write
    await expect(checkboxes.nth(2)).toBeChecked(); // Edit
    await expect(checkboxes.nth(3)).toBeChecked(); // Bash
    await expect(checkboxes.nth(4)).not.toBeChecked(); // Glob
  });

  test('显示已选择工具数量', async ({ page }) => {
    await page.click('#scheduler-add-task-btn');

    // 验证初始状态显示已选择工具
    const btn = page.locator('#task-tools-select-btn');
    await expect(btn.locator('.selected-text')).toContainText('已选择 4 个工具');
    await expect(btn.locator('.selected-count')).toHaveText('4');

    // 打开下拉框并取消选中一个工具
    await page.click('#task-tools-select-btn');
    await page.locator('#task-tools-dropdown input[value="Read"]').uncheck();

    // 验证数量更新
    await expect(btn.locator('.selected-text')).toContainText('已选择 3 个工具');
    await expect(btn.locator('.selected-count')).toHaveText('3');
  });

  test('未选择工具时显示默认文本', async ({ page }) => {
    await page.click('#scheduler-add-task-btn');
    await page.click('#task-tools-select-btn');

    // 取消所有选中
    const checkboxes = page.locator('#task-tools-dropdown input[type="checkbox"]');
    const count = await checkboxes.count();
    for (let i = 0; i < count; i++) {
      await checkboxes.nth(i).uncheck();
    }

    const btn = page.locator('#task-tools-select-btn');
    await expect(btn.locator('.selected-text')).toHaveText('选择工具...');
    await expect(btn.locator('.selected-count')).not.toBeVisible();
  });

  test('选择更多工具', async ({ page }) => {
    await page.click('#scheduler-add-task-btn');
    await page.click('#task-tools-select-btn');

    // 选择更多工具
    await page.locator('#task-tools-dropdown input[value="Glob"]').check();
    await page.locator('#task-tools-dropdown input[value="Grep"]').check();

    const btn = page.locator('#task-tools-select-btn');
    await expect(btn.locator('.selected-text')).toContainText('已选择 6 个工具');
  });

  test('点击外部关闭下拉框', async ({ page }) => {
    await page.click('#scheduler-add-task-btn');
    await page.click('#task-tools-select-btn');

    const dropdown = page.locator('#task-tools-dropdown');
    await expect(dropdown).toHaveClass(/show/);

    // 点击下拉框外部
    await page.locator('body').click({ position: { x: 10, y: 10 } });

    await expect(dropdown).not.toHaveClass(/show/);
  });

  test('定时任务工具选择', async ({ page }) => {
    await page.click('.scheduler-tab[data-tab="scheduled"]');
    await page.click('#scheduler-add-scheduled-btn');

    await page.click('#scheduled-tools-select-btn');

    const dropdown = page.locator('#scheduled-tools-dropdown');
    await expect(dropdown).toHaveClass(/show/);

    // 验证工具选项显示
    const options = dropdown.locator('.tools-option');
    await expect(options).toHaveCount(9); // 9 个可用工具
  });

  test('工具选项显示工具名称和描述', async ({ page }) => {
    await page.click('#scheduler-add-task-btn');
    await page.click('#task-tools-select-btn');

    const firstOption = page.locator('.tools-option').first();
    await expect(firstOption).toContainText('Read');
    await expect(firstOption).toContainText('读取文件');

    const secondOption = page.locator('.tools-option').nth(1);
    await expect(secondOption).toContainText('Write');
    await expect(secondOption).toContainText('创建文件');
  });

  test('工具选择在提交时正确发送', async ({ page }) => {
    await page.goto('/');
    await page.click('.nav-item[data-view="scheduler"]');

    // 拦截添加任务请求
    let receivedTools: string[] | null = null;
    await page.route('**/api/tasks', async route => {
      if (route.request().method() === 'POST') {
        const data = route.request().postDataJSON();
        receivedTools = data.tools ? data.tools.split(',') : null;

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ id: 'task-1' }),
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

    // 配置工具选择
    await page.click('#scheduler-add-task-btn');
    await page.click('#task-tools-select-btn');
    await page.locator('#task-tools-dropdown input[value="Read"]').check();
    await page.locator('#task-tools-dropdown input[value="Write"]').check();
    await page.locator('#task-tools-dropdown input[value="Edit"]').uncheck();
    await page.fill('#task-prompt', '测试');
    await page.click('#confirm-add-task-btn');

    // 验证工具正确发送
    expect(receivedTools).toBeTruthy();
    expect(receivedTools).toContain('Read');
    expect(receivedTools).toContain('Write');
    expect(receivedTools).not.toContain('Edit');
  });
});
