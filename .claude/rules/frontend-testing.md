# 前端测试规范

> 本文件定义 web2 前端项目的测试策略，参考 CoPaw 技术栈。

## 测试覆盖率要求

- **最低覆盖率: 80%**
- **组件测试: 100%**
- **Hooks 测试: 100%**
- **工具函数: 100%**

## 测试工具

| 工具 | 用途 |
|------|------|
| Vitest | 单元测试框架 |
| React Testing Library | 组件测试 |
| @testing-library/jest-dom | DOM 断言 |
| @testing-library/user-event | 用户事件模拟 |
| msw | HTTP 拦截 Mock |
| @vitest/coverage-v8 | 覆盖率报告 |

## 安装测试依赖

```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom @vitest/coverage-v8
```

## 测试结构

```
web2/
├── src/
│   └── ...
├── tests/
│   ├── components/        # 组件测试
│   │   ├── Button.test.tsx
│   │   └── SessionList.test.tsx
│   ├── hooks/           # Hook 测试
│   │   └── useSessionList.test.ts
│   ├── lib/             # 工具函数测试
│   │   └── api.test.ts
│   ├── setup.ts         # 测试环境配置
│   └── vitest.config.ts # Vitest 配置
```

## Vitest 配置

```typescript
// vitest.config.ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
    include: ["tests/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      exclude: [
        "node_modules/",
        "tests/",
        "**/*.d.ts",
        "**/*.config.ts",
      ],
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

## 测试环境配置

```typescript
// tests/setup.ts
import "@testing-library/jest-dom";

// Mock window.matchMedia
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));
```

## 组件测试

### 基本组件测试

```tsx
// tests/components/Button.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "@/components/ui/Button";

describe("Button", () => {
  it("renders with label", () => {
    render(<Button label="点击我" />);
    expect(screen.getByRole("button")).toHaveTextContent("点击我");
  });

  it("calls onClick when clicked", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();

    render(<Button label="点击我" onClick={onClick} />);
    await user.click(screen.getByRole("button"));

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("is disabled when disabled prop is true", () => {
    render(<Button label="点击我" disabled />);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("shows loading state", () => {
    render(<Button label="点击我" loading />);
    expect(screen.getByText("加载中...")).toBeInTheDocument();
  });
});
```

### 复杂组件测试

```tsx
// tests/components/SessionList.test.tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SessionList } from "@/components/features/SessionList";

// Mock API
vi.mock("@/lib/api", () => ({
  getSessions: vi.fn().mockResolvedValue([
    { id: "1", title: "Session 1" },
    { id: "2", title: "Session 2" },
  ]),
  deleteSession: vi.fn().mockResolvedValue(undefined),
}));

describe("SessionList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state initially", () => {
    render(<SessionList />);
    expect(screen.getByText("加载中...")).toBeInTheDocument();
  });

  it("renders sessions after loading", async () => {
    render(<SessionList />);

    await waitFor(() => {
      expect(screen.getByText("Session 1")).toBeInTheDocument();
      expect(screen.getByText("Session 2")).toBeInTheDocument();
    });
  });

  it("deletes session when delete button clicked", async () => {
    const user = userEvent.setup();
    const { deleteSession } = await import("@/lib/api");

    render(<SessionList />);

    await waitFor(() => {
      expect(screen.getByText("Session 1")).toBeInTheDocument();
    });

    const deleteButton = screen.getAllByRole("button", { name: /删除/i })[0];
    await user.click(deleteButton);

    expect(deleteSession).toHaveBeenCalledWith("1");
  });
});
```

## Hooks 测试

### 自定义 Hook 测试

```tsx
// tests/hooks/useCounter.test.ts
import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useCounter } from "@/hooks/useCounter";

describe("useCounter", () => {
  it("initializes with default value", () => {
    const { result } = renderHook(() => useCounter());
    expect(result.current.count).toBe(0);
  });

  it("initializes with provided value", () => {
    const { result } = renderHook(() => useCounter(10));
    expect(result.current.count).toBe(10);
  });

  it("increments count", () => {
    const { result } = renderHook(() => useCounter());

    act(() => {
      result.current.increment();
    });

    expect(result.current.count).toBe(1);
  });

  it("decrements count", () => {
    const { result } = renderHook(() => useCounter(5));

    act(() => {
      result.current.decrement();
    });

    expect(result.current.count).toBe(4);
  });

  it("resets count", () => {
    const { result } = renderHook(() => useCounter(10));

    act(() => {
      result.current.reset();
    });

    expect(result.current.count).toBe(0);
  });
});
```

### 异步 Hook 测试

```tsx
// tests/hooks/useSessionList.test.ts
import { describe, it, expect, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useSessionList } from "@/hooks/useSessionList";

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

describe("useSessionList", () => {
  it("fetches sessions", async () => {
    const { result } = renderHook(() => useSessionList(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(2);
  });

  it("handles error", async () => {
    // Mock error case
    const { result } = renderHook(() => useSessionList(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeDefined();
  });
});
```

## 工具函数测试

```tsx
// tests/lib/api.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiClient } from "@/lib/api";

describe("apiClient", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getSessions", () => {
    it("returns sessions on success", async () => {
      const mockSessions = [
        { id: "1", title: "Test Session" },
      ];

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: mockSessions }),
      });

      const result = await apiClient.getSessions();
      expect(result).toEqual(mockSessions);
    });

    it("throws error on failure", async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      await expect(apiClient.getSessions()).rejects.toThrow("请求失败");
    });
  });
});
```

## 集成测试

### 页面测试

```tsx
// tests/pages/Home.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { Home } from "@/pages/Home";

const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};

describe("Home Page", () => {
  it("renders hero section", () => {
    renderWithRouter(<Home />);
    expect(screen.getByText(/Claude Code Runner/)).toBeInTheDocument();
  });

  it("has navigation links", () => {
    renderWithRouter(<Home />);
    expect(screen.getByRole("link", { name: /开始/i })).toBeInTheDocument();
  });
});
```

## 运行测试

```bash
# 运行所有测试
npm run test

# 运行并监听文件变化
npm run test:watch

# 运行覆盖率
npm run test:coverage

# 运行特定文件
npm run test:watch SessionList

# 生成 HTML 覆盖率报告
npm run test:coverage -- --reporter html
```

## 测试检查清单

- [ ] 所有组件有对应测试
- [ ] 所有自定义 Hook 有测试
- [ ] 工具函数 100% 覆盖
- [ ] 边界条件已覆盖
- [ ] 错误状态已测试
- [ ] 异步流程已测试
- [ ] 用户交互已测试
- [ ] 测试描述清晰
