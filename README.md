# Docker Image Transfer Tool

在中国大陆，直接从`Docker Hub`拉取镜像时常常会遇到网络限制问题（如 GFW），导致下载速度缓慢甚至无法访问。这个问题在服务器上使用开源软件的`docker-compose`一键部署方案时尤为明显，因为这些方案通常使用的都是Docker Hub镜像源，通常情况下，服务器无法通过VPN或代理访问外网。我们开发者的本地电脑通常可以通过科学上网工具（如VPN、代理等）顺利访问外网资源，虽然我们可以手动从docker-compose文件中提取镜像地址，然后通过`skopeo`工具将镜像转移到国内镜像仓库，但这个过程繁琐且耗时，特别是在处理包含多个服务的复杂部署时。

为了解决这个问题，我开发了这个docker镜像批量迁移工具。它可以自动从docker-compose文件中提取所有镜像地址，利用本地网络环境，通过封装skopeo工具，将这些外网的docker镜像批量转移到国内的镜像仓库，如阿里云、腾讯云、华为云等。这样的设计不仅避免了手动提取镜像地址的繁琐过程，还提高了镜像下载的速度和稳定性，大大简化了镜像迁移的流程。

#### 功能特点

- 自动读取docker-compose.yml文件中的所有镜像地址
- 支持环境变量解析（如 ${IMAGE_NAME}）
- 支持compose文件的include指令，可以合并多个compose文件
- 默认只处理没有 profiles 的服务镜像
- 可以通过 --all-profiles (-a) 参数选择处理所有镜像
- 自动将镜像转移到指定的容器镜像仓库
- 在执行转移前会显示详细的镜像列表和目标仓库并请求确认
- 提供自动化的认证文件生成工具，支持多账号配置

#### 安装说明

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置镜像仓库认证：

工具使用 auth.json 文件进行认证。在使用工具之前，需要先创建认证文件：

```bash
# 创建认证文件（需要指定目标镜像仓库地址）
python generate_auth.py registry.cn-hangzhou.aliyuncs.com

# 查看当前认证信息
python generate_auth.py --view

# 添加更多仓库认证信息
python generate_auth.py --merge registry.example.com
```

注意：认证文件默认会保存在当前目录下的 auth.json 中。

#### 使用说明

1. 准备配置文件：

a. 支持 include 指令的 compose 文件示例：

```yaml
include:
  - ./docker-compose-base.yml  # 包含基础配置
  - ./docker-compose-dev.yml   # 包含开发环境配置

services:
  web:
    image: nginx:latest
  mysql:
    image: ${MYSQL_IMAGE}
```

docker-compose-base.yml（基础配置文件）：
```yaml
version: '3.8'

services:
  ghost:
    image: ${GHOST_IMAGE:-ghost:5-alpine}
    ports:
      - "2368:2368"
    environment:
      - url=http://localhost:2368
    depends_on:
      - mysql

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_PASSWORD=${DB_PASSWORD:-secret}
```

docker-compose-dev.yml（开发环境配置文件）：
```yaml
version: '3.8'

services:
  adminer:
    image: adminer:4.8.1
    profiles: ["dev"]
    ports:
      - "8080:8080"
```

b. .env 文件示例（可选，用于环境变量）：
```bash
MYSQL_IMAGE=mysql:8.0.28
GHOST_IMAGE=ghost:5.71-alpine
```

使用这些配置文件时，工具会：
- 自动读取所有包含的文件中的镜像
- 正确处理环境变量
- 根据`--all-profiles`参数决定是否处理带有 profiles 的服务镜像

1. 运行脚本：
```bash
# 基本用法（必须指定目标仓库）
python image_transfer.py docker-compose.yml --target-registry registry.example.com/myproject

# 处理所有镜像，包括带有 profiles 的服务
python image_transfer.py docker-compose.yml -t registry.example.com/myproject -a
```

#### 环境变量解析

工具会按以下顺序解析镜像地址中的环境变量：
1. 首先查找同目录下的 .env 文件
2. 如果在 .env 文件中未找到，则查找系统环境变量
3. 如果都未找到，将保持原始变量形式

示例：
```yaml
# docker-compose.yml
services:
  api:
    image: ${API_IMAGE:-default/api:latest}  # 支持默认值语法
```

```bash
# .env
API_IMAGE=myregistry.com/api:v1.0
```

#### 认证文件生成

使用 `generate_auth.py` 脚本可以方便地生成和管理认证信息：

```bash
# 创建新的认证信息
python generate_auth.py registry_url

# 合并多个认证信息
python generate_auth.py --merge registry_url

# 查看当前认证信息
python generate_auth.py --view
```

---

## 单个镜像转移：

如果只需要转移单个镜像，可以设置`skopeo`别名：

```bash
# 设置别名（根据实际 auth.json 位置调整路径）
echo 'alias skopeo-copy="docker run --rm -it -v ~/.docker/auth.json:/root/.docker/config.json:ro --net=host quay.io/skopeo/stable:latest copy --dest-authfile /root/.docker/config.json"' >> ~/.zshrc
source ~/.zshrc   # 如果使用 zsh
# 或
echo 'alias skopeo-copy="docker run --rm -it -v ~/.docker/auth.json:/root/.docker/config.json:ro --net=host quay.io/skopeo/stable:latest copy --dest-authfile /root/.docker/config.json"' >> ~/.bashrc
source ~/.bashrc  # 如果使用 bash

# 使用示例
skopeo-copy docker://source-registry.com/image:tag docker://target-registry.com/image:tag

skopeo-copy docker://redis:5.0.14 docker://registry.cn-hangzhou.aliyuncs.com/luashiping/redis:5.0.14
```