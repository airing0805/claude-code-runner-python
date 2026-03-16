# 前端编码风格

> 本文件定义 web2 前端项目的编码规范，参考 CoPaw 技术栈（React 18 + TypeScript + Vite）。

## 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18.3.x | UI 框架 |
| TypeScript | 5.6.x | 类型系统 |
| Vite | 6.x | 构建工具 |
| React Router | 7.x | 路由管理 |
| Motion | 11.x | 动画库 |
| Lucide React | 0.468.x | 图标库 |
| react-markdown | 9.x | Markdown 渲染 |
| highlight.js | 代码高亮 |
 11.x || Mermaid | 11.x | 图表渲染 |

## 项目结构

```
web2/
├── src/
│   ├── components/       # 可复用组件
│   │   ├── ui/          # 基础 UI 组件
│   │   └── features/    # 功能组件
│   ├── pages/           # 页面组件
│   ├── hooks/           # 自定义 Hooks
│   ├── lib/             # 工具函数
│   ├── data/            # 静态数据
│   ├── types/           # 类型定义
│   ├── App.tsx         # 根组件
│   ├── main.tsx        # 入口文件
│   └── index.css       # 全局样式
├── public/              # 静态资源
├── index.html           # HTML 模板
└── vite.config.ts       # Vite 配置
```

## 组件规范

### 文件命名

```bash
# 组件文件 - PascalCase
Button.tsx
SessionList.tsx
TaskForm.tsx

# 组件目录 - PascalCase
components/
├── Button/
│   ├── Button.tsx
│   ├── Button.css
│   └── index.ts
```

### 组件结构

```tsx
import { useState, useCallback } from "react";
import type { FC } from "react";
import styles from "./Button.module.css";

interface ButtonProps {
  /** 按钮文字 */
  label: string;
  /** 点击回调 */
  onClick?: () => void;
  /** 是否禁用 */
  disabled?: boolean;
}

/**
 * 基础按钮组件
 */
export const Button: FC<ButtonProps> = ({
  label,
  onClick,
  disabled = false,
}) => {
  const [loading, setLoading] = useState(false);

  const handleClick = useCallback(() => {
    if (disabled || loading) return;
    setLoading(true);
    onClick?.();
  }, [disabled, loading, onClick]);

  return (
    <button
      className={styles.button}
      onClick={handleClick}
      disabled={disabled || loading}
    >
      {loading ? "加载中..." : label}
    </button>
  );
};
```

## Hooks 规范

### 命名约定

```typescript
// use + 动词/名词
useSessionList();
useTaskSubmit();
useAutoRefresh();

// 自定义 Hook 必须以 use 开头
export const useSessionList = () => { ... }
```

### Hook 结构

```typescript
import { useState, useEffect, useCallback } from "react";

interface UseSessionListOptions {
  /** 自动刷新间隔（毫秒） */
  refreshInterval?: number;
}

interface Session {
  id: string;
  title: string;
}

export const useSessionList = (options: UseSessionListOptions = {}) => {
  const { refreshInterval = 5000 } = options;

  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSessions = useCallback(async () => {
    try {
      setError(null);
      const data = await api.getSessions();
      setSessions(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
    const timer = setInterval(fetchSessions, refreshInterval);
    return () => clearInterval(timer);
  }, [fetchSessions, refreshInterval]);

  return {
    sessions,
    loading,
    error,
    refetch: fetchSessions,
  };
};
```

## 状态管理

### 组件状态

```tsx
// 简单状态 - useState
const [count, setCount] = useState(0);

// 复杂状态 - useReducer
const [state, dispatch] = useReducer(reducer, initialState);

// 派生状态 - useMemo
const filteredItems = useMemo(
  () => items.filter(filter),
  [items, filter]
);

// 回调缓存 - useCallback
const handleSubmit = useCallback(
  (data: FormData) => api.submit(data),
  [api]
);
```

### 全局状态

对于跨组件共享的状态，优先使用 Context：

```tsx
// contexts/SessionContext.tsx
import { createContext, useContext, type FC, type ReactNode } from "react";

interface Session {
  id: string;
  title: string;
}

interface SessionContextValue {
  currentSession: Session | null;
  setCurrentSession: (session: Session | null) => void;
}

const SessionContext = createContext<SessionContextValue | null>(null);

export const SessionProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const [currentSession, setCurrentSession] = useState<Session | null>(null);

  return (
    <SessionContext.Provider value={{ currentSession, setCurrentSession }}>
      {children}
    </SessionContext.Provider>
  );
};

export const useSession = () => {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error("useSession must be used within SessionProvider");
  }
  return context;
};
```

## 样式规范

### CSS Modules

```css
/* Button.module.css */
.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 16px;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.button:hover:not(:disabled) {
  transform: translateY(-1px);
}

.button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.primary {
  background: #3b82f6;
  color: white;
}
```

### 使用 CSS 变量

```css
/* index.css */
:root {
  --color-primary: #3b82f6;
  --color-primary-hover: #2563eb;
  --color-bg: #ffffff;
  --color-bg-secondary: #f9fafb;
  --color-text: #111827;
  --color-text-secondary: #6b7280;
  --radius: 6px;
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
}
```

## 类型定义

### 常用类型别名

```typescript
// API 响应类型
interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: string | null;
}

// 分页类型
interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
}

// 任务类型
type TaskStatus = "pending" | "running" | "completed" | "failed";

interface Task {
  id: string;
  prompt: string;
  status: TaskStatus;
  result?: string;
  createdAt: string;
}
```

## 事件处理

```tsx
// 表单事件
const handleSubmit = useCallback(
  (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    // 处理提交
  },
  []
);

// 输入事件
const handleInputChange = useCallback(
  (e: ChangeEvent<HTMLInputElement>) => {
    setValue(e.target.value);
  },
  []
);
```

## 导入顺序

```typescript
// 1. React 相关
import { useState, useCallback, type FC } from "react";

// 2. 第三方库
import { useNavigate } from "react-router-dom";
import { motion } from "motion";
import { Send, Loader2 } from "lucide-react";

// 3. 项目内部
import { useTaskSubmit } from "@/hooks/useTaskSubmit";
import { Button } from "@/components/ui/Button";
import type { Task } from "@/types";

// 4. 样式
import styles from "./TaskForm.module.css";
```

## 错误处理

```tsx
// 组件内错误边界
import { Component, type ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || <div>出错了</div>;
    }
    return this.props.children;
  }
}
```

## 性能优化

### 懒加载

```tsx
import { lazy, Suspense } from "react";

// 路由懒加载
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Settings = lazy(() => import("./pages/Settings"));

// 使用 Suspense 包裹
<Suspense fallback={<Loading />}>
  <Routes>
    <Route path="/" element={<Dashboard />} />
  </Routes>
</Suspense>;
```

### 虚拟列表

对于大量数据渲染，使用虚拟滚动：

```tsx
import { useVirtualizer } from "@tanstack/react-virtual";

const virtualizer = useVirtualizer({
  count: items.length,
  getScrollElement: () => parentRef.current,
  estimateSize: () => 35,
});
```

## 常用命令

```bash
# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 代码格式检查
npm run format:check

# 代码格式化
npm run format

# 代码检查
npm run lint
```
