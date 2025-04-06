# Docker Image Transfer Tool

一个用于在不同 Docker 镜像仓库之间批量转移镜像的工具。支持从 docker-compose.yml 文件中读取镜像列表，并自动将镜像转移到目标仓库，同时保持原有的组织/项目结构。

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