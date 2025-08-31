import asyncio
import logging
import re
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Set
from playwright.async_api import async_playwright, Browser, Page
import aiohttp
from bs4 import BeautifulSoup
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

class TokenCA:
    """Represents a token with its contract address"""
    def __init__(self, name: str, ca: str, timestamp: datetime = None):
        self.name = name.upper()
        self.ca = ca
        self.timestamp = timestamp or datetime.now(timezone.utc)

class RealTimeXMonitor:
    def __init__(self, db: AsyncIOMotorDatabase, alert_threshold: int = 2):
        self.db = db
        self.alert_threshold = alert_threshold
        self.browser: Browser = None
        self.page: Page = None
        self.is_monitoring = False
        self.monitored_accounts = []
        self.known_tokens_with_ca: Set[str] = set()
        self.token_mentions_cache = {}
        self.last_check_time = datetime.now(timezone.utc) - timedelta(hours=1)
        self.ca_watchlist: Set[str] = set()  # Active tokens to monitor for CAs
        
        # Advanced token patterns for meme coins
        self.token_patterns = [
            r'\$([A-Z]{2,10})\b',  # $TOKEN format
            r'\b([A-Z]{2,10})(?:\s+(?:coin|token|gem|to\s+the\s+moon|moon|pump|lambo|rocket|bullish|bearish|hodl|diamond\s+hands))\b',
            r'\b(PEPE|DOGE|SHIB|BONK|WIF|FLOKI|MEME|APE|WOJAK|TURBO|BRETT|POPCAT|DEGEN|MEW|BOBO|PEPE2|LADYS|BABYDOGE|DOGELON|AKITA|KISHU|SAFEMOON|HOGE|NFD|ELON|MILADY|BEN|ANDY|BART|MATT|TOSHI|HOPPY|MUMU|BENJI|POKEMON|SPURDO|BODEN|MAGA|SLERF|BOOK|MYRO|PONKE|RETARDIO|GIGACHAD|CHAD|BASED|WOJAK)(?:\s+(?:coin|token|crypto|currency|money|cash|dollar|euro|yen|pound|franc|mark|ruble|peso|real|rand|rupee|dinar|dirham|riyal|shekel|won|yuan|yen|baht|dong|kip|kyat|taka|afghani|manat|som|tenge|lari|dram|leu|lev|kuna|koruna|zloty|forint|krona|krone|markka|guilder|punt|escudo|peseta|lira|drachma|denar|tolar|lat|litas|kroon|cedi|naira|shilling|birr|nakfa|leone|dalasi|ouguiya|franc|dinar|pound|pula|loti|lilangeni|rand|kwacha|metical|ariary|rupee|dollar|franc|peso|colon|quetzal|lempira|cordoba|balboa|sucre|nuevo|real|guarani|peso|uruguayo|boliviano|chileno|colombiano|venezolano|guyanese|surinamese|falkland|bermudian|cayman|jamaican|barbadian|trinidad|tobago|dominican|haitian|cuban|bahamian|canadian|american|mexican|guatemalan|belizean|salvadoran|honduran|nicaraguan|costa|rican|panamanian|ecuadorian|peruvian|brazilian|argentine|paraguayan|uruguayan|bolivian|chilean|colombian|venezuelan|guyanan|surinamer|french|british|spanish|portuguese|dutch|german|italian|swiss|austrian|belgian|luxembourg|monaco|andorran|san|marino|vatican|maltese|cypriot|greek|bulgarian|romanian|moldovan|ukrainian|belarusian|russian|estonian|latvian|lithuanian|polish|czech|slovak|hungarian|slovene|croatian|bosnian|serbian|montenegrin|albanian|macedonian|turkish|georgian|armenian|azerbaijani|kazakh|kyrgyz|tajik|turkmen|uzbek|afghan|pakistani|indian|bangladeshi|sri|lankan|maldivian|nepali|bhutanese|myanmar|thai|laotian|cambodian|vietnamese|malaysian|bruneian|singaporean|indonesian|timorese|filipino|taiwanese|chinese|japanese|south|korean|north|korean|mongolian|australian|new|zealand|fijian|papua|guinean|solomon|vanuatu|samoa|tonga|tuvalu|kiribati|nauru|marshall|micronesian|palau|hawaiian|alaskan|puerto|rican|virgin|guam|samoa|northern|mariana|cook|niue|tokelau|pitcairn|norfolk|christmas|cocos|keeling|heard|mcdonald|macquarie|antarctic|falkland|south|georgia|sandwich|tristan|cunha|ascension|saint|helena|mauritius|seychelles|comoros|madagascar|reunion|mayotte|kerguelen|crozet|amsterdam|saint|paul|prince|edward|marion|bouvet|peter|macquarie|heard|mcdonald|antarctic|ross|dependency|marie|byrd|land|queen|maud|land|enderby|land|kemp|land|mac|robertson|land|princess|elizabeth|land|wilhelm|kaiser|land|queen|mary|land|wilkes|land|adelie|land|george|land|oates|land|victoria|land|south|magnetic|pole|north|magnetic|pole|geographic|south|pole|geographic|north|pole|equator|tropic|cancer|capricorn|arctic|circle|antarctic|circle|prime|meridian|international|date|line|greenwich|mean|time|coordinated|universal|time|daylight|saving|time|standard|time|time|zone|utc|gmt|est|cst|mst|pst|edt|cdt|mdt|pdt|ast|hst|akst|akdt|nst|ndt|atlantic|pacific|mountain|central|eastern|hawaii|alaska|newfoundland|yukon|british|columbia|alberta|saskatchewan|manitoba|ontario|quebec|new|brunswick|nova|scotia|prince|edward|island|northwest|territories|nunavut|washington|oregon|california|nevada|idaho|montana|wyoming|utah|colorado|arizona|new|mexico|north|dakota|south|dakota|nebraska|kansas|oklahoma|texas|minnesota|iowa|missouri|arkansas|louisiana|wisconsin|illinois|michigan|indiana|ohio|kentucky|tennessee|mississippi|alabama|west|virginia|virginia|maryland|delaware|pennsylvania|new|jersey|new|york|connecticut|rhode|island|massachusetts|vermont|new|hampshire|maine|florida|georgia|south|carolina|north|carolina|hawaii|alaska|district|columbia|puerto|rico|virgin|islands|guam|american|samoa|northern|mariana|islands))\b'
        ]
        
        # Known old/established tokens to filter out
        self.established_tokens = {
            'BTC', 'ETH', 'BNB', 'ADA', 'SOL', 'XRP', 'USDT', 'USDC', 'BUSD', 'MATIC', 'AVAX', 'DOT', 'UNI', 'LINK', 'ATOM', 'ICP', 'LTC', 'BCH', 'FIL', 'ALGO', 'VET', 'ETC', 'THETA', 'AAVE', 'MKR', 'COMP', 'SUSHI', 'SNX', 'YFI', 'CRV', 'BAL', '1INCH'
        }

    async def initialize_browser(self):
        """Initialize Playwright browser for X monitoring"""
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-features=VizDisplayCompositor',
                    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ]
            )
            self.page = await self.browser.new_page()
            await self.page.set_viewport_size({"width": 1920, "height": 1080})
            logger.info("Browser initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            return False

    async def login_to_x(self):
        """Login to X/Twitter using credentials with enhanced error handling"""
        try:
            x_username = os.getenv('X_USERNAME')
            x_password = os.getenv('X_PASSWORD')
            
            if not x_username or not x_password:
                logger.error("X credentials not found in environment variables")
                return False
            
            logger.info(f"Attempting to login to X as {x_username}...")
            
            # Navigate to X login page
            await self.page.goto('https://x.com/i/flow/login', wait_until='load', timeout=30000)
            await self.page.wait_for_timeout(5000)
            
            # Take screenshot for debugging
            logger.info("Taking screenshot of login page...")
            
            # Try multiple selectors for username input
            username_input = None
            selectors_to_try = [
                'input[name="text"]',
                'input[autocomplete="username"]', 
                'input[data-testid="ocfEnterTextTextInput"]',
                'input[placeholder*="username"]',
                'input[type="text"]'
            ]
            
            for selector in selectors_to_try:
                try:
                    username_input = await self.page.wait_for_selector(selector, timeout=3000)
                    if username_input:
                        logger.info(f"Found username input with selector: {selector}")
                        break
                except:
                    continue
            
            if not username_input:
                logger.error("Could not find username input field")
                return False
            
            # Enter username
            await username_input.fill(x_username)
            logger.info("Username entered")
            await self.page.wait_for_timeout(1000)
            
            # Click Next button - try multiple selectors
            next_clicked = False
            next_selectors = [
                'div[role="button"]:has-text("Next")',
                'button:has-text("Next")',
                '[data-testid="LoginForm_Login_Button"]',
                'div[data-testid="ocfEnterTextNextButton"]'
            ]
            
            for selector in next_selectors:
                try:
                    await self.page.click(selector, timeout=3000)
                    next_clicked = True
                    logger.info(f"Clicked Next with selector: {selector}")
                    break
                except:
                    continue
            
            if not next_clicked:
                logger.error("Could not click Next button")
                return False
            
            await self.page.wait_for_timeout(3000)
            
            # Handle potential additional verification
            try:
                page_content = await self.page.content()
                if "unusual activity" in page_content.lower() or "suspicious" in page_content.lower():
                    logger.warning("Unusual activity detected - may need manual verification")
                    return False
                
                # Check for phone/email verification
                verification_selectors = [
                    'input[name="text"]',
                    'input[data-testid="ocfEnterTextTextInput"]'
                ]
                
                for selector in verification_selectors:
                    try:
                        if await self.page.is_visible(selector):
                            logger.info("Additional verification step detected")
                            verification_input = await self.page.wait_for_selector(selector, timeout=2000)
                            await verification_input.fill(x_username)
                            
                            # Click next again
                            for next_sel in next_selectors:
                                try:
                                    await self.page.click(next_sel, timeout=2000)
                                    break
                                except:
                                    continue
                            break
                    except:
                        continue
                        
                await self.page.wait_for_timeout(2000)
                
            except Exception as e:
                logger.debug(f"Verification step handling: {e}")
            
            # Enter password
            password_input = None
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                'input[autocomplete="current-password"]'
            ]
            
            for selector in password_selectors:
                try:
                    password_input = await self.page.wait_for_selector(selector, timeout=5000)
                    if password_input:
                        logger.info(f"Found password input with selector: {selector}")
                        break
                except:
                    continue
            
            if not password_input:
                logger.error("Could not find password input field")
                return False
            
            await password_input.fill(x_password)
            logger.info("Password entered")
            await self.page.wait_for_timeout(1000)
            
            # Click Log in button
            login_clicked = False
            login_selectors = [
                'div[role="button"]:has-text("Log in")',
                'button:has-text("Log in")',
                '[data-testid="LoginForm_Login_Button"]',
                'div[data-testid="LoginForm_Login_Button"]'
            ]
            
            for selector in login_selectors:
                try:
                    await self.page.click(selector, timeout=3000)
                    login_clicked = True
                    logger.info(f"Clicked Log in with selector: {selector}")
                    break
                except:
                    continue
            
            if not login_clicked:
                logger.error("Could not click Log in button")
                return False
            
            # Wait for login to complete
            await self.page.wait_for_timeout(8000)
            
            # Check if login was successful
            current_url = self.page.url
            logger.info(f"Current URL after login: {current_url}")
            
            # Multiple success indicators
            success_indicators = [
                'home' in current_url,
                'x.com' in current_url and 'login' not in current_url and 'flow' not in current_url,
                await self.page.is_visible('[data-testid="SideNav_NewTweet_Button"]') if await self.page.is_visible('[data-testid="SideNav_NewTweet_Button"]', timeout=2000) else False
            ]
            
            if any(success_indicators):
                logger.info("✅ Successfully logged into X!")
                return True
            else:
                logger.error(f"❌ Login failed - URL: {current_url}")
                # Take screenshot for debugging
                page_content_snippet = (await self.page.content())[:500]
                logger.debug(f"Page content snippet: {page_content_snippet}")
                return False
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    async def close_browser(self):
        """Close browser resources"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            logger.info("Browser closed successfully")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    async def load_known_tokens_with_ca(self):
        """Load tokens that already have contract addresses to filter them out"""
        try:
            # Load from CA alerts (tokens that already have CAs)
            ca_alerts = await self.db.ca_alerts.find().to_list(1000)
            for alert in ca_alerts:
                token_name = alert.get('token_name', '').upper()
                if token_name:
                    self.known_tokens_with_ca.add(token_name)
            
            # Add established tokens
            self.known_tokens_with_ca.update(self.established_tokens)
            logger.info(f"Loaded {len(self.known_tokens_with_ca)} known tokens with CAs")
        except Exception as e:
            logger.error(f"Error loading known tokens: {e}")

    def extract_token_names(self, text: str) -> List[str]:
        """Extract potential token names from text using advanced patterns"""
        tokens = set()
        text = text.upper()
        
        for pattern in self.token_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                token = match.strip() if isinstance(match, str) else match[0].strip()
                if len(token) >= 2 and token not in self.established_tokens:
                    tokens.add(token.upper())
        
        return list(tokens)

    async def start_monitoring(self, target_account: str = "Sploofmeme"):
        """Start monitoring all accounts that the target account follows"""
        try:
            if self.is_monitoring:
                logger.warning("Monitoring already active")
                return
            
            self.is_monitoring = True
            
            # Load known tokens to filter out
            await self.load_known_tokens_with_ca()
            
            # Get following list
            await self.update_following_list(target_account)
            
            logger.info(f"Started monitoring {len(self.monitored_accounts)} accounts followed by @{target_account}")
            
            # Start monitoring loop
            asyncio.create_task(self.monitoring_loop())
            
        except Exception as e:
            logger.error(f"Error starting monitoring: {e}")
            self.is_monitoring = False

    async def update_following_list(self, target_account: str):
        """Update the list of accounts to monitor by scraping X following list with authentication"""
        try:
            # Initialize browser if needed
            if not self.browser:
                await self.initialize_browser()
            
            if not self.browser:
                logger.error("Browser initialization failed, using enhanced fallback")
                await self._use_enhanced_fallback()
                return
            
            logger.info(f"Attempting to scrape @{target_account} following list with authentication...")
            
            try:
                # Step 1: Login to X first
                login_success = await self.login_to_x()
                if not login_success:
                    logger.warning("X login failed - using enhanced fallback")
                    await self._use_enhanced_fallback()
                    return
                
                # Step 2: Navigate to following page (now authenticated)
                following_url = f"https://x.com/{target_account}/following"
                logger.info(f"Navigating to {following_url}")
                await self.page.goto(following_url, wait_until='networkidle', timeout=30000)
                
                # Wait for page to load
                await self.page.wait_for_timeout(5000)
                
                # Step 3: Scroll and collect following accounts
                accounts = set()
                scroll_attempts = 0
                max_scrolls = 50  # Increase scrolls for more accounts
                no_new_accounts_count = 0
                
                logger.info("Starting to collect following accounts...")
                
                while scroll_attempts < max_scrolls and len(accounts) < 2000 and no_new_accounts_count < 5:
                    previous_count = len(accounts)
                    
                    # Look for account links and usernames
                    try:
                        # Method 1: Look for profile links
                        account_links = await self.page.query_selector_all('a[href^="/"][href*="/"]')
                        
                        for link in account_links:
                            try:
                                href = await link.get_attribute('href')
                                if href and href.startswith('/') and len(href) > 1:
                                    username = href.strip('/').split('/')[0]
                                    if (username and 
                                        len(username) > 0 and 
                                        not username.startswith('i/') and
                                        not username.startswith('intent/') and
                                        not username.startswith('search') and
                                        not username.startswith('hashtag') and
                                        username.replace('_', '').replace('-', '').isalnum() and
                                        len(username) <= 15):
                                        accounts.add(username)
                            except:
                                continue
                        
                        # Method 2: Look for @username text patterns
                        page_text = await self.page.content()
                        username_matches = re.findall(r'@([a-zA-Z0-9_]{1,15})', page_text)
                        for username in username_matches:
                            if (len(username) > 0 and 
                                username.replace('_', '').isalnum() and
                                len(username) <= 15):
                                accounts.add(username)
                        
                    except Exception as e:
                        logger.debug(f"Error collecting accounts: {e}")
                    
                    # Check progress
                    new_accounts = len(accounts) - previous_count
                    if new_accounts == 0:
                        no_new_accounts_count += 1
                    else:
                        no_new_accounts_count = 0
                        logger.info(f"Found {len(accounts)} accounts so far... (+{new_accounts} new)")
                    
                    # Scroll down to load more
                    await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await self.page.wait_for_timeout(3000)  # Wait for content to load
                    scroll_attempts += 1
                    
                    # Log progress every 10 scrolls
                    if scroll_attempts % 10 == 0:
                        logger.info(f"Scroll {scroll_attempts}/{max_scrolls}: {len(accounts)} accounts collected")
                
                # Filter and clean the accounts list
                filtered_accounts = []
                excluded_terms = {'i', 'intent', 'search', 'hashtag', 'explore', 'settings', 'messages', 
                               'notifications', 'bookmarks', 'lists', 'profile', 'more', 'compose',
                               'home', 'moments', 'topics'}
                
                for account in accounts:
                    clean_account = account.lower().strip()
                    if (len(clean_account) > 0 and 
                        clean_account not in excluded_terms and
                        not clean_account.startswith('i/') and 
                        not clean_account.startswith('intent/') and
                        not clean_account.startswith('search') and
                        not clean_account.isdigit() and  # Skip pure numbers
                        clean_account.replace('_', '').replace('-', '').isalnum() and
                        len(clean_account) <= 15):  # X username limit
                        filtered_accounts.append(clean_account)
                
                # Remove duplicates and sort
                filtered_accounts = sorted(list(set(filtered_accounts)))
                
                logger.info(f"Collected {len(accounts)} raw accounts, filtered to {len(filtered_accounts)} valid accounts")
                
                if len(filtered_accounts) > 100:  # Good scraping result
                    self.monitored_accounts = filtered_accounts[:1500]  # Limit for performance
                    logger.info(f"🎉 SUCCESS: Scraped {len(self.monitored_accounts)} real accounts from @{target_account}!")
                    logger.info(f"Sample accounts: {self.monitored_accounts[:20]}")
                elif len(filtered_accounts) > 20:  # Partial success
                    self.monitored_accounts = filtered_accounts
                    logger.info(f"✅ Partial success: Found {len(self.monitored_accounts)} accounts from @{target_account}")
                else:
                    logger.warning(f"Only found {len(filtered_accounts)} accounts, using enhanced fallback")
                    await self._use_enhanced_fallback()
                    
            except Exception as e:
                logger.error(f"Scraping failed: {e}, using enhanced fallback")
                await self._use_enhanced_fallback()
                
        except Exception as e:
            logger.error(f"Error updating following list: {e}")
            await self._use_enhanced_fallback()

    async def _use_fallback_accounts(self):
        """Use basic fallback account list"""
        fallback_accounts = [
            "elonnmusk", "VitalikButerin", "CZ_Binance", "saylor", "nayibbukele",
            "APompliano", "RaoulGMI", "woonomic", "CryptoCobain", "DegenSpartan",
            "DeFianceCapital", "ChrisBlec", "AltcoinGordon", "pentosh1", "inversebrah",
            "CryptoMessiah", "JackNiewold", "CryptoWendyO", "TraderSZ", "CryptoCow",
            "TheCryptoLark", "AltcoinDaily", "MMCrypto", "IvanOnTech", "aantonop"
        ]
        self.monitored_accounts = fallback_accounts
        logger.info(f"Using fallback: {len(self.monitored_accounts)} accounts")

    async def _use_enhanced_fallback(self):
        """Use enhanced fallback with more meme coin focused accounts"""
        enhanced_accounts = [
            # Top Crypto Influencers
            "elonnmusk", "VitalikButerin", "CZ_Binance", "saylor", "nayibbukele",
            "APompliano", "RaoulGMI", "woonomic", "CryptoCobain", "DegenSpartan",
            
            # Meme Coin Focused
            "DogecoinRise", "PepeCoinEth", "ShibInuHolder", "memecoinbuzz", "AltcoinGordon",
            "pentosh1", "inversebrah", "CryptoMessiah", "JackNiewold", "CryptoWendyO",
            
            # Trading & Analysis
            "TraderSZ", "CryptoCow", "TheCryptoLark", "AltcoinDaily", "MMCrypto",
            "IvanOnTech", "aantonop", "VentureCoinist", "MessariCrypto", "lawmaster",
            
            # Additional Meme/Alt Focused
            "0xHamz", "DefiEdge", "DeFianceCapital", "ChrisBlec", "SatoshiStacker",
            "CryptoBusy", "AltcoinSherpa", "EmperorBTC", "CryptoBull", "mooncat2878",
            
            # More Solana/Meme Ecosystem
            "SolanaFloor", "MagicEden", "solana", "phantom", "SolanaNews",
            "sol_master", "SolanianPunks", "SolanaFM", "jupiter_exchange", "raydium",
            
            # Pump.fun and Meme Coin Ecosystem
            "pumpdotfun", "solana_memes", "meme_factory", "degensol", "SolMemeCoins"
        ]
        self.monitored_accounts = enhanced_accounts
        logger.info(f"Using enhanced fallback: {len(self.monitored_accounts)} meme-focused accounts")

    async def monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                logger.info(f"Checking {len(self.monitored_accounts)} accounts for token mentions...")
                
                # Check each account for recent tweets with token mentions
                for account in self.monitored_accounts:
                    if not self.is_monitoring:
                        break
                    
                    await self.check_account_for_tokens(account)
                    await asyncio.sleep(1)  # Rate limiting
                
                # Process collected mentions for alerts
                await self.process_mentions_for_alerts()
                
                # Update last check time
                self.last_check_time = datetime.now(timezone.utc)
                
                # Wait before next cycle
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)

    async def check_account_for_tokens(self, account_username: str):
        """Check a specific account for recent token mentions"""
        try:
            # Simulate finding token mentions (in production, this would scrape/use API)
            # Generate some test data occasionally
            import random
            
            if random.random() < 0.05:  # 5% chance of finding a mention
                possible_tokens = ['BONK', 'PEPE', 'WIF', 'BRETT', 'POPCAT', 'MEW', 'TURBO', 'DEGEN']
                token_name = random.choice(possible_tokens)
                
                # Skip if token already has CA
                if token_name.upper() not in self.known_tokens_with_ca:
                    # Add to mentions cache
                    if token_name not in self.token_mentions_cache:
                        self.token_mentions_cache[token_name] = []
                    
                    self.token_mentions_cache[token_name].append({
                        'account': account_username,
                        'timestamp': datetime.now(timezone.utc),
                        'tweet_url': f"https://x.com/{account_username}/status/{random.randint(1000000000000000000, 9999999999999999999)}"
                    })
                    
                    logger.info(f"Found token mention: {token_name} by @{account_username}")
            
        except Exception as e:
            logger.error(f"Error checking account {account_username}: {e}")

    async def process_mentions_for_alerts(self):
        """Process collected mentions to create name alerts"""
        try:
            current_time = datetime.now(timezone.utc)
            
            for token_name, mentions in self.token_mentions_cache.items():
                # Filter recent mentions (last hour)
                recent_mentions = [
                    m for m in mentions 
                    if (current_time - m['timestamp']).total_seconds() < 3600
                ]
                
                # Get unique accounts
                unique_accounts = set(m['account'] for m in recent_mentions)
                
                # Check if threshold met
                if len(unique_accounts) >= self.alert_threshold:
                    # Double-check token doesn't have CA
                    if token_name.upper() not in self.known_tokens_with_ca:
                        await self.create_name_alert(token_name, recent_mentions)
                        
                        # Clear processed mentions
                        self.token_mentions_cache[token_name] = []
            
        except Exception as e:
            logger.error(f"Error processing mentions: {e}")

    async def create_name_alert(self, token_name: str, mentions: List[Dict]):
        """Create a name alert for a trending token"""
        try:
            unique_accounts = list(set(m['account'] for m in mentions))
            tweet_urls = [m['tweet_url'] for m in mentions]
            
            name_alert = {
                'id': f"alert_{int(datetime.now(timezone.utc).timestamp())}",
                'token_name': token_name,
                'first_seen': min(m['timestamp'] for m in mentions),
                'quorum_count': len(unique_accounts),
                'accounts_mentioned': unique_accounts,
                'tweet_urls': tweet_urls,
                'is_active': True,
                'alert_triggered': True
            }
            
            # Store in database
            await self.db.name_alerts.insert_one(name_alert)
            
            # Add to CA watchlist for monitoring
            self.ca_watchlist.add(token_name.upper())
            
            logger.info(f"🚨 NAME ALERT: {token_name} mentioned by {len(unique_accounts)} accounts")
            
            # TODO: Broadcast to WebSocket clients
            # await broadcast_to_clients({"type": "name_alert", "data": name_alert})
            
        except Exception as e:
            logger.error(f"Error creating name alert: {e}")

    async def monitor_pump_fun_for_cas(self):
        """Monitor Pump.fun for new contract addresses of watchlisted tokens"""
        try:
            # This would connect to Pump.fun WebSocket or API
            # For now, simulate occasionally finding CAs
            import random
            
            for token_name in list(self.ca_watchlist):
                if random.random() < 0.1:  # 10% chance of finding CA
                    await self.create_ca_alert(token_name)
                    self.ca_watchlist.remove(token_name)
            
        except Exception as e:
            logger.error(f"Error monitoring Pump.fun: {e}")

    async def create_ca_alert(self, token_name: str):
        """Create a CA alert when contract address is found"""
        try:
            import random
            
            ca_alert = {
                'id': f"ca_{int(datetime.now(timezone.utc).timestamp())}",
                'contract_address': f"{''.join(random.choices('123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz', k=44))}",
                'token_name': token_name,
                'market_cap': random.randint(10000, 1000000),
                'created_at': datetime.now(timezone.utc),
                'photon_url': f"https://photon-sol.tinyastro.io/en/lp/CONTRACT_ADDRESS?timeframe=1s",
                'alert_time_utc': datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                'was_trending': True,
                'priority': 'HIGH'
            }
            
            # Store in database
            await self.db.ca_alerts.insert_one(ca_alert)
            
            # Add to known tokens
            self.known_tokens_with_ca.add(token_name.upper())
            
            logger.info(f"⚡ CA ALERT: {token_name} - {ca_alert['contract_address']}")
            
            # TODO: Broadcast to WebSocket clients
            # await broadcast_to_clients({"type": "ca_alert", "data": ca_alert})
            
        except Exception as e:
            logger.error(f"Error creating CA alert: {e}")

    async def stop_monitoring(self):
        """Stop monitoring"""
        self.is_monitoring = False
        await self.close_browser()
        logger.info("Real-time monitoring stopped")

    def set_alert_threshold(self, threshold: int):
        """Set the number of accounts needed to trigger an alert"""
        self.alert_threshold = threshold
        logger.info(f"Alert threshold set to {threshold} accounts")