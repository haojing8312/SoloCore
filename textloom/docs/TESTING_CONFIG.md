# 配置一致性测试指南

## 概述

本文档说明如何使用配置一致性测试来防止配置字段映射错误导致的运行时问题。

## 背景：为什么需要这些测试？

### 问题场景

在 2025-11-29 修复的文件上传 500 错误中，我们发现了一个典型的配置字段映射错误：

```python
# ❌ 错误：web_configs.py 中
@property
def ACCESS_KEY_ID(self):
    return self._settings.obs_access_key_id  # 字段不存在！

# ✅ 正确：config.py 中实际定义的是
obs_access_key: Optional[str] = None
```

### 问题影响

- **即使用户配置了 MinIO**，错误仍会发生
- 原因：Python 的模块级导入会立即执行所有类的初始化
- 结果：`from utils.oss.HuaweiCloudOBS import HuaweiCloudOBS` 会抛出 `AttributeError`
- 表现：所有文件上传请求返回 500 错误

## 测试套件

### 1. 单元测试：配置字段一致性

**文件**: `tests/unit/test_config_consistency.py`

**覆盖场景**:
- ✅ `web_configs.py` 中的所有字段映射与 `config.py` 一致
- ✅ 所有存储配置类可以安全初始化（即使配置未完整）
- ✅ 配置字段类型正确
- ✅ 全局配置实例可访问
- ✅ `.env.example` 文档覆盖所有配置字段

**运行方式**:
```bash
cd textloom
uv run pytest tests/unit/test_config_consistency.py -v
```

**预期输出**:
```
test_huawei_obs_config_fields_mapping PASSED
test_minio_config_fields_mapping PASSED
test_storage_type_field_mapping PASSED
test_storage_factory_import_succeeds PASSED
test_minio_storage_import_succeeds PASSED
test_huawei_obs_storage_import_succeeds PASSED
test_settings_storage_fields_types PASSED
test_web_configs_global_instance_accessible PASSED
test_web_configs_used_by_storage_classes PASSED
test_env_example_covers_storage_fields PASSED

10 passed
```

### 2. 集成测试：存储服务

**文件**: `tests/integration/test_file_upload_integration.py`

**覆盖场景**:
- ✅ 存储工厂可以创建存储实例
- ✅ MinIO 存储配置处理
- ✅ 华为云 OBS 存储配置处理（即使不使用）
- ✅ 存储服务初始化
- ✅ 配置错误检测
- ✅ 配置类型反映正确

**运行方式**:
```bash
cd textloom
uv run pytest tests/integration/test_file_upload_integration.py -v
```

**预期输出**:
```
test_storage_factory_can_create_storage PASSED
test_storage_service_handles_minio_config PASSED
test_storage_service_handles_obs_config PASSED
test_upload_attachment_requires_storage PASSED
test_missing_storage_config_is_detectable PASSED
test_web_configs_reflects_current_storage_type PASSED

6 passed
```

## 快速测试脚本

### Linux / macOS / Git Bash

```bash
cd textloom
bash test_config.sh
```

### Windows (CMD/PowerShell)

```cmd
cd textloom
test_config.bat
```

## 测试失败时的处理

### 场景 1: 字段映射错误

**错误信息**:
```
WebConfigs.ACCESS_KEY_ID 访问失败: AttributeError: 'Settings' object has no attribute 'obs_access_key_id'
检查 web_configs.py 是否正确映射到 settings.obs_access_key
```

**解决方法**:
1. 检查 `config.py` 中的实际字段名（例如 `obs_access_key`）
2. 更新 `web_configs.py` 中的属性访问代码
3. 重新运行测试验证

### 场景 2: 缺少配置字段

**错误信息**:
```
Settings 缺少字段: minio_connect_timeout (WebConfigs.MINIO_CONNECT_TIMEOUT 需要它)
```

**解决方法**:
1. 在 `config.py` 的 `Settings` 类中添加缺失的字段
2. 更新 `.env.example` 添加文档
3. 重新运行测试验证

### 场景 3: 存储类导入失败

**错误信息**:
```
HuaweiCloudOBS 导入失败: AttributeError: ...
这通常是字段名不匹配导致的
```

**解决方法**:
1. 检查 `HuaweiCloudOBS.__init__()` 访问了哪些配置
2. 验证这些配置在 `web_configs.py` 和 `config.py` 中一致
3. 如果使用了 `getattr()` 访问可选字段，确保提供了默认值

## 最佳实践

### 1. 提交前运行测试

```bash
# 修改配置相关代码后，始终运行：
cd textloom
bash test_config.sh
```

### 2. 添加新存储后端时

如果添加新的存储后端（如 AWS S3），请：

1. **更新 `config.py`** 添加新配置字段
2. **更新 `web_configs.py`** 添加字段映射
3. **更新测试** `test_config_consistency.py` 添加新后端的测试
4. **更新 `.env.example`** 添加文档
5. **运行测试** 验证所有映射正确

### 3. 修改配置字段时

如果重命名或修改配置字段：

1. **同时更新** `config.py` 和 `web_configs.py`
2. **全局搜索** 确保没有遗漏的引用
3. **运行测试** 立即验证
4. **更新文档** `.env.example` 和迁移指南

## CI/CD 集成

建议在 CI pipeline 中添加配置测试：

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  config-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v1
      - name: Run config consistency tests
        run: |
          cd textloom
          uv run pytest tests/unit/test_config_consistency.py -v
          uv run pytest tests/integration/test_file_upload_integration.py -v
```

## 测试覆盖的问题类型

### ✅ 能检测到的问题

1. **字段名拼写错误** (`obs_access_key_id` vs `obs_access_key`)
2. **缺少必需字段** (新增配置未在 Settings 中定义)
3. **类型不匹配** (字段应该是 `float` 但定义为 `str`)
4. **模块导入失败** (所有存储类必须能安全导入)
5. **文档不完整** (`.env.example` 缺少配置说明)

### ❌ 无法检测到的问题

1. **运行时值错误** (配置值本身错误，如错误的端点 URL)
2. **网络连接问题** (MinIO 服务器不可达)
3. **权限问题** (存储桶访问权限配置错误)
4. **业务逻辑错误** (配置正确但使用方式错误)

这些问题需要通过集成测试和端到端测试来检测。

## 相关文件

- 配置定义: `textloom/config.py`
- 配置映射: `textloom/utils/web_configs.py`
- 单元测试: `textloom/tests/unit/test_config_consistency.py`
- 集成测试: `textloom/tests/integration/test_file_upload_integration.py`
- 配置文档: `textloom/.env.example`
- 快速测试: `textloom/test_config.sh`, `textloom/test_config.bat`

## 问题诊断流程

```
文件上传返回 500 错误
    ↓
查看后端日志
    ↓
发现 AttributeError: 'Settings' object has no attribute 'xxx'
    ↓
运行配置一致性测试
    ↓
uv run pytest tests/unit/test_config_consistency.py -v
    ↓
测试会指出具体哪个字段映射错误
    ↓
修复 web_configs.py 或 config.py
    ↓
重新运行测试验证
    ↓
重启后端服务应用修复
    ↓
验证文件上传功能恢复
```

## 总结

配置一致性测试是防御性编程的重要组成部分。它确保：

- ✅ **开发时**：IDE 提供正确的代码补全和类型检查
- ✅ **提交时**：自动化测试捕获配置错误
- ✅ **部署前**：CI pipeline 验证配置完整性
- ✅ **运行时**：所有存储后端可以安全初始化

**记住**：配置错误是生产环境中最常见的问题之一。预防胜于治疗！
