# Requirements Checklist: TextLoom Web Frontend

**Feature**: TextLoom Web Frontend  
**Branch**: `001-textloom-web-frontend`  
**Generated**: 2025-11-26  
**Source**: [spec.md](../spec.md)

## Purpose

此检查清单用于在实现过程中跟踪功能需求的完成状态。每完成一个需求,请在对应的复选框中打勾。

---

## User Story 1 - 文档上传并生成视频 (Priority: P1) 🎯 MVP

### Acceptance Scenarios

- [ ] **US1-S1**: 用户可以点击上传区域或拖拽 .md 文件到上传区域,文件成功上传并显示文件名、大小和成功提示
- [ ] **US1-S2**: 用户选择字幕模板卡片后,该卡片显示选中状态(边框高亮),其他卡片取消选中
- [ ] **US1-S3**: 用户点击"开始生成"按钮后,调用后端 API 创建任务并跳转到任务详情页面
- [ ] **US1-S4**: 任务详情页面每 3 秒轮询后端 API,更新进度条和百分比显示
- [ ] **US1-S5**: 任务状态变为 completed 后停止轮询,显示视频播放器和"下载视频"按钮
- [ ] **US1-S6**: 用户点击播放按钮后,视频在播放器中正常播放并显示播放控制条

### Related Functional Requirements

- [ ] **FR-001**: 支持点击上传区域或拖拽方式上传 Markdown (.md) 文件
- [ ] **FR-002**: 验证上传文件的格式(仅允许 .md 文件)和大小(不超过 10MB)
- [ ] **FR-003**: 显示至少 4 种字幕模板(Hype、Minimalist、Explosive、Vibrant)
- [ ] **FR-004**: 字幕模板卡片单选,清晰标识选中状态
- [ ] **FR-005**: 点击"开始生成"后调用 `/api/tasks/create` API
- [ ] **FR-006**: 任务创建成功后跳转到 `/tasks/:taskId` 页面
- [ ] **FR-007**: 任务详情页面每 3 秒轮询 `/api/tasks/:taskId/status` API
- [ ] **FR-008**: 显示实时进度条和百分比(0-100%)
- [ ] **FR-009**: 任务状态变为 `completed` 时停止轮询,显示视频播放器
- [ ] **FR-010**: 支持浏览器内播放视频(HTML5 video 元素)
- [ ] **FR-011**: 提供"下载视频"按钮,允许下载视频文件

### Success Criteria

- [ ] **SC-001**: 用户可在 30 秒内完成文件上传和任务创建流程
- [ ] **SC-002**: 任务状态轮询延迟不超过 3 秒
- [ ] **SC-003**: 视频播放器加载时间不超过 5 秒
- [ ] **SC-004**: 90% 的用户可在第一次尝试时成功创建视频任务

---

## User Story 2 - 查看和管理历史任务 (Priority: P2)

### Acceptance Scenarios

- [ ] **US2-S1**: 任务列表页面显示所有任务,每个任务卡片显示文件名、状态、创建时间和进度
- [ ] **US2-S2**: 点击状态标签(全部/进行中/已完成/失败)后只显示对应状态的任务
- [ ] **US2-S3**: 点击任务卡片后跳转到该任务的详情页面
- [ ] **US2-S4**: 点击"取消任务"按钮后调用后端 API,任务状态变为 cancelled
- [ ] **US2-S5**: 点击"删除"按钮后弹出确认对话框,确认后调用 API 删除任务
- [ ] **US2-S6**: 任务列表为空时显示空状态提示和"开始创建"按钮

### Related Functional Requirements

- [ ] **FR-012**: 任务列表页面显示所有历史任务(文件名、状态、创建时间、进度)
- [ ] **FR-013**: 支持按任务状态筛选(全部/进行中/已完成/失败)
- [ ] **FR-014**: 允许取消状态为 `processing` 的任务,调用 `/api/tasks/:taskId/cancel`
- [ ] **FR-015**: 允许删除状态为 `completed` 或 `failed` 的任务,需要用户确认后调用 `/api/tasks/:taskId`

### Success Criteria

- [ ] **SC-005**: 任务列表页面加载时间不超过 3 秒(即使有 100+ 个任务)
- [ ] **SC-008**: 用户可通过状态筛选在 5 秒内找到目标任务
- [ ] **SC-009**: 取消任务的响应时间不超过 2 秒
- [ ] **SC-010**: 删除任务后任务列表立即刷新(不超过 1 秒)

---

## User Story 3 - 查看数据统计和分析 (Priority: P3)

### Acceptance Scenarios

- [ ] **US3-S1**: 统计页面显示 4 个统计卡片(总任务数、今日生成数、成功率、平均耗时)
- [ ] **US3-S2**: 饼图显示任务状态分布(进行中/已完成/失败),每个扇区显示数量和百分比
- [ ] **US3-S3**: 折线图显示最近 7 天的任务生成数量趋势
- [ ] **US3-S4**: 统计数据在用户刷新页面后更新(无需实时更新)

### Related Functional Requirements

- [ ] **FR-016**: 统计页面显示总任务数、今日生成数、成功率和平均耗时 4 个指标
- [ ] **FR-017**: 显示任务状态分布饼图(进行中/已完成/失败的数量和百分比)
- [ ] **FR-018**: 显示最近 7 天的任务生成趋势折线图

### Success Criteria

- [ ] **SC-006**: 统计页面的图表渲染时间不超过 2 秒

---

## Edge Cases & Error Handling

- [ ] **EC-001**: 上传超过 10MB 的文件时显示错误提示"文件大小不能超过 10MB"
- [ ] **EC-002**: API 请求失败时显示友好错误提示(如"网络连接失败,请检查网络后重试")并提供"重试"按钮
- [ ] **EC-003**: 任务列表为空时显示空状态插图和引导文案;统计数据为空时显示"暂无数据"提示
- [ ] **EC-004**: 点击"开始生成"按钮后,按钮进入 loading 状态(显示 spinner),防止重复提交
- [ ] **EC-005**: 任务状态轮询失败 3 次后停止轮询,显示错误提示"无法获取任务状态,请刷新页面重试"
- [ ] **EC-006**: 视频 URL 无法加载或播放失败时显示错误提示"视频加载失败,请稍后重试"
- [ ] **EC-007**: 用户未选择字幕模板就点击"开始生成"时显示提示"请选择一个字幕模板"
- [ ] **EC-008**: 用户上传非 .md 文件时显示错误提示"仅支持 Markdown (.md) 文件"

### Related Functional Requirements

- [ ] **FR-019**: 所有 API 请求失败时显示友好的错误提示并提供重试选项
- [ ] **FR-020**: 防止用户重复提交表单(通过按钮 loading 状态)

### Success Criteria

- [ ] **SC-007**: 网络错误时在 1 秒内显示错误提示,95% 的用户理解错误原因

---

## Key Entities Implementation

- [ ] **VideoTask (视频任务)**: 实现包含 id, filename, status, progress, videoUrl, createdAt, completedAt 的数据结构
- [ ] **UploadedFile (上传文件)**: 实现包含 filename, size, uploadTime, fileUrl 的数据结构
- [ ] **SubtitleTemplate (字幕模板)**: 实现包含 id, name, previewImage, description 的数据结构
- [ ] **ScriptContent (脚本内容)**: 实现包含 taskId, scriptText, style, generatedAt 的数据结构

---

## Progress Summary

**Total Requirements**: 20 Functional Requirements + 14 User Story Scenarios + 10 Success Criteria + 8 Edge Cases + 4 Key Entities = **56 items**

**Completed**: 0 / 56 (0%)

---

## Notes

- 优先完成 User Story 1 (P1) - 这是 MVP 的核心功能
- User Story 2 和 3 可以在 MVP 完成后逐步添加
- 每完成一个需求后,立即在对应的复选框中打勾
- 如果发现规格说明中有不明确的地方,请在实现前向产品负责人澄清
