# 认证模块文档

## 概述

前端认证模块实现了用户登录、注册、登出和令牌管理功能。

## 文件结构

```
web/static/modules/auth/
├── auth.js           # 核心认证逻辑
├── authUI.js         # UI 交互逻辑
└── README.md         # 本文档

web/static/css/
└── auth.css          # 认证模块样式
```

## 核心模块

### Auth 模块 (auth.js)

提供核心认证功能：

- **login(username, password)** - 用户登录
- **register(username, password, name)** - 用户注册
- **logout()** - 用户登出
- **getCurrentUser()** - 获取当前用户信息
- **isLoggedIn()** - 检查登录状态
- **getToken()** - 获取访问令牌
- **refreshToken()** - 刷新访问令牌

#### 特性

1. **自动令牌刷新**
   - 每5分钟检查令牌过期时间
   - 令牌将在10分钟内过期时自动刷新
   - 令牌过期后自动登出

2. **请求拦截**
   - 自动拦截所有 fetch 请求
   - 为 API 请求自动添加 `Authorization` 头
   - 认证接口请求不添加认证头

3. **令牌存储**
   - 使用 localStorage 存储令牌和用户信息
   - 存储键名：
     - `auth_access_token` - 访问令牌
     - `auth_refresh_token` - 刷新令牌
     - `auth_user_info` - 用户信息
     - `auth_token_expires_at` - 令牌过期时间戳

### AuthUI 模块 (authUI.js)

处理登录/注册对话框和导航栏更新：

- **initLoginDialog()** - 初始化登录对话框
- **initRegisterDialog()** - 初始化注册对话框
- **updateNavbar()** - 更新导航栏显示
- **checkPasswordStrength(password)** - 密码强度检查

#### 对话框特性

1. **登录对话框**
   - 用户名（邮箱）输入
   - 密码输入
   - 错误提示显示
   - 加载状态显示
   - 跳转到注册链接

2. **注册对话框**
   - 用户名（邮箱）输入（带格式验证）
   - 显示名称输入
   - 密码输入（带强度提示）
   - 确认密码输入
   - 密码强度实时检查
   - 密码一致性验证
   - 注册成功后自动登录
   - 跳转到登录链接

## API 接口

### 登录

```
POST /api/auth/login

Request:
{
  "username": "user@example.com",
  "password": "password123"
}

Response:
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 注册

```
POST /api/auth/register

Request:
{
  "username": "user@example.com",
  "password": "password123",
  "name": "User Name"
}

Response (201 Created):
{
  "user_id": "...",
  "username": "...",
  "name": "..."
}
```

### 获取当前用户

```
GET /api/auth/me
Authorization: Bearer {token}

Response:
{
  "user_id": "...",
  "username": "...",
  "name": "...",
  "api_key": "..."
}
```

### 刷新令牌

```
POST /api/auth/refresh

Request:
{
  "refresh_token": "..."
}

Response:
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

## 使用示例

### 在 JavaScript 中使用

```javascript
// 检查登录状态
if (Auth.isLoggedIn()) {
    const user = Auth.getUser();
    console.log('当前用户:', user.name);
}

// 手动登录
const result = await Auth.login('user@example.com', 'password123');
if (result.success) {
    console.log('登录成功');
} else {
    console.error('登录失败:', result.error);
}

// 手动登出
Auth.logout();
```

### 在 HTML 中使用

HTML 模板已经包含认证 UI，无需额外代码。认证模块会在页面加载时自动初始化。

## 安全特性

1. **XSS 防护**
   - 所有用户输入在显示前都经过 HTML 转义
   - 使用 `escapeHtml()` 方法处理用户名、显示名称等

2. **密码安全**
   - 密码输入框使用 `type="password"`
   - 密码强度验证（至少8位，包含字母和数字）
   - 密码一致性验证

3. **错误处理**
   - 登录失败显示通用错误信息
   - 不暴露具体的用户名或密码错误
   - 网络错误友好提示

4. **令牌管理**
   - 访问令牌存储在 localStorage
   - 令牌过期自动刷新
   - 刷新令牌失效后自动登出

## 响应式设计

认证 UI 支持以下断点：

- **桌面端** (> 768px)
  - 正常显示所有元素
  - 对话框最大宽度 400px

- **平板端** (768px - 1024px)
  - 适当调整间距和字体大小

- **移动端** (< 768px)
  - 认证按钮垂直排列
  - 对话框最大宽度 90%
  - 用户名显示截断

- **小屏移动端** (< 480px)
  - 认证区域全宽显示
  - 用户信息垂直排列

## 样式定制

认证模块使用 CSS 变量，可以通过修改以下变量来自定义样式：

```css
/* 在你的自定义 CSS 中覆盖 */
:root {
    --primary-color: var(--violet-600);
    --primary-hover: var(--violet-700);
    --danger-color: var(--rose-500);
    --success-color: var(--emerald-500);
    --warning-color: var(--amber-500);
}
```

## 调试

### 检查登录状态

在浏览器控制台中：

```javascript
// 检查是否登录
Auth.isLoggedIn()

// 获取当前用户
Auth.getUser()

// 获取令牌
Auth.getToken()

// 检查令牌过期时间
new Date(parseInt(localStorage.getItem('auth_token_expires_at')))
```

### 清除认证状态

```javascript
// 手动登出
Auth.logout()

// 或直接清除 localStorage
localStorage.clear()
```

## 浏览器兼容性

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- 移动端浏览器（iOS Safari, Chrome Mobile）

## 测试

后端认证 API 已通过单元测试和集成测试：

```bash
# 运行认证测试
uv run pytest tests/test_auth.py -v

# 运行认证集成测试
uv run pytest tests/test_auth_integration.py -v
```

## 注意事项

1. **localStorage 安全性**
   - localStorage 易受 XSS 攻击
   - 敏感操作建议使用 httpOnly cookie
   - 当前实现仅适用于非高安全场景

2. **令牌刷新**
   - 令牌刷新失败会导致自动登出
   - 用户需要重新登录
   - 建议在刷新失败时提示用户

3. **并发请求**
   - 多个并发请求同时刷新令牌时，可能需要额外处理
   - 当前实现为简单刷新，未处理并发场景

## 未来改进

1. **httpOnly Cookie**
   - 将令牌存储在 httpOnly cookie 中
   - 提高 XSS 防护能力

2. **记住我功能**
   - 延长刷新令牌有效期
   - 30天内自动登录

3. **多因素认证**
   - 支持 2FA/MFA
   - 增强账户安全

4. **社交登录**
   - 支持 OAuth2.0
   - GitHub、Google 等第三方登录

5. **令牌并发刷新**
   - 防止多个请求同时刷新令牌
   - 使用请求队列或锁机制
