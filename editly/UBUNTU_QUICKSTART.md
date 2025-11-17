# Editly Ubuntu 服务器快速开始指南

> 5 分钟在 Ubuntu 服务器上安装和测试 Editly

---

## 🚀 方法 1：一键安装（推荐）

### 步骤 1：上传文件到服务器

将整个 `editly` 目录上传到你的 Ubuntu 服务器：

```bash
# 在本地 Windows 上（使用 scp 或 WinSCP）
scp -r E:\code\yzpd\SoloCore\editly user@your-server:/home/user/
```

### 步骤 2：SSH 连接到服务器

```bash
ssh user@your-server
```

### 步骤 3：运行安装脚本

```bash
cd ~/editly
chmod +x setup_ubuntu.sh
./setup_ubuntu.sh
```

**安装时间**: 约 3-5 分钟

### 步骤 4：运行第一个测试

```bash
# 测试 Editly CLI
node dist/cli.js --version

# 生成示例视频
node dist/cli.js examples/single.json5 --out output/test1.mp4

# 检查输出
ls -lh output/test1.mp4
```

---

## 📋 方法 2：手动安装

### 1. 更新系统

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### 2. 安装 Node.js 18

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 验证
node --version
npm --version
```

### 3. 安装 FFmpeg

```bash
sudo apt-get install -y ffmpeg

# 验证
ffmpeg -version
ffprobe -version
```

### 4. 安装 Canvas 依赖

```bash
sudo apt-get install -y \
    libcairo2-dev \
    libpango1.0-dev \
    libjpeg-dev \
    libgif-dev \
    librsvg2-dev \
    build-essential
```

### 5. 构建 Editly

```bash
cd ~/editly
npm install
npm run build
```

### 6. 验证安装

```bash
node dist/cli.js --version
node dist/cli.js --help
```

---

## 🎬 运行测试

### 测试 1：基础幻灯片

```bash
# 创建测试配置
cat > test1_slideshow.json5 << 'EOF'
{
  outPath: "output/test1_slideshow.mp4",
  width: 1080,
  height: 1920,
  fps: 30,
  clips: [
    {
      duration: 3,
      layers: [
        {
          type: "fill-color",
          color: "#0066cc"
        },
        {
          type: "title",
          text: "测试标题 - Editly 正常工作！",
          textColor: "#ffffff"
        }
      ]
    },
    {
      duration: 3,
      layers: [
        {
          type: "fill-color",
          color: "#ff6600"
        },
        {
          type: "title",
          text: "第二个场景",
          textColor: "#ffffff"
        }
      ]
    }
  ]
}
EOF

# 运行测试
node dist/cli.js test1_slideshow.json5
```

### 测试 2：图片幻灯片

```bash
# 下载测试图片（或使用你自己的）
mkdir -p test_images
wget -O test_images/img1.jpg https://picsum.photos/1080/1920
wget -O test_images/img2.jpg https://picsum.photos/1080/1920

# 创建配置
cat > test2_images.json5 << 'EOF'
{
  outPath: "output/test2_images.mp4",
  width: 1080,
  height: 1920,
  clips: [
    {
      duration: 3,
      transition: { name: "fade", duration: 0.5 },
      layers: [
        {
          type: "image",
          path: "test_images/img1.jpg"
        }
      ]
    },
    {
      duration: 3,
      transition: { name: "crosswarp", duration: 0.5 },
      layers: [
        {
          type: "image",
          path: "test_images/img2.jpg"
        }
      ]
    }
  ]
}
EOF

# 运行测试
node dist/cli.js test2_images.json5
```

### 测试 3：自定义字幕（Fabric.js）

```bash
cat > test3_subtitle.json5 << 'EOF'
{
  outPath: "output/test3_subtitle.mp4",
  width: 1080,
  height: 1920,
  clips: [
    {
      duration: 5,
      layers: [
        { type: "fill-color", color: "#000000" },
        {
          type: "fabric",
          func: `
            ({ fabric, canvas, params }) => {
              const text = new fabric.Text('自定义字幕测试\\n精确位置控制', {
                left: 100,
                top: 1700,
                fontSize: 60,
                fill: '#ffffff',
                stroke: '#ff0000',
                strokeWidth: 3,
                textAlign: 'center'
              });
              canvas.add(text);
            }
          `
        }
      ]
    }
  ]
}
EOF

node dist/cli.js test3_subtitle.json5
```

---

## 📥 下载测试视频到本地

### 方法 1：使用 scp

```bash
# 在本地 Windows 上运行
scp user@your-server:~/editly/output/*.mp4 E:\code\yzpd\SoloCore\output\
```

### 方法 2：使用 WinSCP

1. 连接到服务器
2. 导航到 `~/editly/output/`
3. 拖拽文件到本地

### 方法 3：使用 Web 服务器

在服务器上临时启动一个 HTTP 服务器：

```bash
cd ~/editly/output
python3 -m http.server 8000
```

然后在浏览器访问：
```
http://your-server-ip:8000/
```

---

## 🔍 性能测试

### 测试不同规格视频的生成时间

```bash
# 创建性能测试脚本
cat > benchmark.sh << 'EOF'
#!/bin/bash

echo "=== Editly 性能测试 ==="
echo ""

# 测试 1: 30 秒 1080p 视频
echo "测试 1: 30秒 1080x1920 @30fps"
time node dist/cli.js examples/single.json5 --out output/bench_30s.mp4

# 测试 2: 60 秒视频
echo ""
echo "测试 2: 60秒 1080x1920 @30fps"
# TODO: 创建 60 秒配置

echo ""
echo "=== 测试完成 ==="
EOF

chmod +x benchmark.sh
./benchmark.sh
```

---

## ⚙️ 系统要求建议

### 最低配置
- CPU: 2 核
- 内存: 4GB
- 磁盘: 10GB 可用空间

### 推荐配置（生产环境）
- CPU: 4 核+
- 内存: 8GB+
- 磁盘: 50GB+ SSD

### 性能参考
| 视频规格 | 时长 | 预期生成时间 (4核) |
|---------|------|------------------|
| 1080x1920 @30fps | 30s | 1-2 分钟 |
| 1080x1920 @30fps | 60s | 2-4 分钟 |
| 720x1280 @30fps | 30s | 30-60 秒 |

---

## 🐛 故障排查

### 问题 1：`node: command not found`

**解决**:
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### 问题 2：`canvas` 构建失败

**解决**:
```bash
sudo apt-get install -y \
    libcairo2-dev \
    libpango1.0-dev \
    libjpeg-dev \
    libgif-dev \
    librsvg2-dev \
    build-essential

cd ~/editly
rm -rf node_modules
npm install
```

### 问题 3：`ffmpeg: command not found`

**解决**:
```bash
sudo apt-get install -y ffmpeg
```

### 问题 4：权限错误

**解决**:
```bash
# 修复文件权限
chmod +x dist/cli.js
chmod +x setup_ubuntu.sh

# 修复目录权限
chmod -R 755 ~/editly
```

---

## 📊 验收标准

### ✅ 阶段 1.1 完成标准

- [ ] Node.js 安装成功 (v12+)
- [ ] FFmpeg 安装成功
- [ ] Editly 构建成功
- [ ] `node dist/cli.js --version` 正常输出
- [ ] 测试 1 (幻灯片) 生成成功
- [ ] 测试 2 (图片) 生成成功
- [ ] 测试 3 (字幕) 生成成功
- [ ] 视频文件可正常播放

---

## 🚀 下一步

完成上述测试后，进入 **阶段 1.2：运行基础功能测试**

查看详细计划：
```bash
cat ../docs/IMPLEMENTATION_ROADMAP.md
```

---

**准备好了吗？立即开始！** 🎬

```bash
# 一键安装
./setup_ubuntu.sh

# 运行测试
node dist/cli.js examples/single.json5 --out output/test1.mp4
```
