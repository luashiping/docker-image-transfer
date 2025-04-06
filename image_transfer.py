#!/usr/bin/env python
import yaml
import subprocess
import sys
import os
import argparse
from pathlib import Path

def read_env_file(env_file_path):
    """
    Read environment variables from .env file
    
    Args:
        env_file_path (str): Path to .env file
    
    Returns:
        dict: Environment variables
    """
    env_vars = {}
    if os.path.exists(env_file_path):
        with open(env_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")
    return env_vars

def resolve_image_var(image_value, env_vars):
    """
    Resolve environment variables in image value
    
    Args:
        image_value (str): Image value from compose file
        env_vars (dict): Environment variables
    
    Returns:
        str: Resolved image value
    """
    if not image_value or not isinstance(image_value, str):
        return image_value
        
    # Handle ${VAR} and ${VAR:-default} formats
    if image_value.startswith('${') and image_value.endswith('}'):
        var_expr = image_value[2:-1]
        
        # Check if there's a default value
        if ':-' in var_expr:
            var_name, default_value = var_expr.split(':-', 1)
        else:
            var_name = var_expr
            default_value = image_value  # Keep original if no value found
            
        # First try env_vars from .env file
        if var_name in env_vars:
            return env_vars[var_name]
        # Then try system environment variables
        return os.environ.get(var_name, default_value)
    
    return image_value

def read_compose_file(file_path):
    """Read and parse docker-compose file."""
    if not os.path.exists(file_path):
        print(f"Error: {file_path} does not exist")
        sys.exit(1)
        
    # Look for .env file in the same directory as the compose file
    env_file_path = os.path.join(os.path.dirname(file_path), '.env')
    env_vars = read_env_file(env_file_path)
    
    with open(file_path, 'r') as f:
        try:
            compose_data = yaml.safe_load(f)
            
            # Handle 'include' directive
            if 'include' in compose_data:
                includes = compose_data['include']
                if isinstance(includes, str):
                    includes = [includes]
                for include in includes:
                    include_path = os.path.join(os.path.dirname(file_path), include)
                    if os.path.exists(include_path):
                        with open(include_path, 'r') as inc_f:
                            include_data = yaml.safe_load(inc_f)
                            # Merge services
                            if 'services' in include_data:
                                if 'services' not in compose_data:
                                    compose_data['services'] = {}
                                compose_data['services'].update(include_data['services'])
            
            return compose_data, env_vars
        except yaml.YAMLError as e:
            print(f"Error parsing docker-compose file: {e}")
            sys.exit(1)

def extract_images(compose_data, env_vars, include_profiles=False):
    """
    Extract image references from compose data.
    
    Args:
        compose_data (dict): The parsed docker-compose data
        env_vars (dict): Environment variables
        include_profiles (bool): Whether to include services with profiles
    
    Returns:
        list: List of tuples containing (image_name, service_name, profiles)
    """
    images = []
    if 'services' not in compose_data:
        return images
        
    for service_name, service in compose_data['services'].items():
        if 'image' not in service:
            continue
            
        profiles = service.get('profiles', [])
        
        # Skip services with profiles unless explicitly requested
        if profiles and not include_profiles:
            continue
            
        # Resolve environment variables in image value
        image_value = resolve_image_var(service['image'], env_vars)
        if not image_value:
            print(f"Warning: Could not resolve image value for service '{service_name}'")
            continue
            
        images.append((image_value, service_name, profiles))
    
    return images

def get_skopeo_command():
    """
    Get the skopeo command with authentication configuration.
    Requires auth.json file to be present in the current directory.
    Returns the base command as a list of arguments.
    """
    if not os.path.exists('auth.json'):
        print("错误：未找到认证文件")
        print("请使用以下命令创建认证文件：")
        print("python generate_auth.py")
        sys.exit(1)
    
    return [
        "docker", "run", "--rm",
        "-v", f"{os.getcwd()}/auth.json:/root/.docker/config.json:ro",
        "--net=host",
        "quay.io/skopeo/stable:latest"
    ]

def process_image_name(image_name, target_registry):
    """
    Process image name according to specific rules.
    
    Args:
        image_name (str): Original image name
        target_registry (str): Target registry URL
    
    Returns:
        str: Processed target image name
    """
    # Get everything after the last slash (name:tag)
    name_tag = image_name.split('/')[-1]
    return f"{target_registry}/{name_tag}"

def transfer_image(source_image, target_registry):
    """
    Transfer image using skopeo.
    
    Args:
        source_image (str): Source image path
        target_registry (str): Target registry URL
    """
    # Process target image name
    target_image = process_image_name(source_image, target_registry)

    print(f"Transferring {source_image} to {target_image}")
    
    try:
        # Get base skopeo command
        cmd = get_skopeo_command()
        # Add skopeo-specific arguments
        cmd.extend([
            "copy",
            f"docker://{source_image}",
            f"docker://{target_image}",
            "--dest-authfile", "/root/.docker/config.json",
        ])
        
        # Run the command
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"Successfully transferred {source_image}")
        
        # If there's any output, print it
        if result.stdout:
            print("Output:", result.stdout)
            
    except subprocess.CalledProcessError as e:
        print(f"Error transferring {source_image}:")
        if e.stdout:
            print("stdout:", e.stdout)
        if e.stderr:
            print("stderr:", e.stderr)
        return False
    return True

def main():
    parser = argparse.ArgumentParser(description='Transfer Docker images from compose file to target registry')
    parser.add_argument('compose_file', help='Path to docker-compose file')
    parser.add_argument('--target-registry', '-t', 
                      required=True,
                      help='Target registry URL (e.g., registry.cn-hangzhou.aliyuncs.com/myproject)')
    parser.add_argument('--all-profiles', '-a', action='store_true',
                      help='Include services with profiles')
    
    args = parser.parse_args()
    
    # Verify Docker is available
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print("Error: Docker is not available. Please make sure Docker is installed and running.")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: Docker command not found. Please make sure Docker is installed.")
        sys.exit(1)
    
    compose_data, env_vars = read_compose_file(args.compose_file)
    images = extract_images(compose_data, env_vars, args.all_profiles)
    
    if not images:
        print("No images found in the compose file" + 
              " (use --all-profiles to include services with profiles)" if not args.all_profiles else "")
        sys.exit(0)
        
    print(f"\nFound {len(images)} images to transfer:")
    for image, service_name, profiles in images:
        profile_info = f" (profiles: {', '.join(profiles)})" if profiles else ""
        target_image = process_image_name(image, args.target_registry)
        print(f"- {image} -> {target_image} (service: '{service_name}'{profile_info})")
    print(f"\nTarget registry: {args.target_registry}")
    
    proceed = input("\nDo you want to proceed with the transfer? [y/N] ")
    if proceed.lower() != 'y':
        print("Transfer cancelled")
        sys.exit(0)
    
    print("\nStarting transfer process...")
    success_count = 0
    for image, service_name, _ in images:
        if transfer_image(image, args.target_registry):
            success_count += 1
            
    print(f"\nTransfer complete: {success_count}/{len(images)} images transferred successfully")

if __name__ == "__main__":
    main() 