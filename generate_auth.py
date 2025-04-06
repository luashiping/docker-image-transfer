#!/usr/bin/env python
import json
import os
import sys
import base64
import getpass
from pathlib import Path

def read_docker_config():
    """读取现有的 Docker 配置文件"""
    docker_config_path = os.path.expanduser("~/.docker/config.json")
    if os.path.exists(docker_config_path):
        with open(docker_config_path, 'r') as f:
            return json.load(f)
    return {"auths": {}}

def create_auth_config(username, password, registry="registry.cn-hangzhou.aliyuncs.com"):
    """创建认证配置"""
    auth_string = f"{username}:{password}"
    auth_base64 = base64.b64encode(auth_string.encode()).decode()
    return {
        "auths": {
            registry: {
                "auth": auth_base64
            }
        }
    }

def merge_auth_configs(existing_config, new_config):
    """合并认证配置"""
    merged = existing_config.copy()
    merged["auths"].update(new_config["auths"])
    return merged

def save_auth_file(config, output_file="auth.json"):
    """保存认证文件"""
    with open(output_file, 'w') as f:
        json.dump(config, f, indent=2)
    os.chmod(output_file, 0o600)

def view_auth_info(auth_file="auth.json"):
    """查看认证信息"""
    if not os.path.exists(auth_file):
        print(f"错误：{auth_file} 文件不存在")
        return

    try:
        with open(auth_file, 'r') as f:
            config = json.load(f)
        
        print("\n认证信息：")
        print("-" * 50)
        for registry, auth_data in config.get("auths", {}).items():
            print(f"\n镜像仓库: {registry}")
            if "auth" in auth_data:
                auth_decoded = base64.b64decode(auth_data["auth"]).decode()
                username, password = auth_decoded.split(":", 1)
                print(f"用户名: {username}")
                print(f"密码: {'*' * len(password)}")
            else:
                print("警告：没有找到认证信息")
        print("\n" + "-" * 50)
    except json.JSONDecodeError:
        print(f"错误：{auth_file} 不是有效的 JSON 文件")
    except Exception as e:
        print(f"错误：{str(e)}")

def main():
    # 解析命令行参数
    if "--help" in sys.argv:
        print("""用法：
python generate_auth.py [选项] [registry_url]

选项：
  --copy-docker   直接复制 ~/.docker/config.json 的内容
  --merge         合并新的认证信息到现有的 auth.json（如果存在）
  --view          查看当前认证文件中的信息（不会显示完整密码）
  registry_url    可选，指定镜像仓库地址（默认：registry.cn-hangzhou.aliyuncs.com）

示例：
  python generate_auth.py                    # 交互式创建新的认证文件
  python generate_auth.py --copy-docker      # 复制现有的 Docker 认证
  python generate_auth.py --merge            # 添加新的认证信息到现有文件
  python generate_auth.py --view             # 查看当前认证信息
""")
        sys.exit(0)

    # 处理命令行选项
    if "--view" in sys.argv:
        view_auth_info()
        return

    copy_docker = "--copy-docker" in sys.argv
    merge_existing = "--merge" in sys.argv
    registry = next((arg for arg in sys.argv[1:] if not arg.startswith("--")), 
                   "registry.cn-hangzhou.aliyuncs.com")

    if copy_docker:
        # 直接复制 Docker 配置
        config = read_docker_config()
        save_auth_file(config)
        print(f"已复制 Docker 认证信息到 auth.json")
        # 显示认证信息
        view_auth_info()
        return

    # 读取现有的认证文件（如果需要合并）
    existing_config = {"auths": {}}
    if merge_existing and os.path.exists("auth.json"):
        with open("auth.json", 'r') as f:
            existing_config = json.load(f)

    # 获取认证信息
    username = input(f"请输入 {registry} 的用户名: ")
    password = getpass.getpass(f"请输入 {registry} 的密码: ")

    # 创建新的认证配置
    new_config = create_auth_config(username, password, registry)

    # 合并配置（如果需要）
    final_config = merge_auth_configs(existing_config, new_config) if merge_existing else new_config

    # 保存认证文件
    save_auth_file(final_config)
    print(f"\n认证文件已保存到 auth.json")
    
    # 显示认证信息
    view_auth_info()

if __name__ == "__main__":
    main() 