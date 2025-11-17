# Editly 在 Windows 上的安装指南

## 问题说明

在 Windows 上，Editly 依赖的 `canvas` 包需要编译原生模块，这需要：
1. Cairo 图形库
2. GTK 开发工具
3. Visual Studio Build Tools

由于这些依赖配置复杂，我们提供两种解决方案：

---

## ✅ 方案 A：使用 Docker（推荐）

### 优点
- 无需配置复杂的依赖
- 环境一致，避免版本冲突
- 一键运行

### 步骤

#### 1. 确保 Docker 已安装
```bash
docker --version
```

#### 2. 使用 Editly Docker 镜像

**方式 1：使用官方示例**
```bash
cd editly
docker-compose up editly
```

**方式 2：直接运行 Docker**
```bash
docker run --rm \
  -v E:/code/yzpd/SoloCore/editly/examples:/examples \
  -v E:/code/yzpd/SoloCore/output:/outputs \
  editly/editly \
  bash -c "cd /examples && editly single.json5 --out /outputs/test1.mp4"
```

---

## ⚠️ 方案 B：手动安装 Canvas 依赖（复杂）

### 步骤 1：安装 GTK（如果还没有）

下载 GTK for Windows:
https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases

安装到 `C:\GTK\`

### 步骤 2：配置环境变量

将以下路径添加到系统 `Path`:
```
C:\GTK\bin
```

添加以下环境变量:
```
GTK_BASEPATH=C:\GTK
PKG_CONFIG_PATH=C:\GTK\lib\pkgconfig
```

### 步骤 3：重启命令行，重新安装

```bash
cd editly
npm install
```

---

## 🚀 方案 C：使用全局安装的 Editly（最简单）

如果你只是想快速测试 Editly，可以使用全局安装：

```bash
npm install -g editly
```

然后直接使用:
```bash
editly examples/single.json5 --out output/test1.mp4
```

**注意**: 这种方式仍然需要 canvas 依赖，可能还是会遇到同样的问题。

---

## 💡 推荐方案：Docker

基于当前情况，我**强烈推荐使用 Docker 方案**，原因：
1. 不需要配置复杂的 Windows 依赖
2. 环境隔离，不会污染系统
3. 可以在生产环境中使用同样的镜像
4. 性能几乎无损耗

下一步：检查你是否安装了 Docker Desktop for Windows。
