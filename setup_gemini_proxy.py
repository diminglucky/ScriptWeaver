"""快速配置 Gemini 代理的辅助脚本"""

import os
import sys
from pathlib import Path

# 设置输出编码为 UTF-8（Windows 兼容）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def setup_proxy():
    """配置 Gemini 代理"""
    print("=" * 60)
    print("Gemini API 代理配置向导")
    print("=" * 60)
    
    # 检查 .env 文件
    env_path = Path(".env")
    
    print("\n📋 当前配置状态：")
    
    # 读取现有配置
    existing_config = {}
    if env_path.exists():
        print(f"✅ 找到 .env 文件：{env_path.absolute()}")
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    existing_config[key.strip()] = value.strip()
    else:
        print(f"⚠️  未找到 .env 文件，将创建新文件")
    
    # 显示当前配置
    api_key = existing_config.get('GEMINI_API_KEY', '')
    model = existing_config.get('GEMINI_MODEL', '')
    http_proxy = existing_config.get('HTTP_PROXY', '')
    https_proxy = existing_config.get('HTTPS_PROXY', '')
    
    if api_key:
        print(f"  • GEMINI_API_KEY: {'*' * (len(api_key)-8) + api_key[-8:] if len(api_key) > 8 else '***'}")
    else:
        print(f"  • GEMINI_API_KEY: 未配置")
    
    if model:
        print(f"  • GEMINI_MODEL: {model}")
    else:
        print(f"  • GEMINI_MODEL: 未配置")
    
    if http_proxy:
        print(f"  • HTTP_PROXY: {http_proxy}")
    else:
        print(f"  • HTTP_PROXY: 未配置")
    
    if https_proxy:
        print(f"  • HTTPS_PROXY: {https_proxy}")
    else:
        print(f"  • HTTPS_PROXY: 未配置")
    
    print("\n" + "=" * 60)
    print("配置选项：")
    print("=" * 60)
    
    # 选择配置方式
    print("\n请选择配置方式：")
    print("1. 快速配置（使用默认代理端口 7890）")
    print("2. 自定义配置（手动输入代理地址和端口）")
    print("3. 仅配置 API Key 和模型（跳过代理配置）")
    print("4. 查看配置指南")
    print("5. 退出")
    
    choice = input("\n请输入选项 (1-5): ").strip()
    
    if choice == '1':
        # 快速配置
        print("\n📝 快速配置模式")
        print("   将使用默认代理：http://127.0.0.1:7890")
        
        # API Key
        if not api_key:
            api_key = input("\n请输入 GEMINI_API_KEY: ").strip()
        else:
            use_existing = input(f"\n使用现有 API Key？(y/n，默认 y): ").strip().lower()
            if use_existing == 'n':
                api_key = input("请输入新的 GEMINI_API_KEY: ").strip()
        
        # Model
        if not model:
            model = "gemini-1.5-flash"
            print(f"\n使用默认模型：{model}")
        else:
            use_existing = input(f"\n使用现有模型 {model}？(y/n，默认 y): ").strip().lower()
            if use_existing == 'n':
                model = input("请输入模型名称 (默认 gemini-1.5-flash): ").strip() or "gemini-1.5-flash"
        
        # 代理
        http_proxy = "http://127.0.0.1:7890"
        https_proxy = "http://127.0.0.1:7890"
        
        save_config(env_path, api_key, model, http_proxy, https_proxy)
        
    elif choice == '2':
        # 自定义配置
        print("\n📝 自定义配置模式")
        
        # API Key
        if not api_key:
            api_key = input("\n请输入 GEMINI_API_KEY: ").strip()
        else:
            use_existing = input(f"\n使用现有 API Key？(y/n，默认 y): ").strip().lower()
            if use_existing == 'n':
                api_key = input("请输入新的 GEMINI_API_KEY: ").strip()
        
        # Model
        if not model:
            model = input("\n请输入模型名称 (默认 gemini-1.5-flash): ").strip() or "gemini-1.5-flash"
        else:
            use_existing = input(f"\n使用现有模型 {model}？(y/n，默认 y): ").strip().lower()
            if use_existing == 'n':
                model = input("请输入新的模型名称: ").strip() or model
        
        # 代理
        print("\n代理配置：")
        print("常见代理端口：")
        print("  • Clash: 7890")
        print("  • V2Ray: 10808 或 1080")
        print("  • Shadowsocks: 1080")
        
        proxy_host = input("\n代理地址 (默认 127.0.0.1): ").strip() or "127.0.0.1"
        proxy_port = input("代理端口 (默认 7890): ").strip() or "7890"
        
        http_proxy = f"http://{proxy_host}:{proxy_port}"
        https_proxy = f"http://{proxy_host}:{proxy_port}"
        
        save_config(env_path, api_key, model, http_proxy, https_proxy)
        
    elif choice == '3':
        # 仅配置 API Key
        print("\n📝 仅配置 API Key 和模型")
        
        # API Key
        if not api_key:
            api_key = input("\n请输入 GEMINI_API_KEY: ").strip()
        else:
            use_existing = input(f"\n使用现有 API Key？(y/n，默认 y): ").strip().lower()
            if use_existing == 'n':
                api_key = input("请输入新的 GEMINI_API_KEY: ").strip()
        
        # Model
        if not model:
            model = input("\n请输入模型名称 (默认 gemini-1.5-flash): ").strip() or "gemini-1.5-flash"
        else:
            use_existing = input(f"\n使用现有模型 {model}？(y/n，默认 y): ").strip().lower()
            if use_existing == 'n':
                model = input("请输入新的模型名称: ").strip() or model
        
        save_config(env_path, api_key, model, http_proxy, https_proxy)
        
    elif choice == '4':
        # 查看配置指南
        print("\n📖 配置指南")
        print("\n请查看以下文档：")
        print("  • GEMINI_PROXY_SETUP_GUIDE.md - 详细的代理配置指南")
        print("  • GEMINI_CONNECTION_FIX.md - 连接问题修复报告")
        print("\n或访问项目文档目录查看更多信息。")
        return
        
    else:
        print("\n👋 退出配置向导")
        return

def save_config(env_path, api_key, model, http_proxy, https_proxy):
    """保存配置到 .env 文件"""
    print("\n💾 保存配置...")
    
    # 读取现有内容
    existing_lines = []
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            existing_lines = f.readlines()
    
    # 更新配置
    config_keys = {
        'GEMINI_API_KEY': api_key,
        'GEMINI_MODEL': model,
        'HTTP_PROXY': http_proxy,
        'HTTPS_PROXY': https_proxy,
    }
    
    # 构建新内容
    new_lines = []
    updated_keys = set()
    
    for line in existing_lines:
        line_stripped = line.strip()
        if '=' in line_stripped and not line_stripped.startswith('#'):
            key = line_stripped.split('=', 1)[0].strip()
            if key in config_keys:
                if config_keys[key]:  # 只有在有值时才更新
                    new_lines.append(f"{key}={config_keys[key]}\n")
                    updated_keys.add(key)
                else:
                    new_lines.append(line)  # 保留原有行
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    # 添加未更新的配置
    if not any('# Gemini API' in line for line in new_lines):
        new_lines.append("\n# Gemini API 配置\n")
    
    for key, value in config_keys.items():
        if key not in updated_keys and value:
            new_lines.append(f"{key}={value}\n")
    
    # 写入文件
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print(f"✅ 配置已保存到：{env_path.absolute()}")
    
    # 显示配置摘要
    print("\n📋 配置摘要：")
    if api_key:
        print(f"  • GEMINI_API_KEY: {'*' * (len(api_key)-8) + api_key[-8:] if len(api_key) > 8 else '***'}")
    if model:
        print(f"  • GEMINI_MODEL: {model}")
    if http_proxy:
        print(f"  • HTTP_PROXY: {http_proxy}")
    if https_proxy:
        print(f"  • HTTPS_PROXY: {https_proxy}")
    
    # 测试连接
    print("\n" + "=" * 60)
    test = input("\n是否测试连接？(y/n，默认 y): ").strip().lower()
    if test != 'n':
        print("\n🔍 测试连接...")
        os.system("python test_gemini_connection.py")

if __name__ == "__main__":
    try:
        setup_proxy()
    except KeyboardInterrupt:
        print("\n\n👋 用户取消配置")
    except Exception as e:
        print(f"\n❌ 配置失败：{e}")
        import traceback
        traceback.print_exc()

