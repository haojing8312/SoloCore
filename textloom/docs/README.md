# TextLoom 文档索引

本目录包含TextLoom项目的完整技术文档，按功能和主题分类组织。

## 📁 文档结构

### 🏗️ 架构文档 (`architecture/`)
- [架构审查发现](architecture/ARCHITECTURE_REVIEW_FINDINGS.md) - 系统架构分析和改进建议
- [日志系统增强总结](architecture/LOGGING_ENHANCEMENT_SUMMARY.md) - 统一日志系统的实施记录
- [架构待办事项](architecture/ARCHITECTURE_TODO.md) - 架构改进任务清单

### 🔒 安全文档 (`security/`)
- [安全审计报告](security/SECURITY_AUDIT_REPORT.md) - 完整的安全漏洞分析和修复
- [安全扫描报告](security/SECURITY_SCAN_REPORT.md) - 依赖包安全扫描结果
- [CORS安全审计报告](security/CORS_SECURITY_AUDIT_REPORT.md) - 跨域安全配置审计
- [硬编码凭据修复报告](security/SECURITY_HARDCODED_CREDENTIALS_FIX_REPORT.md) - 敏感信息安全修复
- [安全实施指南](security/SECURITY_IMPLEMENTATION_GUIDE.md) - 安全措施实施指导
- [安全流程](security/SECURITY_PROCESS.md) - 安全管理流程和规范
- [CORS安全配置](security/cors_security_configuration.md) - 跨域请求安全配置
- [JWT认证](security/jwt_authentication.md) - JWT认证机制实现文档

### ⚡ 性能文档 (`performance/`)
- [睡眠优化报告](performance/SLEEP_OPTIMIZATION_REPORT.md) - 异步睡眠优化记录
- [数据库优化分析](performance/database_optimization_analysis.md) - 数据库性能优化分析
- [数据库连接池优化](performance/database_connection_pool_optimization.md) - 连接池性能调优

### 🚀 部署文档 (`deployment/`)
- [CI/CD指南](deployment/README-CICD.md) - 持续集成和部署配置
- [部署指南](deployment/DEPLOYMENT.md) - 系统部署操作手册
- [生产架构](deployment/PRODUCTION_ARCHITECTURE.md) - 生产环境架构设计
- [SaaS实施路线图](deployment/SAAS_IMPLEMENTATION_ROADMAP.md) - SaaS化实施计划
- [配置文件管理](deployment/CONFIG_FILE_MANAGEMENT.md) - 配置文件管理规范

### 📊 监控文档 (`monitoring/`)
- [监控部署指南](monitoring/MONITORING_DEPLOYMENT_GUIDE.md) - Prometheus+Grafana监控系统部署

### 💾 备份文档 (`backup/`)
- [备份灾难恢复指南](backup/BACKUP_DISASTER_RECOVERY_GUIDE.md) - 数据备份和灾难恢复策略

### 💼 业务文档
- [TextLoom业务分析报告](TEXTLOOM_BUSINESS_ANALYSIS_REPORT.md) - 产品商业化分析与市场策略

### 📄 法律文档 (`legal/`)
- [隐私政策模板](legal/PRIVACY_POLICY_TEMPLATE.md) - 隐私政策标准模板
- [服务条款模板](legal/TERMS_OF_SERVICE_TEMPLATE.md) - 用户服务条款模板

### 🎬 功能文档
- [动态字幕功能](dynamic_subtitles.md) - TikTok风格动态字幕实现
- [视频生成请求示例](视频生成请求示例.txt) - API使用示例

### 🔌 API文档
- [API接口文档](API_DOCUMENTATION.md) - 完整的API接口规范，用于第三方系统对接

## 📖 快速导航

### 新用户入门
1. 阅读 [README.md](../README.md) 了解项目概述
2. 参考 [安全实施指南](security/SECURITY_IMPLEMENTATION_GUIDE.md) 了解安全配置
3. 查看 [CI/CD指南](deployment/README-CICD.md) 了解部署流程

### 开发者指南
- [架构审查发现](architecture/ARCHITECTURE_REVIEW_FINDINGS.md) - 了解系统设计和最佳实践
- [API接口文档](API_DOCUMENTATION.md) - 第三方系统对接指南
- [数据库优化分析](performance/database_optimization_analysis.md) - 数据库性能调优
- [JWT认证](security/jwt_authentication.md) - 认证机制实现

### 运维指南
- [监控部署指南](monitoring/MONITORING_DEPLOYMENT_GUIDE.md) - 系统监控配置
- [备份灾难恢复指南](backup/BACKUP_DISASTER_RECOVERY_GUIDE.md) - 数据保护策略
- [安全流程](security/SECURITY_PROCESS.md) - 安全管理规范

### 审计和合规
- [安全审计报告](security/SECURITY_AUDIT_REPORT.md) - 安全状态评估
- [安全扫描报告](security/SECURITY_SCAN_REPORT.md) - 漏洞扫描结果
- [性能优化记录](performance/) - 性能改进历史

## 🔄 文档维护

本文档结构遵循以下原则：
- **分类清晰**: 按功能域分类，便于查找
- **层次分明**: 从概述到详细实施的递进结构
- **实用导向**: 每个文档都有明确的使用场景
- **持续更新**: 随系统演进同步更新文档

如需添加新文档，请按照相应的功能分类放入对应目录，并更新本索引文件。