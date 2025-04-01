# Docker Image Transfer Tool

这个工具用于将 docker-compose 文件中的镜像批量转移到阿里云容器镜像服务。

## 前置条件

1. 安装 Python 3.6 或更高版本
2. 安装 Docker（如果使用推荐的 Docker 方式运行 skopeo）或安装 skopeo
3. 安装所需的 Python 依赖

## 安装

1. 配置 skopeo：

推荐方式 - 使用 Docker 运行 skopeo（避免版本依赖问题）：
在你的 shell 配置文件（如 ~/.bashrc 或 ~/.zshrc）中添加以下别名之一：

方式一 - 使用本地 Docker 认证（推荐）：
```bash
# 在 Linux/macOS 中添加以下内容到 ~/.bashrc 或 ~/.zshrc
alias skopeo='docker run --rm -it -v ${PWD}:/work:z -v ${HOME}/.docker:/root/.docker:ro -w /work --net=host quay.io/skopeo/stable:latest'
```

方式二 - 使用独立认证文件：
```bash
# 在 Linux/macOS 中添加以下内容到 ~/.bashrc 或 ~/.zshrc
alias skopeo='docker run --rm -it -v ${PWD}:/work:z -v ${PWD}/auth.json:/root/.docker/config.json:ro -w /work --net=host quay.io/skopeo/stable:latest'
```

添加后执行以下命令使配置生效：
```bash
source ~/.bashrc  # 如果使用 bash
# 或
source ~/.zshrc   # 如果使用 zsh
```

替代方式 - 直接安装 skopeo：
```bash
# macOS
brew install skopeo

# Ubuntu
sudo apt-get install skopeo
```
注意：直接安装可能会遇到版本兼容性问题，建议使用 Docker 方式。

2. 安装 Python 依赖：
```bash
pip install -r requirements.txt
```

## 使用方法

1. 配置镜像仓库认证（选择以下任一方式）：

方式一 - 使用本地 Docker 认证（推荐）：
```bash
# Docker 登录（如果还没有登录过）
docker login registry.cn-hangzhou.aliyuncs.com

# 登录信息会自动从 ~/.docker/config.json 读取
# 如果需要使用 skopeo 重新登录，执行：
skopeo login registry.cn-hangzhou.aliyuncs.com
```

方式二 - 使用独立认证文件：

使用提供的 `generate_auth.py` 脚本生成认证文件：

```bash
# 1. 直接复制现有的 Docker 认证信息（如果已经用 docker login 登录过）
python3 generate_auth.py --copy-docker

# 2. 创建新的认证信息（不会影响现有的 Docker 登录）
python3 generate_auth.py

# 3. 添加新的认证信息到现有的 auth.json（用于多账号认证）
python3 generate_auth.py --merge

# 4. 指定其他镜像仓库地址
python3 generate_auth.py registry.example.com

# 查看更多用法：
python3 generate_auth.py --help
```

2. 运行脚本：
```bash
# 默认只处理没有 profiles 的服务镜像，使用默认目标仓库
python3 image_transfer.py docker-compose.yml

# 处理所有镜像，包括带有 profiles 的服务
python3 image_transfer.py docker-compose.yml --all-profiles

# 指定目标仓库
python3 image_transfer.py docker-compose.yml --target-registry registry.example.com/myproject

# 使用简短参数形式
python3 image_transfer.py docker-compose.yml -t registry.example.com/myproject -a
```

## 功能说明

- 自动读取 docker-compose.yml 文件中的所有镜像地址
- 默认只处理没有 profiles 的服务镜像（通常是核心服务）
- 可以通过 --all-profiles (-a) 参数选择处理所有镜像
- 支持通过 --target-registry (-t) 参数指定目标镜像仓库
- 保持原有的组织/项目结构
- 自动将镜像转移到指定的容器镜像仓库
- 显示转移进度和结果
- 在执行转移前会显示详细的镜像列表和目标仓库并请求确认
- 提供自动化的认证文件生成工具，支持多账号配置

## 注意事项

- 确保有足够的磁盘空间用于临时存储镜像
- 确保有阿里云容器镜像服务的访问权限
- 建议在网络良好的环境下运行
- 使用 Docker 方式运行 skopeo 时，确保当前目录可以被容器访问
- 如果使用本地 Docker 认证，确保 ~/.docker/config.json 存在并有正确的权限
- 如果使用独立认证文件，确保 auth.json 文件权限为 600（chmod 600 auth.json）
- 注意不要将包含认证信息的 auth.json 提交到代码仓库
- 建议将 auth.json 添加到 .gitignore 文件中