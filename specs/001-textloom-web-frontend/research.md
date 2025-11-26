# Research: TextLoom Web Frontend

**Date**: 2025-11-26
**Branch**: `001-textloom-web-frontend`

## Purpose

本文档记录 TextLoom Web Frontend 的技术选型研究和决策过程,解决 Technical Context 中的所有技术不确定性。

---

## 1. 前端框架选型

### Decision: React 18 + TypeScript

### Rationale:
1. **React 18 的优势**:
   - 并发渲染(Concurrent Rendering)提升用户体验
   - Suspense 和 Streaming SSR 支持(未来可扩展)
   - 自动批处理(Automatic Batching)优化性能
   - 社区生态成熟,组件库丰富

2. **TypeScript 的优势**:
   - 类型安全,减少运行时错误
   - 优秀的 IDE 支持(自动补全、重构)
   - 与后端 API 契约集成(通过 OpenAPI 生成类型)
   - 代码可维护性高

3. **项目适配性**:
   - TextLoom 需要轮询任务状态,React 的 useEffect 和自定义 hooks 非常适合
   - 文件上传、进度条、视频播放等交互需求与 React 组件化思想契合

### Alternatives Considered:
- **Vue 3**: easegen-front 已使用 Vue,但 TextLoom Frontend 需要独立技术栈,React 社区资源更丰富
- **Svelte**: 更小的打包体积,但生态不如 React 成熟,组件库选择有限
- **Next.js (SSR)**: 过度设计,TextLoom 是本地部署的单用户工具,不需要 SEO 和服务端渲染

---

## 2. 构建工具选型

### Decision: Vite 5

### Rationale:
1. **性能优势**:
   - 冷启动速度极快(~200ms vs Webpack ~2s)
   - HMR (热模块替换) 响应迅速
   - 基于 ESM 的开发服务器,按需编译

2. **开发体验**:
   - 开箱即用的 TypeScript、JSX、CSS Modules 支持
   - 插件生态完善(React、Tailwind、PWA 等)
   - 配置简单,学习曲线平缓

3. **生产优化**:
   - 基于 Rollup 的生产构建
   - 自动代码分割(Code Splitting)
   - Tree-shaking 和资源压缩

### Alternatives Considered:
- **Webpack**: 配置复杂,启动速度慢,不适合快速迭代
- **Create React App (CRA)**: 已停止维护,不推荐新项目使用
- **Parcel**: 性能不如 Vite,社区活跃度较低

---

## 3. UI 组件库选型

### Decision: shadcn/ui (Radix UI + Tailwind CSS)

### Rationale:
1. **无依赖锁定**:
   - 组件代码直接复制到项目中,完全可定制
   - 不会像 Material-UI 或 Ant Design 那样增加大量 bundle 体积
   - 避免版本升级带来的 breaking changes

2. **可访问性 (a11y)**:
   - 基于 Radix UI Primitives,完全符合 WAI-ARIA 标准
   - 键盘导航、屏幕阅读器支持开箱即用
   - 符合国际化无障碍要求

3. **设计一致性**:
   - 基于 Tailwind CSS,与现代设计趋势契合
   - 组件风格统一,易于维护
   - 支持暗黑模式(未来可扩展)

4. **适配性**:
   - prototype.html 采用 Apple 风格设计,shadcn/ui 的简洁风格与之契合
   - 组件丰富:Button, Card, Progress, Dialog, Select 等满足所有需求

### Alternatives Considered:
- **Ant Design**: 体积大(1MB+),设计风格偏向 B 端,不适合 TextLoom 的简洁定位
- **Material-UI (MUI)**: 依赖重,定制困难,Google Material 风格与产品设计不符
- **Chakra UI**: 性能不如 Radix UI,运行时样式解析有性能开销
- **手写组件**: 开发周期长,可访问性难以保证

---

## 4. 状态管理选型

### Decision: Zustand + TanStack Query

### Rationale:

#### Zustand (全局状态):
1. **轻量级**: 仅 1KB gzip,无需 Provider 包裹
2. **简单**: API 简洁,学习成本低(比 Redux/MobX 简单 10 倍)
3. **TypeScript 友好**: 类型推断完美,无需手动定义 Action 类型
4. **适用场景**: 管理 UI 状态(当前选中的模板、全局 loading、错误提示)

#### TanStack Query (服务端状态):
1. **专为异步数据设计**: 自动处理缓存、重试、轮询、失效
2. **减少样板代码**: 无需手动管理 loading/error/data 状态
3. **轮询支持**: `refetchInterval` 完美适配任务状态轮询需求
4. **适用场景**: 管理从后端 API 获取的数据(任务列表、任务详情、统计数据)

### Alternatives Considered:
- **Redux Toolkit**: 过度设计,TextLoom 状态简单不需要时间旅行调试
- **Context API + useReducer**: 手动管理缓存和重新获取逻辑,工作量大
- **Jotai/Recoil**: 原子化状态管理,适合复杂依赖关系,TextLoom 不需要

---

## 5. 路由选型

### Decision: React Router 6

### Rationale:
1. **行业标准**: React 生态最成熟的路由解决方案
2. **数据加载**: Loader API 支持在路由切换前预加载数据
3. **嵌套路由**: 支持布局组件复用(如统一的 Header/Sidebar)
4. **类型安全**: TypeScript 支持完善

### Alternatives Considered:
- **TanStack Router**: 新兴方案,类型安全更强,但生态不如 React Router 成熟
- **Wouter**: 轻量级,但功能有限,不支持嵌套路由

---

## 6. 数据可视化(图表)选型

### Decision: Recharts

### Rationale:
1. **React 原生**: 基于 React 组件,API 简洁直观
2. **响应式**: 自动适配容器尺寸,移动端友好
3. **图表类型丰富**: 支持饼图、折线图、柱状图等(满足统计页面需求)
4. **可定制性**: 支持自定义颜色、样式、工具提示

### Alternatives Considered:
- **Chart.js + react-chartjs-2**: 功能强大,但配置复杂,非 React 原生
- **Victory**: API 复杂,学习曲线陡峭
- **D3.js**: 功能最强,但开发成本高,适合复杂可视化场景

---

## 7. HTTP 客户端选型

### Decision: Axios

### Rationale:
1. **拦截器**: 统一处理请求/响应(添加 token、错误处理)
2. **取消请求**: 支持 AbortController,避免内存泄漏
3. **超时控制**: 防止长时间等待
4. **兼容性**: 自动处理浏览器兼容性问题

### Alternatives Considered:
- **Fetch API**: 原生支持,但需要手动处理错误、超时、拦截器
- **ky**: 轻量级,但功能不如 Axios 完整

---

## 8. 测试策略

### Decision: Vitest + React Testing Library + Playwright

### Rationale:

#### Vitest (单元测试):
- 与 Vite 无缝集成,配置简单
- 兼容 Jest API,迁移成本低
- 速度快(10x faster than Jest)

#### React Testing Library (组件测试):
- 测试用户行为而非实现细节
- 鼓励编写可维护的测试
- 与 Vitest 集成良好

#### Playwright (E2E 测试):
- 跨浏览器测试(Chromium, Firefox, WebKit)
- 可靠性高(自动等待元素可见)
- 调试体验好(Trace Viewer)

### Test Coverage Goals:
- **单元测试**: 工具函数、自定义 hooks (目标覆盖率 80%)
- **组件测试**: 关键 UI 组件(FileUpload, TaskCard, VideoPlayer)
- **E2E 测试**: 核心用户流程(P1 用户故事:上传文件 → 生成视频)

### Alternatives Considered:
- **Jest**: 配置复杂,启动慢
- **Cypress**: E2E 测试功能强,但不支持多标签页,Playwright 更灵活

---

## Summary

所有技术选型已完成,无遗留的 NEEDS CLARIFICATION。关键决策:
- **框架**: React 18 + TypeScript + Vite
- **UI**: shadcn/ui (Radix UI + Tailwind CSS)
- **状态**: Zustand(全局) + TanStack Query(服务端)
- **路由**: React Router 6
- **图表**: Recharts
- **测试**: Vitest + React Testing Library + Playwright
- **HTTP**: Axios
- **轮询**: TanStack Query refetchInterval
- **错误**: 分层处理(API 拦截器 + ErrorBoundary + Toast)

下一步: Phase 1 - 生成 data-model.md 和 API contracts。
