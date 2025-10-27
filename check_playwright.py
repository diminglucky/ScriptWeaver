"""
检查 Playwright 是否正确安装
"""

import sys


def check_playwright_installation():
    """检查 Playwright 安装状态"""
    print("=" * 60)
    print("   Playwright 安装检查")
    print("=" * 60)
    print()
    
    # 1. 检查 playwright 包是否安装
    print("[1/3] 检查 playwright 包...")
    try:
        import playwright
        print(f"    [OK] playwright 版本: {playwright.__version__}")
    except ImportError:
        print("    [ERROR] playwright 未安装")
        print()
        print("    请运行以下命令安装:")
        print("    pip install playwright")
        print()
        return False
    
    print()
    
    # 2. 检查浏览器驱动是否安装
    print("[2/3] 检查 chromium 浏览器...")
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                print("    [OK] chromium 浏览器已安装")
            except Exception as e:
                print(f"    [ERROR] chromium 浏览器未安装: {e}")
                print()
                print("    请运行以下命令安装:")
                print("    playwright install chromium")
                print()
                return False
                
    except Exception as e:
        print(f"    [ERROR] 无法启动 playwright: {e}")
        return False
    
    print()
    
    # 3. 测试异步API
    print("[3/3] 测试异步 API...")
    try:
        import asyncio
        from playwright.async_api import async_playwright
        
        async def test_async():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto('https://www.baidu.com')
                title = await page.title()
                await browser.close()
                return title
        
        # 运行异步测试
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(test_async())
        loop.close()
        
        print(f"    [OK] 异步 API 正常 (测试页面标题: {result})")
        
    except Exception as e:
        print(f"    [WARN] 异步 API 测试失败: {e}")
        print("    (这可能不影响基本功能)")
    
    print()
    print("=" * 60)
    print("   [SUCCESS] Playwright 安装完成!")
    print("=" * 60)
    print()
    print("你现在可以使用知乎发布功能了!")
    print()
    
    return True


if __name__ == "__main__":
    try:
        success = check_playwright_installation()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print()
        print("检查已取消")
        sys.exit(1)
    except Exception as e:
        print()
        print(f"[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

