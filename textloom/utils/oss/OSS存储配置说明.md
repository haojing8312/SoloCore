# TextLoom OSS存储配置说明

## 概述

TextLoom现已支持OSS对象存储功能，可以根据配置选择华为云OBS或MinIO作为存储后端。在视频合成过程中，系统会自动将素材文件上传到云存储，并使用云存储URL进行视频合成，确保接口调用的正确性。

## 支持的存储类型

- **华为云OBS** (`huawei_obs`)
- **MinIO** (`minio`)

## 配置步骤

### 1. 环境变量配置

复制 `env.template` 为 `.env` 文件，并填入相应的配置：

```bash
cp env.template .env
```

### 2. 存储类型选择

在 `.env` 文件中设置存储类型：

```bash
# 选择存储类型: huawei_obs 或 minio
STORAGE_TYPE=huawei_obs
```

### 3. 华为云OBS配置

如果选择华为云OBS，需要配置以下参数：

```bash
# 华为云OBS配置
OBS_ACCESS_KEY_ID=your-obs-access-key-id
OBS_SECRET_ACCESS_KEY=your-obs-secret-access-key
OBS_ENDPOINT=https://obs.cn-north-4.myhuaweicloud.com
OBS_BUCKET_NAME=your-obs-bucket-name
OBS_DOMAIN_NAME=your-obs-domain-name
```

#### 获取华为云OBS配置信息：

1. **Access Key ID / Secret Access Key**: 
   - 登录华为云控制台
   - 进入"我的凭证" → "访问密钥"
   - 创建或查看已有的访问密钥

2. **Endpoint**: 
   - 根据你的bucket所在区域设置
   - 例如：`https://obs.cn-north-4.myhuaweicloud.com`

3. **Bucket Name**: 你创建的OBS存储桶名称

4. **Domain Name**: 
   - 可以使用默认域名：`bucket-name.obs.region.myhuaweicloud.com`
   - 或者配置的自定义域名

### 4. MinIO配置

如果选择MinIO，需要配置以下参数：

```bash
# MinIO配置
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=your-minio-access-key
MINIO_SECRET_KEY=your-minio-secret-key
MINIO_SECURE=false
MINIO_BUCKET_NAME=your-minio-bucket-name
MINIO_DOMAIN_NAME=your-minio-domain-name
```

#### MinIO配置说明：

1. **Endpoint**: MinIO服务器地址和端口
2. **Access Key / Secret Key**: MinIO的访问凭证
3. **Secure**: 是否使用HTTPS（true/false）
4. **Bucket Name**: MinIO存储桶名称
5. **Domain Name**: 访问域名，用于生成文件URL

## 使用方式

### 自动使用

配置完成后，系统会自动使用OSS存储：

1. **素材处理**: 下载的媒体文件会自动上传到云存储
2. **素材分析**: 分析完成后保存云存储URL
3. **视频生成**: 使用云存储URL而不是本地路径进行视频合成

### 手动使用存储工厂

你也可以在代码中直接使用存储工厂：

```python
from utils.oss.storage_factory import StorageFactory

# 获取当前配置的存储实例
storage = StorageFactory.get_storage()

# 上传文件
file_url = storage.upload_file("local_file.jpg", "images/uploaded_file.jpg")
print(f"文件URL: {file_url}")

# 指定存储类型
huawei_storage = StorageFactory.get_storage_by_type("huawei_obs")
minio_storage = StorageFactory.get_storage_by_type("minio")
```

## 测试配置

运行测试脚本验证配置是否正确：

```bash
python test_oss_config.py
```

该脚本会测试：
- 配置文件加载
- 存储工厂初始化
- 文件上传功能
- 各种存储类型的兼容性

## 文件结构

OSS存储相关的文件结构：

```bash
utils/
└── oss/
    ├── __init__.py                 # 模块初始化
    ├── storage_interface.py        # 存储接口定义
    ├── storage_factory.py          # 存储工厂
    ├── HuaweiCloudOBS.py          # 华为云OBS实现
    ├── MinioStorage.py            # MinIO实现
    ├── MinioStorageAsync.py       # MinIO异步实现
    └── usage_example.py           # 使用示例
utils/
└── web_configs.py                 # 配置适配器
```

## 故障排除

### 常见问题

1. **配置加载失败**
   - 检查 `.env` 文件是否存在
   - 确认环境变量名称正确

2. **华为云OBS连接失败**
   - 验证Access Key和Secret Key是否正确
   - 检查Endpoint是否对应正确的区域
   - 确认存储桶是否存在且有相应权限

3. **MinIO连接失败**
   - 确认MinIO服务是否正常运行
   - 检查网络连接和端口
   - 验证访问凭证是否正确

4. **文件上传失败**
   - 检查存储桶权限设置
   - 确认网络连接稳定
   - 查看日志文件获取详细错误信息

### 日志查看

查看应用日志了解详细错误信息：

```bash
tail -f logs/app.log
```

## 性能优化建议

1. **选择合适的存储区域**：选择距离服务器较近的存储区域
2. **配置CDN**：对于频繁访问的文件，建议配置CDN加速
3. **文件命名规范**：使用有意义的文件名和目录结构
4. **定期清理**：定期清理不需要的临时文件

## 安全建议

1. **访问密钥安全**：
   - 不要在代码中硬编码访问密钥
   - 定期轮换访问密钥
   - 使用最小权限原则

2. **网络安全**：
   - 生产环境建议使用HTTPS
   - 配置适当的防火墙规则

3. **存储桶权限**：
   - 设置合适的存储桶访问权限
   - 避免公开读写权限

## 更新日志

- **v1.0.0**: 初始版本，支持华为云OBS和MinIO
- 支持自动上传素材文件到云存储
- 视频合成接口使用云存储URL
- 提供配置测试脚本 