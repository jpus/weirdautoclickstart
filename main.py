#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Weirdhost Start脚本 - GitHub Actions 版本
"""

import os
import sys
import time
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError


class WeirdhostLogin:
    def __init__(self):
        """初始化，从环境变量读取配置"""
        self.url = os.getenv('WEIRDHOST_URL', 'https://hub.weirdhost.xyz')
        self.server_urls = os.getenv('WEIRDHOST_SERVER_URLS', '')
        self.login_url = os.getenv('WEIRDHOST_LOGIN_URL', 'https://hub.weirdhost.xyz/auth/login')
        
        # 获取认证信息
        self.remember_web_cookie = os.getenv('REMEMBER_WEB_COOKIE', '')
        self.email = os.getenv('WEIRDHOST_EMAIL', '')
        self.password = os.getenv('WEIRDHOST_PASSWORD', '')
        
        # 浏览器配置
        self.headless = os.getenv('HEADLESS', 'true').lower() == 'true'
        
        # 解析服务器URL列表
        self.server_list = []
        if self.server_urls:
            self.server_list = [url.strip() for url in self.server_urls.split(',') if url.strip()]
    
    def log(self, message, level="INFO"):
        """日志输出"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {level}: {message}")
    
    def has_cookie_auth(self):
        """检查是否有 cookie 认证信息"""
        return bool(self.remember_web_cookie)
    
    def has_email_auth(self):
        """检查是否有邮箱密码认证信息"""
        return bool(self.email and self.password)
    
    def check_login_status(self, page):
        """检查是否已登录"""
        try:
            self.log("检查登录状态...")
            
            # 简单检查：如果URL包含login或auth，说明未登录
            if "login" in page.url or "auth" in page.url:
                self.log("当前在登录页面，未登录")
                return False
            else:
                self.log("不在登录页面，判断为已登录")
                return True
                
        except Exception as e:
            self.log(f"检查登录状态时出错: {e}", "ERROR")
            return False
    
    def login_with_cookies(self, context):
        """使用 Cookies 登录"""
        try:
            self.log("尝试使用 Cookies 登录...")
            
            # 创建cookie
            session_cookie = {
                'name': 'remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d',
                'value': self.remember_web_cookie,
                'domain': 'hub.weirdhost.xyz',
                'path': '/',
                'expires': int(time.time()) + 3600 * 24 * 365,
                'httpOnly': True,
                'secure': True,
                'sameSite': 'Lax'
            }
            
            context.add_cookies([session_cookie])
            self.log("已添加 remember_web cookie")
            return True
                
        except Exception as e:
            self.log(f"设置 Cookies 时出错: {e}", "ERROR")
            return False
    
    def login_with_email(self, page):
        """使用邮箱密码登录"""
        try:
            self.log("尝试使用邮箱密码登录...")
            
            # 访问登录页面
            self.log(f"访问登录页面: {self.login_url}")
            page.goto(self.login_url, wait_until="domcontentloaded")
            
            # 使用固定选择器
            email_selector = 'input[name="username"]'
            password_selector = 'input[name="password"]'
            login_button_selector = 'button[type="submit"]'
            
            # 等待元素加载
            self.log("等待登录表单元素加载...")
            page.wait_for_selector(email_selector)
            page.wait_for_selector(password_selector)
            page.wait_for_selector(login_button_selector)
            
            # 填写登录信息
            self.log("填写邮箱和密码...")
            page.fill(email_selector, self.email)
            page.fill(password_selector, self.password)
            
            # 点击登录并等待导航
            self.log("点击登录按钮...")
            with page.expect_navigation(wait_until="domcontentloaded", timeout=90000):
                page.click(login_button_selector)
            
            # 检查登录是否成功
            if "login" in page.url or "auth" in page.url:
                self.log("邮箱密码登录失败，仍在登录页面", "ERROR")
                return False
            else:
                self.log("邮箱密码登录成功！")
                return True
                
        except Exception as e:
            self.log(f"邮箱密码登录时出错: {e}", "ERROR")
            return False
    
    def start_server(self, page, server_url):
        """启动服务器"""
        try:
            server_id = server_url.split('/')[-1]
            self.log(f"开始处理服务器 {server_id}")
            
            # 访问服务器页面 - 使用更严格的等待条件
            self.log(f"访问服务器页面: {server_url}")
            page.goto(server_url, wait_until="networkidle")
            
            # 多重等待策略确保页面完全加载
            self.wait_for_page_ready(page, server_id)
            
            # 使用更可靠的查找方法
            button = self.find_start_button(page, server_id)
            
            if not button:
                return f"{server_id}: no_button_found"
            
            # 检查按钮状态并处理
            if button.is_enabled():
                self.log(f"✅ 服务器 {server_id} 可以启动，正在点击...")
                button.click()
                
                # 等待操作完成
                time.sleep(5)
                return f"{server_id}: started"
            else:
                self.log(f"ℹ️ 服务器 {server_id} 已启动，按钮不可点击")
                return f"{server_id}: already_started"
                
        except Exception as e:
            self.log(f"❌ 服务器 {server_id} 处理过程中出错: {e}")
            return f"{server_id}: error"

    def wait_for_page_ready(self, page, server_id):
        """等待页面完全就绪"""
        # 等待主要内容区域加载
        try:
            page.wait_for_selector('.server-details, .server-info, .card, .panel', timeout=10000)
            self.log(f"✅ 服务器 {server_id} 主要内容已加载")
        except:
            self.log(f"⚠️ 服务器 {server_id} 未找到主要内容区域")
        
        # 等待所有图片加载完成
        try:
            page.wait_for_load_state('networkidle', timeout=15000)
            self.log(f"✅ 服务器 {server_id} 网络空闲")
        except:
            self.log(f"⚠️ 服务器 {server_id} 网络未完全空闲")
        
        # 额外等待时间确保动态内容加载
        time.sleep(3)

    def find_start_button(self, page, server_id):
        """查找启动按钮 - 完全匹配 Start，忽略 Restart"""
        selectors = [
            'button:has-text("Start")',
            '//button[text()="Start"]',
        ]
        
        for selector in selectors:
            try:
                if selector.startswith('//'):
                    button = page.locator(f'xpath={selector}')
                else:
                    button = page.locator(selector)
                
                # 使用更严格的可见性检查
                button.wait_for(state='visible', timeout=10000)
                
                if button.is_visible():
                    self.log(f"✅ 服务器 {server_id} 找到按钮: {selector}")
                    return button
                    
            except Exception as e:
                continue
        
        # 如果上述方法都失败，尝试更广泛的搜索
        return self.find_button_alternative_methods(page, server_id)

    def find_button_alternative_methods(self, page, server_id):
        """备用的按钮查找方法"""
        # 方法1: 查找所有按钮并筛选（完全匹配Start）
        try:
            all_buttons = page.locator('button')
            button_count = all_buttons.count()
            
            for i in range(button_count):
                try:
                    button = all_buttons.nth(i)
                    if button.is_visible():
                        text = button.text_content().strip()
                        if text == "Start":  # 完全匹配Start
                            self.log(f"✅ 服务器 {server_id} 通过文本搜索找到按钮: '{text}'")
                            return button
                except:
                    continue
        except:
            pass
        
        # 方法2: 查找特定class的按钮
        try:
            primary_buttons = page.locator('button.btn-primary, button.btn-success')
            if primary_buttons.count() > 0:
                for i in range(primary_buttons.count()):
                    button = primary_buttons.nth(i)
                    if button.is_visible():
                        text = button.text_content().strip()
                        if text == "Start":  # 完全匹配Start
                            self.log(f"✅ 服务器 {server_id} 通过class找到Start按钮")
                            return button
        except:
            pass
        
        # 方法3: 执行JavaScript查找（完全匹配Start）
        try:
            button = page.evaluate_handle('''() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                return buttons.find(btn => 
                    btn.offsetParent !== null && 
                    btn.textContent.trim() === "Start"
                );
            }''')
            
            if button:
                self.log(f"✅ 服务器 {server_id} 通过JavaScript找到Start按钮")
                return button
        except:
            pass
        
        self.log(f"❌ 服务器 {server_id} 所有方法都未找到Start按钮")
        return None

    def debug_element_visibility(self, page, server_id):
        """调试元素可见性"""
        self.log(f"🔍 调试服务器 {server_id} 的元素可见性")
        
        # 检查按钮的各种状态
        selectors = ['button:has-text("Start")', '//button[text()="Start"]']
        
        for selector in selectors:
            try:
                element = page.locator(selector)
                count = element.count()
                visible = element.is_visible() if count > 0 else False
                enabled = element.is_enabled() if count > 0 else False
                
                self.log(f"选择器 '{selector}': count={count}, visible={visible}, enabled={enabled}")
                
                if count > 0:
                    text = element.first.text_content().strip()
                    self.log(f"  文本内容: '{text}'")
                    
            except Exception as e:
                self.log(f"选择器 '{selector}' 检查失败: {e}")
                    
    def process_server(self, page, server_url):
        """处理单个服务器的启动操作"""
        server_id = server_url.split('/')[-1] if server_url else "unknown"
        self.log(f"开始处理服务器 {server_id}")
        
        try:
            # 访问服务器页面
            self.log(f"访问服务器页面: {server_url}")
            page.goto(server_url, wait_until="networkidle")
            
            # 添加详细的调试信息
            self.debug_element_visibility(page, server_id)
            
            # 检查是否已登录
            if not self.check_login_status(page):
                self.log(f"服务器 {server_id} 未登录，尝试重新登录", "WARNING")
                return f"{server_id}: login_failed"
            
            # 执行启动操作
            result = self.start_server(page, server_url)
            return result  # 直接返回结果，不要再次添加 server_id
            
        except Exception as e:
            self.log(f"处理服务器 {server_id} 时出错: {e}", "ERROR")
            return f"{server_id}: error"
    
    def run(self):
        """主运行函数"""
        self.log("开始 Weirdhost 自动启动任务")
        
        # 检查认证信息
        has_cookie = self.has_cookie_auth()
        has_email = self.has_email_auth()
        
        self.log(f"Cookie 认证可用: {has_cookie}")
        self.log(f"邮箱密码认证可用: {has_email}")
        
        if not has_cookie and not has_email:
            self.log("没有可用的认证信息！", "ERROR")
            return ["error: no_auth"]
        
        # 检查服务器URL列表
        if not self.server_list:
            self.log("未设置服务器URL列表！请设置 WEIRDHOST_SERVER_URLS 环境变量", "ERROR")
            return ["error: no_servers"]
        
        self.log(f"需要处理的服务器数量: {len(self.server_list)}")
        for i, server_url in enumerate(self.server_list, 1):
            self.log(f"服务器 {i}: {server_url}")
        
        results = []
        
        try:
            with sync_playwright() as p:
                # 启动浏览器
                browser = p.chromium.launch(headless=self.headless)
                
                # 创建浏览器上下文
                context = browser.new_context()
                
                # 创建页面
                page = context.new_page()
                page.set_default_timeout(90000)
                
                login_success = False
                
                # 方案1: 尝试 Cookie 登录
                if has_cookie:
                    if self.login_with_cookies(context):
                        # 访问任意页面检查登录状态
                        self.log("检查Cookie登录状态...")
                        page.goto(self.url, wait_until="domcontentloaded")
                        
                        if self.check_login_status(page):
                            self.log("✅ Cookie 登录成功！")
                            login_success = True
                        else:
                            self.log("Cookie 登录失败，cookies 可能已过期", "WARNING")
                
                # 方案2: 如果 Cookie 登录失败，尝试邮箱密码登录
                if not login_success and has_email:
                    if self.login_with_email(page):
                        # 登录成功后访问首页
                        self.log("检查邮箱密码登录状态...")
                        page.goto(self.url, wait_until="domcontentloaded")
                        
                        if self.check_login_status(page):
                            self.log("✅ 邮箱密码登录成功！")
                            login_success = True
                
                # 如果登录成功，依次处理每个服务器
                if login_success:
                    for server_url in self.server_list:
                        result = self.process_server(page, server_url)
                        results.append(result)
                        self.log(f"服务器处理结果: {result}")
                        
                        # 在处理下一个服务器前等待一下
                        time.sleep(5)
                else:
                    self.log("❌ 所有登录方式都失败了", "ERROR")
                    results = ["login_failed"] * len(self.server_list)
                
                browser.close()
                return results
                
        except TimeoutError as e:
            self.log(f"操作超时: {e}", "ERROR")
            return ["error: timeout"] * len(self.server_list)
        except Exception as e:
            self.log(f"运行时出错: {e}", "ERROR")
            return ["error: runtime"] * len(self.server_list)
    
    def write_readme_file(self, results):
        """写入README文件"""
        try:
            # 获取东八区时间
            from datetime import datetime, timezone, timedelta
            beijing_time = datetime.now(timezone(timedelta(hours=8)))
            timestamp = beijing_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # 状态消息映射
            status_messages = {
                "started": "✅ 启动成功",
                "already_started": "ℹ️ 已经启动",
                "no_button_found": "❌ 未找到Start按钮",
                "login_failed": "❌ 登录失败", 
                "error": "💥 运行出错",
                "error: no_auth": "❌ 无认证信息",
                "error: no_servers": "❌ 无服务器配置",
                "error: timeout": "⏰ 操作超时",
                "error: runtime": "💥 运行时错误"
            }
            
            # 创建README内容
            readme_content = f"""# Weirdhost 自动启动脚本

**最后运行时间**: `{timestamp}` (北京时间)

## 运行结果

"""
            
            # 添加每个服务器的结果
            for result in results:
                if ":" in result and not result.startswith("error:"):
                    # 正确分割服务器ID和状态
                    parts = result.split(":", 1)
                    server_id = parts[0].strip()
                    status = parts[1].strip() if len(parts) > 1 else "unknown"
                    # 检查状态是否包含服务器ID
                    if ":" in status:
                        # 如果状态中还包含冒号，说明分割有问题，重新处理
                        status_parts = status.split(":", 1)
                        server_id = f"{server_id}:{status_parts[0]}"
                        status = status_parts[1].strip() if len(status_parts) > 1 else "unknown"
                        
                    status_msg = status_messages.get(status, f"❓ 未知状态 ({status})")
                    readme_content += f"- 服务器 `{server_id}`: {status_msg}\n"
                else:
                    # 处理错误状态
                    status_msg = status_messages.get(result, f"❓ 未知状态 ({result})")
                    readme_content += f"- {status_msg}\n"
            
            # 写入README文件
            with open('README.md', 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            self.log("📝 README已更新")
            
        except Exception as e:
            self.log(f"写入README文件失败: {e}", "ERROR")


def main():
    """主函数"""
    print("🚀 Weirdhost 自动启动脚本启动")
    print("=" * 50)
    
    # 创建登录器
    login = WeirdhostLogin()
    
    # 检查环境变量
    if not login.has_cookie_auth() and not login.has_email_auth():
        print("❌ 错误：未设置认证信息！")
        print("\n请在 GitHub Secrets 中设置以下任一组合：")
        print("\n方案1 - Cookie 认证：")
        print("REMEMBER_WEB_COOKIE: 你的cookie值")
        print("\n方案2 - 邮箱密码认证：")
        print("WEIRDHOST_EMAIL: 你的邮箱")
        print("WEIRDHOST_PASSWORD: 你的密码")
        print("\n推荐使用 Cookie 认证，更稳定可靠")
        sys.exit(1)
    
    # 检查服务器URL列表
    if not login.server_list:
        print("❌ 错误：未设置服务器URL列表！")
        print("\n请在 GitHub Secrets 中设置：")
        print("WEIRDHOST_SERVER_URLS: https://hub.weirdhost.xyz/server/服务器ID1,https://hub.weirdhost.xyz/server/服务器ID2")
        print("\n示例: https://hub.weirdhost.xyz/server/abc12345,https://hub.weirdhost.xyz/server/abc67890")
        sys.exit(1)
    
    # 执行启动任务
    results = login.run()
    
    # 写入README文件
    login.write_readme_file(results)
    
    print("=" * 50)
    print("📊 运行结果汇总:")
    for result in results:
        print(f"  - {result}")
    
    # 检查是否有完全失败的情况
    if any("login_failed" in result or "error:" in result for result in results):
        print("❌ 启动任务有失败的情况！")
        sys.exit(1)
    else:
        print("🎉 启动任务完成！")
        sys.exit(0)


if __name__ == "__main__":
    main()
