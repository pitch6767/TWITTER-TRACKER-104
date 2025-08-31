from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
import json
import websockets
import aiohttp
import re
from pathlib import Path
import random
from x_monitor_realtime import RealTimeXMonitor
from github_integration import GitHubIntegration
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid
import time

# Custom JSON encoder for datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Tweet Tracker", description="Real-time meme coin tracking from X accounts", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Global state management
active_websocket_connections: List[WebSocket] = []
name_alerts: List[Dict] = []
ca_alerts: List[Dict] = []
tracked_accounts: List[Dict] = []
performance_data: List[Dict] = []
app_versions: List[Dict] = []
blacklist_words = ["scam", "referral", "spam", "bot"]
whitelist_accounts = []
blacklist_accounts = []

# Pydantic Models
class AlertType(str, Enum):
    NAME_ALERT = "name_alert"
    CA_ALERT = "ca_alert"

class XAccount(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    display_name: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    name_alerts_contributed: int = 0
    accepted_cas_posted: int = 0
    max_gain_24h: float = 0.0

class TokenMention(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    token_name: str
    account_username: str
    tweet_url: str
    mentioned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processed: bool = False

class NameAlert(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    token_name: str
    first_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    quorum_count: int = 1
    accounts_mentioned: List[str] = []
    tweet_urls: List[str] = []
    is_active: bool = True
    alert_triggered: bool = False

class CAAlert(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    contract_address: str
    token_name: str
    market_cap: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    photon_url: str
    alert_time_utc: str

class AppVersion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    version_number: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tag_name: Optional[str] = None
    snapshot_data: Dict[str, Any]

class MonitoringConfig(BaseModel):
    alert_threshold: int = 2
    check_interval_seconds: int = 30
    enable_browser_monitoring: bool = True
    enable_rss_monitoring: bool = True
    enable_scraping_monitoring: bool = True
    filter_old_tokens: bool = True
    filter_tokens_with_ca: bool = True

class GitHubConfig(BaseModel):
    github_token: Optional[str] = None
    repository_name: str = "tweet-tracker-backups"
    auto_backup_enabled: bool = False
    backup_interval_hours: int = 24

class XAccountMonitor:
    def __init__(self):
        self.monitored_accounts = []
        self.is_monitoring = False
        self.known_tokens_with_ca = set()  # Track tokens that already have CAs
        self.token_patterns = [
            r'\$[A-Z]{2,10}\b',  # $TOKEN format
            r'\b[A-Z]{2,10}(?:\s+(?:coin|token|gem|moon|pump|lambo))b',  # TOKEN coin/token
            r'\b(?:DOGE|PEPE|SHIB|BONK|WIF|FLOKI|MEME|APE|WOJAK|TURBO|BRETT|POPCAT|DEGEN|MEW|BOBO|PEPE2|LADYS|BABYDOGE|DOGELON|AKITA|KISHU|SAFEMOON|HOGE|NFD|ELON|MILADY|BEN|ANDY|BART|MATT|TOSHI|HOPPY|MUMU|BENJI|POKEMON|SPURDO|BODEN|MAGA|SLERF|BOOK|MYRO|PONKE)\b',  # Common meme coins
        ]

    async def start_monitoring(self):
        """Start monitoring X accounts for token mentions"""
        self.is_monitoring = True
        logger.info("Starting X account monitoring...")
        
        # Get all active tracked accounts
        accounts = await db.x_accounts.find({"is_active": True}).to_list(1000)
        self.monitored_accounts = [acc['username'] for acc in accounts]
        
        logger.info(f"Monitoring {len(self.monitored_accounts)} X accounts")
        
        # Start monitoring loop
        asyncio.create_task(self.monitoring_loop())

    async def monitoring_loop(self):
        """Main monitoring loop that checks accounts periodically"""
        while self.is_monitoring:
            try:
                await self.check_accounts_for_mentions()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)

    async def check_accounts_for_mentions(self):
        """Check tracked accounts for new token mentions"""
        try:
            # Simulate checking X accounts (replace with actual implementation)
            for account in self.monitored_accounts:
                # For now, simulate finding token mentions
                await self.simulate_account_check(account)
        except Exception as e:
            logger.error(f"Error checking accounts: {e}")

    async def simulate_account_check(self, account_username):
        """Simulate checking an X account for token mentions"""
        # This simulates finding token mentions from the account
        # In a real implementation, this would scrape or use alternative APIs
        # Randomly simulate finding tokens (for demonstration)
        if random.random() < 0.1:  # 10% chance of finding a mention
            possible_tokens = ['BONK', 'PEPE', 'DOGE', 'WIF', 'BRETT', 'POPCAT', 'MEW', 'TURBO']
            token_name = random.choice(possible_tokens)
            
            # Create a simulated tweet URL
            tweet_url = f"https://x.com/{account_username}/status/{random.randint(1000000000000000000, 9999999999999999999)}"
            
            # Add the token mention
            mention = TokenMention(
                token_name=token_name,
                account_username=account_username,
                tweet_url=tweet_url
            )
            
            await self.process_token_mention(mention)

    async def process_token_mention(self, mention: TokenMention):
        """Process a found token mention"""
        try:
            # Store in database
            mention_dict = mention.dict()
            await db.token_mentions.insert_one(mention_dict)
            logger.info(f"Found token mention: {mention.token_name} by @{mention.account_username}")
            
            # Check for name alerts
            await self.check_for_name_alerts(mention.token_name)
        except Exception as e:
            logger.error(f"Error processing token mention: {e}")

    async def check_token_has_ca(self, token_name: str) -> bool:
        """Check if a token already has a Contract Address"""
        try:
            # Check in CA alerts collection
            ca_exists = await db.ca_alerts.find_one({
                "token_name": {"$regex": f"^{token_name}$", "$options": "i"}
            })
            
            if ca_exists:
                logger.info(f"Token {token_name} already has CA - filtering from Name Alerts")
                return True
            
            # Also check known tokens with CAs
            if token_name.upper() in self.known_tokens_with_ca:
                logger.info(f"Token {token_name} is in known tokens with CA - filtering from Name Alerts")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking if token has CA: {e}")
            return False  # If unsure, allow the alert

    async def check_for_name_alerts(self, token_name: str):
        """Check if this token mention should trigger a name alert (ONLY for tokens WITHOUT CA)"""
        try:
            # CRITICAL: Check if token already has a CA - if yes, NO name alert
            if await self.check_token_has_ca(token_name):
                logger.info(f"⚠️ Token {token_name} already has CA - skipping Name Alert")
                return
            
            # Get recent mentions of this token (last hour)
            from datetime import datetime, timedelta
            one_hour_ago = datetime.now() - timedelta(hours=1)
            
            recent_mentions = await db.token_mentions.find({
                "token_name": {"$regex": f"^{token_name}$", "$options": "i"},
                "mentioned_at": {"$gte": one_hour_ago},
                "processed": {"$ne": True}
            }).to_list(100)
            
            # Group by unique accounts
            unique_accounts = set()
            tweet_urls = []
            for mention in recent_mentions:
                unique_accounts.add(mention['account_username'])
                tweet_urls.append(mention['tweet_url'])
            
            # If 2+ unique accounts mentioned this token AND it has no CA, create alert
            if len(unique_accounts) >= 2:
                # Double-check token doesn't have CA before creating alert
                if await self.check_token_has_ca(token_name):
                    logger.info(f"⚠️ Token {token_name} got CA during processing - skipping Name Alert")
                    return
                
                name_alert = NameAlert(
                    token_name=token_name,
                    first_seen=min(mention['mentioned_at'] for mention in recent_mentions),
                    quorum_count=len(unique_accounts),
                    accounts_mentioned=list(unique_accounts),
                    tweet_urls=tweet_urls,
                    alert_triggered=True
                )
                
                # Store alert
                alert_dict = name_alert.dict()
                name_alerts.append(alert_dict)
                
                logger.info(f"🚨 NAME ALERT (NO CA): {token_name} mentioned by {len(unique_accounts)} accounts")
                
                # Broadcast to clients
                await broadcast_to_clients({
                    "type": "name_alert",
                    "data": alert_dict
                })
                
                # Mark mentions as processed
                await db.token_mentions.update_many(
                    {"token_name": {"$regex": f"^{token_name}$", "$options": "i"}},
                    {"$set": {"processed": True}}
                )
        except Exception as e:
            logger.error(f"Error checking for name alerts: {e}")

class PumpFunWebSocketClient:
    def __init__(self):
        self.websocket_url = "wss://pumpportal.fun/api/data"
        self.websocket = None
        self.is_connected = False
        self.reconnect_delay = 5

    async def connect(self):
        """Connect to Pump.fun WebSocket for real-time CA alerts"""
        while True:
            try:
                logger.info("Connecting to Pump.fun WebSocket...")
                self.websocket = await websockets.connect(
                    self.websocket_url,
                    ping_interval=20,
                    ping_timeout=10
                )
                self.is_connected = True
                logger.info("Connected to Pump.fun WebSocket")
                
                # Subscribe to new token launches
                await self.subscribe_to_new_tokens()
                await self.listen_for_messages()
                
            except Exception as e:
                logger.error(f"WebSocket connection failed: {e}")
                self.is_connected = False
                await asyncio.sleep(self.reconnect_delay)

    async def subscribe_to_new_tokens(self):
        """Subscribe to new token creation events"""
        if self.websocket and self.is_connected:
            subscription_message = {"method": "subscribeNewToken"}
            try:
                await self.websocket.send(json.dumps(subscription_message))
                logger.info("Subscribed to new token launches")
            except Exception as e:
                logger.error(f"Failed to subscribe: {e}")

    async def listen_for_messages(self):
        """Process incoming messages from Pump.fun"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self.process_pump_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Error in message loop: {e}")
            self.is_connected = False

    async def process_pump_message(self, message_data: dict):
        """Process Pump.fun messages and create CA alerts for trending tokens"""
        try:
            if message_data.get('type') == 'tokenCreate':
                token_data = message_data.get('data', {})
                token_name = token_data.get('name', 'Unknown').upper()
                
                # Check if token is less than 1 minute old
                created_time = datetime.now(timezone.utc)
                time_diff = (datetime.now(timezone.utc) - created_time).total_seconds()
                
                if time_diff <= 60:  # Less than 1 minute old
                    # Check if this token is being monitored (was trending)
                    monitored_token = await db.ca_monitoring_queue.find_one({
                        "token_name": {"$regex": f"^{token_name}$", "$options": "i"},
                        "status": "active"
                    })
                    
                    ca_alert = CAAlert(
                        contract_address=token_data.get('mint', ''),
                        token_name=token_name,
                        market_cap=token_data.get('marketCap', 0),
                        photon_url=f"https://photon-sol.tinyastro.io/en/lp/{token_data.get('mint', '')}?timeframe=1s",
                        alert_time_utc=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                    )
                    
                    # Enhanced alert data for trending tokens
                    alert_data = ca_alert.dict()
                    if monitored_token:
                        alert_data['was_trending'] = True
                        alert_data['mention_count'] = monitored_token.get('mention_count', 0)
                        alert_data['priority'] = 'HIGH'
                        
                        # Mark as processed in monitoring queue
                        await db.ca_monitoring_queue.update_one(
                            {"_id": monitored_token["_id"]},
                            {"$set": {"status": "ca_found", "ca_found_at": datetime.now(timezone.utc)}}
                        )
                        
                        logger.info(f"🚨🚀 TRENDING CA ALERT: {token_name} - {ca_alert.contract_address} (was mentioned by {monitored_token.get('mention_count', 0)} accounts)")
                    else:
                        alert_data['was_trending'] = False
                        alert_data['priority'] = 'NORMAL'
                        logger.info(f"🚨 CA ALERT: {token_name} - {ca_alert.contract_address}")
                    
                    ca_alerts.append(alert_data)
                    
                    # Store in database
                    await db.ca_alerts.insert_one(alert_data)
                    
                    # Broadcast to connected clients
                    await broadcast_to_clients({
                        "type": "ca_alert",
                        "data": alert_data
                    })
        except Exception as e:
            logger.error(f"Error processing Pump.fun message: {e}")

# Initialize WebSocket client and monitoring systems
pump_client = PumpFunWebSocketClient()
x_monitor = XAccountMonitor()
real_time_monitor = RealTimeXMonitor(db)
github_integration = GitHubIntegration()

# Global configuration
monitoring_config = MonitoringConfig()
github_config = GitHubConfig()

async def broadcast_to_clients(data: dict):
    """Broadcast data to all connected WebSocket clients"""
    if active_websocket_connections:
        disconnected_clients = []
        for connection in active_websocket_connections:
            try:
                await connection.send_text(json.dumps(data, cls=DateTimeEncoder))
            except Exception:
                disconnected_clients.append(connection)
        
        for connection in disconnected_clients:
            active_websocket_connections.remove(connection)

async def check_token_has_ca_server(token_name: str) -> bool:
    """Check if a token already has a Contract Address (server version)"""
    try:
        # Check in CA alerts collection
        ca_exists = await db.ca_alerts.find_one({
            "token_name": {"$regex": f"^{token_name}$", "$options": "i"}
        })
        
        if ca_exists:
            logger.info(f"Token {token_name} already has CA - filtering from Name Alerts")
            return True
        
        return False
    except Exception as e:
        logger.error(f"Error checking if token has CA: {e}")
        return False  # If unsure, allow the alert

async def check_name_alerts(token_mentions: List[TokenMention], threshold: int = 2):
    """Check if token mentions meet alert threshold (ONLY for tokens WITHOUT CA)"""
    token_counts = {}
    
    for mention in token_mentions:
        if not mention.processed:
            token_name = mention.token_name.lower()
            
            # CRITICAL: Skip tokens that already have CA
            if await check_token_has_ca_server(mention.token_name):
                logger.info(f"⚠️ Token {mention.token_name} already has CA - skipping Name Alert")
                continue
            
            if token_name not in token_counts:
                token_counts[token_name] = {
                    'count': 0,
                    'accounts': [],
                    'urls': [],
                    'first_seen': mention.mentioned_at
                }
            
            token_counts[token_name]['count'] += 1
            token_counts[token_name]['accounts'].append(mention.account_username)
            token_counts[token_name]['urls'].append(mention.tweet_url)
            
            if token_counts[token_name]['count'] >= threshold:
                # Double-check token doesn't have CA before creating alert
                if await check_token_has_ca_server(mention.token_name):
                    logger.info(f"⚠️ Token {mention.token_name} got CA during processing - skipping Name Alert")
                    continue
                
                # Create name alert ONLY for tokens without CA
                name_alert = NameAlert(
                    token_name=mention.token_name,
                    first_seen=token_counts[token_name]['first_seen'],
                    quorum_count=token_counts[token_name]['count'],
                    accounts_mentioned=token_counts[token_name]['accounts'],
                    tweet_urls=token_counts[token_name]['urls'],
                    alert_triggered=True
                )
                
                name_alerts.append(name_alert.dict())
                logger.info(f"🚨 NAME ALERT (NO CA): {name_alert.token_name} ({name_alert.quorum_count} mentions)")
                
                # Broadcast to clients
                await broadcast_to_clients({
                    "type": "name_alert",
                    "data": name_alert.dict()
                })
                
                # Mark mentions as processed
                for mention in token_mentions:
                    if mention.token_name.lower() == token_name:
                        mention.processed = True

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Tweet Tracker API", "version": "1.0.0"}

@api_router.get("/accounts", response_model=List[XAccount])
async def get_tracked_accounts():
    """Get list of tracked X accounts"""
    accounts = await db.x_accounts.find().to_list(1000)
    return [XAccount(**account) for account in accounts]

@api_router.post("/accounts", response_model=XAccount)
async def add_tracked_account(account: XAccount):
    """Add new X account to track"""
    account_dict = account.dict()
    await db.x_accounts.insert_one(account_dict)
    tracked_accounts.append(account_dict)
    return account

class ManualAccountImport(BaseModel):
    accounts: List[str]
    source: str = "manual_import"

@api_router.post("/accounts/import")
async def import_sploofmeme_accounts(import_data: ManualAccountImport):
    """Import real @Sploofmeme following accounts manually"""
    try:
        global tracked_accounts
        
        # Clean and validate usernames
        clean_accounts = []
        for account in import_data.accounts:
            clean_username = account.strip().lower().replace('@', '')
            if (len(clean_username) > 0 and 
                clean_username.replace('_', '').replace('-', '').isalnum() and
                len(clean_username) <= 15):
                clean_accounts.append(clean_username)
        
        # Create account objects
        imported_accounts = []
        for username in clean_accounts:
            account_obj = {
                "id": str(uuid.uuid4()),
                "username": username,
                "display_name": username,
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "source": import_data.source
            }
            
            # Store in database
            await db.x_accounts.insert_one(account_obj)
            imported_accounts.append(account_obj)
        
        # Update tracked accounts
        tracked_accounts.extend(imported_accounts)
        
        # Update real-time monitor if it exists
        if hasattr(real_time_monitor, 'monitored_accounts'):
            real_time_monitor.monitored_accounts = clean_accounts
            logger.info(f"✅ Real-time monitor updated with {len(clean_accounts)} @Sploofmeme accounts")
        
        logger.info(f"✅ Imported {len(clean_accounts)} real @Sploofmeme following accounts")
        
        return {
            "message": f"Successfully imported {len(clean_accounts)} @Sploofmeme following accounts",
            "imported_count": len(clean_accounts),
            "accounts": clean_accounts[:20],  # Show first 20
            "total_tracked": len(tracked_accounts)
        }
        
    except Exception as e:
        logger.error(f"Error importing accounts: {e}")
        return {"error": str(e)}

@api_router.post("/mentions")
async def add_token_mention(mention: TokenMention):
    """Add token mention from X account (manual input for testing)"""
    mention_dict = mention.dict()
    await db.token_mentions.insert_one(mention_dict)
    
    # Use X monitor to process the mention
    await x_monitor.process_token_mention(mention)
    
    return {"message": "Token mention added successfully"}

@api_router.post("/monitoring/start")
async def start_monitoring():
    """Start real-time X account monitoring of all @Sploofmeme follows"""
    try:
        # Start real-time monitoring of all accounts @Sploofmeme follows
        asyncio.create_task(real_time_monitor.start_monitoring("Sploofmeme"))
        
        return {
            "message": "Real-time monitoring started - tracking ALL accounts @Sploofmeme follows",
            "monitoring_type": "auto_follow_tracking",
            "alert_threshold": real_time_monitor.alert_threshold,
            "check_interval": "30_seconds",
            "target_account": "Sploofmeme"
        }
    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        return {"error": str(e)}

@api_router.post("/monitoring/stop")
async def stop_monitoring():
    """Stop real-time X account monitoring"""
    await real_time_monitor.stop_monitoring()
    return {"message": "Real-time X account monitoring stopped"}

@api_router.get("/monitoring/status")
async def get_monitoring_status():
    """Get current monitoring status"""
    return {
        "is_monitoring": real_time_monitor.is_monitoring,
        "monitored_accounts_count": len(real_time_monitor.monitored_accounts),
        "accounts": real_time_monitor.monitored_accounts[:10],  # Show only first 10 for reference
        "alert_threshold": real_time_monitor.alert_threshold,
        "monitoring_type": "sploofmeme_auto_follow_tracking",
        "last_check": real_time_monitor.last_check_time.isoformat() if real_time_monitor.last_check_time else None,
        "known_tokens_filtered": len(real_time_monitor.known_tokens_with_ca),
        "target_account": "Sploofmeme",
        "real_following_count": len(real_time_monitor.monitored_accounts)
    }

@api_router.post("/monitoring/config")
async def update_monitoring_config(config: MonitoringConfig):
    """Update monitoring configuration"""
    global monitoring_config
    monitoring_config = config
    
    # Update real-time monitor settings
    real_time_monitor.set_alert_threshold(config.alert_threshold)
    
    return {
        "message": "Monitoring configuration updated",
        "config": config.dict()
    }

@api_router.get("/monitoring/config")
async def get_monitoring_config():
    """Get current monitoring configuration"""
    return monitoring_config.dict()

@api_router.get("/alerts/names")
async def get_name_alerts():
    """Get all name alerts"""
    return {"alerts": name_alerts}

@api_router.get("/alerts/cas")
async def get_ca_alerts():
    """Get all CA alerts"""
    return {"alerts": ca_alerts}

@api_router.get("/performance")
async def get_performance_data():
    """Get performance metrics for tracked accounts"""
    return {"performance": performance_data}

@api_router.post("/versions/save")
async def save_version(version: AppVersion):
    """Save current app state as a version"""
    version_dict = version.dict()
    version_dict['snapshot_data'] = {
        'tracked_accounts': tracked_accounts,
        'name_alerts': name_alerts,
        'ca_alerts': ca_alerts,
        'performance_data': performance_data,
        'blacklist_words': blacklist_words,
        'whitelist_accounts': whitelist_accounts,
        'blacklist_accounts': blacklist_accounts
    }
    
    await db.app_versions.insert_one(version_dict)
    app_versions.append(version_dict)
    
    # Keep only last 10 versions
    if len(app_versions) > 10:
        app_versions.pop(0)
    
    return {"message": "Version saved successfully", "version": version_dict}

@api_router.get("/versions")
async def get_versions():
    """Get all saved versions"""
    versions = await db.app_versions.find().to_list(100)
    return {"versions": versions}

@api_router.post("/versions/{version_id}/load")
async def load_version(version_id: str):
    """Load a specific version and restore app state"""
    version = await db.app_versions.find_one({"id": version_id})
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # Restore app state
    global tracked_accounts, name_alerts, ca_alerts, performance_data
    global blacklist_words, whitelist_accounts, blacklist_accounts
    
    snapshot = version['snapshot_data']
    tracked_accounts = snapshot.get('tracked_accounts', [])
    name_alerts = snapshot.get('name_alerts', [])
    ca_alerts = snapshot.get('ca_alerts', [])
    performance_data = snapshot.get('performance_data', [])
    blacklist_words = snapshot.get('blacklist_words', [])
    whitelist_accounts = snapshot.get('whitelist_accounts', [])
    blacklist_accounts = snapshot.get('blacklist_accounts', [])
    
    return {"message": "Version loaded successfully", "version": version}

# GitHub Integration Endpoints
class GitHubSetupRequest(BaseModel):
    github_token: str
    username: str

@api_router.post("/github/setup")
async def setup_github_integration(request: GitHubSetupRequest):
    """Setup GitHub integration with user token"""
    try:
        global github_integration, github_config
        github_config.github_token = request.github_token
        github_integration = GitHubIntegration(request.github_token)
        
        success = await github_integration.initialize_repository(request.username)
        if success:
            return {"message": "GitHub integration setup successfully", "repository": f"{request.username}/tweet-tracker-backups"}
        else:
            return {"error": "Failed to setup GitHub integration"}
    except Exception as e:
        return {"error": str(e)}

class GitHubBackupRequest(BaseModel):
    version_tag: str

@api_router.post("/github/backup")
async def create_github_backup(request: GitHubBackupRequest):
    """Create a backup to GitHub"""
    try:
        app_data = {
            'tracked_accounts': tracked_accounts,
            'name_alerts': name_alerts,
            'ca_alerts': ca_alerts,
            'performance_data': performance_data,
            'blacklist_words': blacklist_words,
            'whitelist_accounts': whitelist_accounts,
            'blacklist_accounts': blacklist_accounts,
            'monitoring_config': monitoring_config.dict()
        }
        
        result = await github_integration.create_backup(app_data, request.version_tag)
        return result
    except Exception as e:
        return {"error": str(e)}

@api_router.get("/github/backups")
async def list_github_backups():
    """List all GitHub backups"""
    try:
        backups = await github_integration.list_backups()
        return {"backups": backups}
    except Exception as e:
        return {"error": str(e)}

@api_router.post("/github/restore/{backup_path:path}")
async def restore_github_backup(backup_path: str):
    """Restore from GitHub backup"""
    try:
        result = await github_integration.restore_backup(backup_path)
        if result["success"]:
            # Restore app state
            global tracked_accounts, name_alerts, ca_alerts, performance_data
            global blacklist_words, whitelist_accounts, blacklist_accounts
            
            app_data = result["app_data"]
            tracked_accounts = app_data.get('tracked_accounts', [])
            name_alerts = app_data.get('name_alerts', [])
            ca_alerts = app_data.get('ca_alerts', [])
            performance_data = app_data.get('performance_data', [])
            blacklist_words = app_data.get('blacklist_words', [])
            whitelist_accounts = app_data.get('whitelist_accounts', [])
            blacklist_accounts = app_data.get('blacklist_accounts', [])
        
        return result
    except Exception as e:
        return {"error": str(e)}

@api_router.delete("/github/backup/{backup_path:path}")
async def delete_github_backup(backup_path: str):
    """Delete a GitHub backup"""
    try:
        success = await github_integration.delete_backup(backup_path)
        return {"success": success}
    except Exception as e:
        return {"error": str(e)}

@api_router.get("/github/stats")
async def get_github_stats():
    """Get GitHub repository statistics"""
    try:
        stats = await github_integration.get_repository_stats()
        return stats
    except Exception as e:
        return {"error": str(e)}

@api_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    active_websocket_connections.append(websocket)
    
    try:
        # Send current state to newly connected client
        await websocket.send_text(json.dumps({
            "type": "initial_state",
            "data": {
                "name_alerts": name_alerts[-10:],
                "ca_alerts": ca_alerts[-10:],
                "tracked_accounts_count": len(tracked_accounts)
            }
        }, cls=DateTimeEncoder))
        
        while True:
            try:
                data = await websocket.receive_text()
                client_message = json.loads(data)
                
                if client_message.get('type') == 'ping':
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }, cls=DateTimeEncoder))
            except Exception as e:
                logger.error(f"Error processing client message: {e}")
                break
    
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if websocket in active_websocket_connections:
            active_websocket_connections.remove(websocket)

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Tweet Tracker...")
    
    # Start Pump.fun WebSocket client in background
    asyncio.create_task(pump_client.connect())
    
    # Start X account monitoring
    await asyncio.sleep(2)  # Give time for DB to be ready
    await x_monitor.start_monitoring()
    
    logger.info("Tweet Tracker started successfully")

@app.on_event("shutdown")
async def shutdown_db_client():
    """Cleanup on shutdown"""
    logger.info("Shutting down Tweet Tracker...")
    client.close()
    
    # Close all WebSocket connections
    for connection in active_websocket_connections:
        try:
            await connection.close()
        except Exception:
            pass