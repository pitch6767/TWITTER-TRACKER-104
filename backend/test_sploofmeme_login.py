#!/usr/bin/env python3
"""
Test script to login to @Sploofmeme account and get following list
This script will ask for verification code interactively
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
from x_monitor_realtime import RealTimeXMonitor
from motor.motor_asyncio import AsyncIOMotorClient
import logging

# Load environment variables
load_dotenv('.env')

# Enable detailed logging
logging.basicConfig(level=logging.INFO)

class InteractiveXMonitor(RealTimeXMonitor):
    """X Monitor that can ask for verification codes interactively"""
    
    async def login_to_x_interactive(self):
        """Interactive login that asks for verification code when needed"""
        try:
            x_username = os.getenv('X_USERNAME')
            x_password = os.getenv('X_PASSWORD')
            x_email = os.getenv('X_EMAIL')
            
            if not x_username or not x_password:
                print("❌ X credentials not found in environment variables")
                return False
            
            print(f"🔐 Attempting to login to X as {x_username}...")
            
            # Navigate to X login page
            await self.page.goto('https://x.com/i/flow/login', wait_until='load', timeout=30000)
            await self.page.wait_for_timeout(5000)
            
            # Step 1: Enter username
            username_input = None
            selectors_to_try = [
                'input[name="text"]',
                'input[autocomplete="username"]', 
                'input[data-testid="ocfEnterTextTextInput"]'
            ]
            
            for selector in selectors_to_try:
                try:
                    username_input = await self.page.wait_for_selector(selector, timeout=5000)
                    if username_input:
                        print("✅ Found username input")
                        break
                except:
                    continue
            
            if not username_input:
                print("❌ Could not find username input field")
                return False
            
            await username_input.fill(x_username)
            print("✅ Username entered")
            await self.page.wait_for_timeout(1000)
            
            # Click Next
            next_clicked = False
            next_selectors = [
                'button:has-text("Next")',
                'div[role="button"]:has-text("Next")',
                '[data-testid="LoginForm_Login_Button"]'
            ]
            
            for selector in next_selectors:
                try:
                    await self.page.click(selector, timeout=3000)
                    next_clicked = True
                    print("✅ Clicked Next")
                    break
                except:
                    continue
            
            if not next_clicked:
                print("❌ Could not click Next button")
                return False
            
            await self.page.wait_for_timeout(3000)
            
            # Step 2: Handle email verification if present
            page_content = await self.page.content()
            
            if ("email" in page_content.lower() or 
                "verify" in page_content.lower() or
                "confirmation" in page_content.lower()):
                
                print("🔐 Email verification step detected")
                
                # Enter email
                email_input = None
                email_selectors = [
                    'input[name="text"]',
                    'input[data-testid="ocfEnterTextTextInput"]',
                    'input[type="text"]'
                ]
                
                for selector in email_selectors:
                    try:
                        email_input = await self.page.wait_for_selector(selector, timeout=3000)
                        if email_input and x_email:
                            print("✅ Found email verification input")
                            await email_input.fill(x_email)
                            print(f"✅ Email entered: {x_email}")
                            break
                    except:
                        continue
                
                # Click Next after email
                for selector in next_selectors:
                    try:
                        await self.page.click(selector, timeout=3000)
                        print("✅ Clicked Next after email verification")
                        break
                    except:
                        continue
                
                await self.page.wait_for_timeout(3000)
                
                # Check if verification code is needed
                page_content_after = await self.page.content()
                
                if ("code" in page_content_after.lower() or 
                    "verify" in page_content_after.lower() or
                    "confirmation" in page_content_after.lower()):
                    
                    print("\n" + "="*60)
                    print("🔢 VERIFICATION CODE REQUIRED")
                    print("📧 Check your ProtonMail inbox: sploofmeme@protonmail.com")
                    print("🔍 Look for email from X/Twitter with verification code")
                    print("📱 The code is usually 8 characters (letters + numbers)")
                    print("="*60)
                    
                    # Ask for verification code
                    verification_code = input("Enter the verification code from email: ").strip()
                    
                    if verification_code and len(verification_code) >= 6:
                        print(f"✅ Received verification code: {verification_code}")
                        
                        # Enter verification code
                        code_input = None
                        code_selectors = [
                            'input[name="text"]',
                            'input[data-testid="ocfEnterTextTextInput"]',
                            'input[type="text"]'
                        ]
                        
                        for selector in code_selectors:
                            try:
                                code_input = await self.page.wait_for_selector(selector, timeout=3000)
                                if code_input:
                                    print("✅ Found verification code input")
                                    await code_input.fill(verification_code)
                                    print(f"✅ Verification code entered")
                                    break
                            except:
                                continue
                        
                        # Click Next after verification code
                        for selector in next_selectors:
                            try:
                                await self.page.click(selector, timeout=3000)
                                print("✅ Clicked Next after verification code")
                                break
                            except:
                                continue
                        
                        await self.page.wait_for_timeout(3000)
                    else:
                        print("❌ No verification code provided or invalid format")
                        return False
            
            # Step 3: Enter password
            password_input = None
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                'input[autocomplete="current-password"]'
            ]
            
            for selector in password_selectors:
                try:
                    password_input = await self.page.wait_for_selector(selector, timeout=10000)
                    if password_input:
                        print("✅ Found password input")
                        break
                except:
                    continue
            
            if not password_input:
                print("❌ Could not find password input field")
                return False
            
            await password_input.fill(x_password)
            print("✅ Password entered")
            await self.page.wait_for_timeout(1000)
            
            # Step 4: Click Log in
            login_clicked = False
            login_selectors = [
                'button:has-text("Log in")',
                'div[role="button"]:has-text("Log in")',
                '[data-testid="LoginForm_Login_Button"]'
            ]
            
            for selector in login_selectors:
                try:
                    await self.page.click(selector, timeout=3000)
                    login_clicked = True
                    print("✅ Clicked Log in")
                    break
                except:
                    continue
            
            if not login_clicked:
                print("❌ Could not click Log in button")
                return False
            
            # Step 5: Wait and check login success
            await self.page.wait_for_timeout(8000)
            
            current_url = self.page.url
            print(f"📍 Current URL: {current_url}")
            
            # Check success indicators
            success_indicators = [
                'home' in current_url.lower(),
                current_url.startswith('https://x.com/home'),
                current_url.startswith('https://x.com') and 'login' not in current_url and 'flow' not in current_url
            ]
            
            if any(success_indicators):
                print("🎉 LOGIN SUCCESSFUL!")
                return True
            else:
                print(f"❌ Login failed. Current URL: {current_url}")
                return False
                
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False

async def main():
    print("🎯 Interactive @Sploofmeme Following List Scraper")
    print("=" * 60)
    
    # Connect to MongoDB
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    # Create interactive monitor
    monitor = InteractiveXMonitor(db)
    
    print("🔄 Initializing browser...")
    browser_ok = await monitor.initialize_browser()
    
    if not browser_ok:
        print("❌ Browser initialization failed")
        return
    
    print("✅ Browser ready")
    
    # Attempt interactive login
    login_success = await monitor.login_to_x_interactive()
    
    if login_success:
        print("\n🎉 LOGIN SUCCESSFUL! Now getting @Sploofmeme following list...")
        
        # Navigate to following page
        print("📂 Navigating to @Sploofmeme following page...")
        await monitor.page.goto('https://x.com/Sploofmeme/following', timeout=30000)
        await monitor.page.wait_for_timeout(5000)
        
        # Quick test to see if we can access the page
        current_url = monitor.page.url
        page_title = await monitor.page.title()
        
        print(f"📍 URL: {current_url}")
        print(f"📄 Title: {page_title}")
        
        if 'Sploofmeme' in page_title or 'following' in current_url.lower():
            print("✅ Successfully accessed @Sploofmeme following page!")
            
            # Now scrape the following list
            print("🔄 Starting to scrape following accounts...")
            await monitor.update_following_list('Sploofmeme')
            
            print(f"\n🎉 FINAL RESULT: {len(monitor.monitored_accounts)} accounts scraped!")
            
            if len(monitor.monitored_accounts) > 50:
                print("✅ SUCCESS! Real @Sploofmeme following list obtained!")
                print(f"📊 Total accounts: {len(monitor.monitored_accounts)}")
                print(f"📋 First 20 accounts: {monitor.monitored_accounts[:20]}")
                print(f"📋 Sample from middle: {monitor.monitored_accounts[len(monitor.monitored_accounts)//2:len(monitor.monitored_accounts)//2+10]}")
            else:
                print(f"⚠️ Limited results: {monitor.monitored_accounts}")
        else:
            print("❌ Could not access following page")
    else:
        print("❌ Login failed")
    
    await monitor.close_browser()
    print("✅ Browser closed")

if __name__ == "__main__":
    asyncio.run(main())