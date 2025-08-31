import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import { Bell, Activity, Users, TrendingUp, Save, RotateCcw, Settings, AlertTriangle, ExternalLink, Clock, DollarSign, Github, Zap, Filter, Shield } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Button } from './components/ui/button';
import { Badge } from './components/ui/badge';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog';
import { toast } from './hooks/use-toast';
import { Toaster } from './components/ui/toaster';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const WS_URL = `${BACKEND_URL}/api/ws`.replace('https://', 'wss://').replace('http://', 'ws://');

function TweetTracker() {
  const [nameAlerts, setNameAlerts] = useState([]);
  const [caAlerts, setCaAlerts] = useState([]);
  const [trackedAccounts, setTrackedAccounts] = useState([]);
  const [performanceData, setPerformanceData] = useState([]);
  const [versions, setVersions] = useState([]);
  const [alertThreshold, setAlertThreshold] = useState(2);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [monitoringStatus, setMonitoringStatus] = useState({
    is_monitoring: false,
    monitored_accounts_count: 0,
    accounts: []
  });

  const [bulkAccountsText, setBulkAccountsText] = useState('');
  const [newAccountUsername, setNewAccountUsername] = useState('');
  const [newAccountDisplayName, setNewAccountDisplayName] = useState('');

  const bulkImportAccounts = async () => {
    if (!bulkAccountsText.trim()) {
      toast({
        title: "Error",
        description: "Please paste the accounts list",
        variant: "destructive"
      });
      return;
    }

    try {
      const response = await fetch(`${API}/accounts/bulk-import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          accounts_text: bulkAccountsText,
          separator: ",",
          source: "sploofmeme_following"
        })
      });

      const result = await response.json();
      if (result.success) {
        setBulkAccountsText('');
        toast({
          title: "🎉 Bulk Import Successful!",
          description: `Imported ${result.imported_count} REAL @Sploofmeme accounts`,
        });
        fetchInitialData(); // Refresh data
      } else {
        toast({
          title: "Error",
          description: result.error || "Failed to import accounts",
          variant: "destructive"
        });
      }
    } catch (error) {
      console.error('Error bulk importing accounts:', error);
      toast({
        title: "Error",
        description: "Failed to bulk import accounts",
        variant: "destructive"
      });
    }
  };
  const [tokenMention, setTokenMention] = useState({
    token_name: '',
    account_username: '',
    tweet_url: ''
  });
  const [alertThresholdConfig, setAlertThresholdConfig] = useState(2);
  const [githubToken, setGithubToken] = useState('');
  const [githubUsername, setGithubUsername] = useState('pitch6767');
  const [githubBackups, setGithubBackups] = useState([]);
  const [githubStats, setGithubStats] = useState({});

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  useEffect(() => {
    fetchInitialData();
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  const fetchInitialData = async () => {
    try {
      const [alertsName, alertsCA, accounts, performance, versionsData, monitoringStatusData, githubBackupsData, githubStatsData] = await Promise.all([
        fetch(`${API}/alerts/names`).then(r => r.json()),
        fetch(`${API}/alerts/cas`).then(r => r.json()),
        fetch(`${API}/accounts`).then(r => r.json()),
        fetch(`${API}/performance`).then(r => r.json()),
        fetch(`${API}/versions`).then(r => r.json()),
        fetch(`${API}/monitoring/status`).then(r => r.json()),
        fetch(`${API}/github/backups`).then(r => r.json()).catch(() => ({ backups: [] })),
        fetch(`${API}/github/stats`).then(r => r.json()).catch(() => ({}))
      ]);

      setNameAlerts(alertsName.alerts || []);
      setCaAlerts(alertsCA.alerts || []);
      setTrackedAccounts(accounts || []);
      setPerformanceData(performance.performance || []);
      setVersions(versionsData.versions || []);
      setMonitoringStatus(monitoringStatusData);
      setAlertThresholdConfig(monitoringStatusData.alert_threshold || 2);
      setGithubBackups(githubBackupsData.backups || []);
      setGithubStats(githubStatsData);
    } catch (error) {
      console.error('Error fetching initial data:', error);
      toast({
        title: "Error",
        description: "Failed to load initial data",
        variant: "destructive"
      });
    }
  };

  const connectWebSocket = () => {
    try {
      wsRef.current = new WebSocket(WS_URL);

      wsRef.current.onopen = () => {
        setConnectionStatus('connected');
        toast({
          title: "Connected",
          description: "Real-time alerts are now active",
        });
      };

      wsRef.current.onmessage = (event) => {
        const message = JSON.parse(event.data);
        switch (message.type) {
          case 'name_alert':
            setNameAlerts(prev => [message.data, ...prev]);
            toast({
              title: "🚨 Name Alert!",
              description: `${message.data.token_name} mentioned by ${message.data.quorum_count} accounts`,
            });
            break;
          case 'ca_alert':
            setCaAlerts(prev => [message.data, ...prev]);
            toast({
              title: "⚡ CA Alert!",
              description: `New token: ${message.data.token_name}`,
            });
            break;
          case 'initial_state':
            setNameAlerts(message.data.name_alerts || []);
            setCaAlerts(message.data.ca_alerts || []);
            break;
        }
      };

      wsRef.current.onclose = () => {
        setConnectionStatus('disconnected');
        reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000);
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('error');
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      setConnectionStatus('error');
    }
  };

  const addTrackedAccount = async () => {
    if (!newAccountUsername.trim()) return;

    try {
      const response = await fetch(`${API}/accounts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: newAccountUsername,
          display_name: newAccountDisplayName || newAccountUsername
        })
      });

      if (response.ok) {
        const newAccount = await response.json();
        setTrackedAccounts(prev => [...prev, newAccount]);
        setNewAccountUsername('');
        setNewAccountDisplayName('');
        toast({
          title: "Account Added",
          description: `Now tracking @${newAccount.username}`,
        });
      }
    } catch (error) {
      console.error('Error adding account:', error);
      toast({
        title: "Error",
        description: "Failed to add account",
        variant: "destructive"
      });
    }
  };

  const addTokenMention = async () => {
    if (!tokenMention.token_name.trim() || !tokenMention.account_username.trim()) return;

    try {
      const response = await fetch(`${API}/mentions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(tokenMention)
      });

      if (response.ok) {
        setTokenMention({ token_name: '', account_username: '', tweet_url: '' });
        toast({
          title: "Mention Added",
          description: `Token mention tracked: ${tokenMention.token_name}`,
        });
      }
    } catch (error) {
      console.error('Error adding mention:', error);
      toast({
        title: "Error",
        description: "Failed to add token mention",
        variant: "destructive"
      });
    }
  };

  const saveVersion = async () => {
    try {
      const response = await fetch(`${API}/versions/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          version_number: `v${Date.now()}`,
          tag_name: `Snapshot ${new Date().toLocaleString()}`
        })
      });

      if (response.ok) {
        const savedVersion = await response.json();
        setVersions(prev => [savedVersion.version, ...prev]);
        toast({
          title: "Version Saved",
          description: "Current state has been saved",
        });
      }
    } catch (error) {
      console.error('Error saving version:', error);
      toast({
        title: "Error",
        description: "Failed to save version",
        variant: "destructive"
      });
    }
  };

  const startMonitoring = async () => {
    try {
      const response = await fetch(`${API}/monitoring/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (response.ok) {
        const result = await response.json();
        setMonitoringStatus(prev => ({
          ...prev,
          is_monitoring: true,
          monitored_accounts_count: result.accounts_count
        }));
        toast({
          title: "🚀 Monitoring Started!",
          description: `Now monitoring ${result.accounts_count} X accounts automatically`,
        });
      }
    } catch (error) {
      console.error('Error starting monitoring:', error);
      toast({
        title: "Error",
        description: "Failed to start monitoring",
        variant: "destructive"
      });
    }
  };

  const stopMonitoring = async () => {
    try {
      const response = await fetch(`${API}/monitoring/stop`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (response.ok) {
        setMonitoringStatus(prev => ({
          ...prev,
          is_monitoring: false
        }));
        toast({
          title: "⏹️ Monitoring Stopped",
          description: "Automatic X account monitoring has been stopped",
        });
      }
    } catch (error) {
      console.error('Error stopping monitoring:', error);
      toast({
        title: "Error",
        description: "Failed to stop monitoring",
        variant: "destructive"
      });
    }
  };

  const updateAlertThreshold = async () => {
    try {
      const response = await fetch(`${API}/monitoring/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          alert_threshold: alertThresholdConfig,
          check_interval_seconds: 30,
          enable_browser_monitoring: true,
          enable_rss_monitoring: true,
          enable_scraping_monitoring: true,
          filter_old_tokens: true,
          filter_tokens_with_ca: true
        })
      });

      if (response.ok) {
        toast({
          title: "⚙️ Settings Updated",
          description: `Alert threshold set to ${alertThresholdConfig} accounts`,
        });
      }
    } catch (error) {
      console.error('Error updating config:', error);
      toast({
        title: "Error",
        description: "Failed to update settings",
        variant: "destructive"
      });
    }
  };

  const setupGitHub = async () => {
    if (!githubToken.trim()) {
      toast({
        title: "⚠️ Token Required",
        description: "Please enter your GitHub Personal Access Token (not password!)",
        variant: "destructive"
      });
      return;
    }

    if (!githubUsername.trim()) {
      toast({
        title: "⚠️ Username Required",
        description: "Please enter your GitHub username",
        variant: "destructive"
      });
      return;
    }

    if (!githubToken.startsWith('ghp_')) {
      toast({
        title: "⚠️ Invalid Token Format",
        description: "GitHub tokens start with 'ghp_'. Please check your token.",
        variant: "destructive"
      });
      return;
    }

    try {
      const response = await fetch(`${API}/github/setup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          github_token: githubToken,
          username: githubUsername
        })
      });

      const result = await response.json();
      if (result.repository) {
        toast({
          title: "🎉 GitHub Connected!",
          description: `Repository: ${result.repository}`,
        });
        fetchInitialData(); // Refresh to get backups
      } else {
        let errorMsg = "Unknown error";
        if (result.error?.includes("Bad credentials")) {
          errorMsg = "Invalid token. Please check your GitHub Personal Access Token.";
        } else if (result.error?.includes("Not Found")) {
          errorMsg = "Username not found. Please check your GitHub username.";
        } else if (result.error?.includes("rate limit")) {
          errorMsg = "GitHub rate limit exceeded. Please try again later.";
        } else {
          errorMsg = result.error || "Failed to setup GitHub";
        }

        toast({
          title: "❌ GitHub Connection Failed",
          description: errorMsg,
          variant: "destructive"
        });
      }
    } catch (error) {
      console.error('Error setting up GitHub:', error);
      toast({
        title: "❌ Connection Error",
        description: "Failed to connect to GitHub. Check your internet connection.",
        variant: "destructive"
      });
    }
  };

  const createGitHubBackup = async () => {
    try {
      const version_tag = `backup_${new Date().toISOString().split('T')[0]}`;
      const response = await fetch(`${API}/github/backup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ version_tag })
      });

      const result = await response.json();
      if (result.success) {
        toast({
          title: "☁️ GitHub Backup Created!",
          description: `Backup saved to GitHub repository`,
        });
        fetchInitialData(); // Refresh backups
      } else {
        toast({
          title: "Error",
          description: result.error || "Failed to create GitHub backup",
          variant: "destructive"
        });
      }
    } catch (error) {
      console.error('Error creating GitHub backup:', error);
      toast({
        title: "Error",
        description: "Failed to create GitHub backup",
        variant: "destructive"
      });
    }
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 text-white">
      <div className="container mx-auto p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center space-x-3">
            <div className="p-3 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg">
              <TrendingUp className="h-8 w-8" />
            </div>
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
                Tweet Tracker
              </h1>
              <p className="text-slate-400">Real-time meme coin monitoring</p>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <Badge variant={connectionStatus === 'connected' ? 'default' : 'destructive'}>
              {connectionStatus === 'connected' ? '🟢 Live' : '🔴 Offline'}
            </Badge>
            <Badge variant={monitoringStatus.is_monitoring ? 'default' : 'secondary'}>
              {monitoringStatus.is_monitoring ? '👁️ Monitoring' : '⏸️ Stopped'}
            </Badge>
            <Button onClick={saveVersion} className="bg-purple-600 hover:bg-purple-700">
              <Save className="h-4 w-4 mr-2" />
              Save Version
            </Button>
          </div>
        </div>

        {/* Main Content */}
        <Tabs defaultValue="alerts" className="space-y-6">
          <TabsList className="bg-slate-800 border-slate-700">
            <TabsTrigger value="alerts" className="data-[state=active]:bg-purple-600">
              <Bell className="h-4 w-4 mr-2" />
              Alerts
            </TabsTrigger>
            <TabsTrigger value="accounts" className="data-[state=active]:bg-purple-600">
              <Users className="h-4 w-4 mr-2" />
              Accounts ({monitoringStatus.monitored_accounts_count || 0})
            </TabsTrigger>
            <TabsTrigger value="performance" className="data-[state=active]:bg-purple-600">
              <Activity className="h-4 w-4 mr-2" />
              Performance
            </TabsTrigger>
          </TabsList>

          {/* Alerts Tab */}
          <TabsContent value="alerts" className="space-y-6">
            {/* CA Alerts - Full Width Trading Window */}
            <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="flex items-center text-green-400">
                  <TrendingUp className="h-5 w-5 mr-2" />
                  CA Alerts ({caAlerts.length}) • Trending Token Launches
                </CardTitle>
                <CardDescription>
                  New contract addresses from trending tokens (&lt;1 min old) • Background tracking: {alertThresholdConfig} mentions needed
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4 max-h-96 overflow-y-auto">
                  {caAlerts.length > 0 ? caAlerts.map((alert, index) => (
                    <div key={alert.id || index} className="p-4 bg-slate-700/50 rounded-lg border-l-4 border-green-500 relative">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="font-semibold text-green-300">{alert.token_name}</h3>
                        <div className="flex items-center space-x-2">
                          <Badge variant="outline" className="text-green-400 border-green-400">
                            <DollarSign className="h-3 w-3 mr-1" />
                            {formatCurrency(alert.market_cap)}
                          </Badge>
                          <Badge variant="outline" className="text-yellow-400 border-yellow-400 animate-pulse">
                            🚀 TRENDING
                          </Badge>
                        </div>
                      </div>
                      <div className="text-sm text-slate-400 space-y-2">
                        <div className="flex items-center">
                          <Clock className="h-3 w-3 mr-1" />
                          {alert.alert_time_utc} • Less than 1 minute old
                        </div>
                        <div className="font-mono text-xs bg-slate-800 p-2 rounded">
                          CA: {alert.contract_address}
                        </div>
                        <div className="flex items-center space-x-2">
                          <a
                            href={`https://photon-sol.tinyastro.io/en/lp/${alert.contract_address}?timeframe=1s`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 px-4 py-2 rounded-lg text-sm font-medium transition-all transform hover:scale-105 shadow-lg"
                          >
                            <TrendingUp className="h-4 w-4 mr-2" />
                            📈 1s Chart • TRADE NOW
                          </a>
                          <button
                            onClick={() => navigator.clipboard.writeText(alert.contract_address)}
                            className="inline-flex items-center bg-slate-600 hover:bg-slate-700 px-3 py-2 rounded-lg text-xs transition-colors"
                          >
                            📋 Copy CA
                          </button>
                          <a
                            href={`https://dexscreener.com/solana/${alert.contract_address}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center bg-orange-600 hover:bg-orange-700 px-3 py-2 rounded-lg text-xs transition-colors"
                          >
                            📊 DexScreener
                          </a>
                        </div>
                        <div className="text-xs text-yellow-400 bg-yellow-900/20 p-2 rounded border border-yellow-500/30">
                          ⚡ This token was mentioned by multiple accounts before getting CA - High priority trading opportunity!
                        </div>
                      </div>
                    </div>
                  )) : (
                    <div className="text-center text-slate-500 py-12">
                      <TrendingUp className="h-16 w-16 mx-auto mb-4 opacity-50" />
                      <div className="space-y-2">
                        <p className="text-lg font-medium">🎯 Waiting for Trending Token Launches</p>
                        <p className="text-sm">Background system is monitoring @Sploofmeme follows...</p>
                        <p className="text-xs text-green-400">CA alerts will appear when trending tokens get new contracts &lt;1 min old</p>
                        <div className="mt-4 p-3 bg-slate-800/50 rounded-lg border border-green-500/30">
                          <p className="text-xs text-slate-400">
                            🔍 Active: {monitoringStatus.monitored_accounts_count} accounts •
                            ⚙️ Threshold: {alertThresholdConfig} mentions •
                            ⚡ Check: Every 30s
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Accounts Tab */}
          <TabsContent value="accounts" className="space-y-6">
            {/* Bulk Import Real @Sploofmeme Accounts */}
            <Card className="bg-gradient-to-r from-blue-900/30 to-green-900/30 border-blue-500/30 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-blue-400 flex items-center">
                  <Users className="h-5 w-5 mr-2" />
                  Import REAL @Sploofmeme Following List (800 accounts)
                </CardTitle>
                <CardDescription>
                  Paste your exported list of accounts that @Sploofmeme follows - supports comma, newline, or space separated
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="bulk-accounts">Paste 800 @Sploofmeme Accounts Here</Label>
                    <textarea
                      id="bulk-accounts"
                      placeholder="Paste your account list here... 
Examples:
elonmusk, vitalikbuterin, cz_binance, saylor
OR
elonmusk
vitalikbuterin  
cz_binance
saylor"
                      value={bulkAccountsText}
                      onChange={(e) => setBulkAccountsText(e.target.value)}
                      className="w-full h-32 p-3 bg-slate-700 border-slate-600 rounded-lg text-sm"
                      rows={6}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="text-sm text-slate-400">
                      Supports: comma separated, newline separated, or space separated
                    </div>
                    <Button 
                      onClick={bulkImportAccounts} 
                      className="bg-green-600 hover:bg-green-700"
                      disabled={!bulkAccountsText.trim()}
                    >
                      <Users className="h-4 w-4 mr-2" />
                      Import {bulkAccountsText.trim().split(/[,\n\r\s]+/).length} Accounts
                    </Button>
                  </div>
                  <div className="text-xs text-green-400 bg-green-900/20 p-3 rounded border border-green-500/30">
                    💡 This will replace the current 130 accounts with your full 800 @Sploofmeme following list
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Real-time Monitoring Control */}
            <Card className="bg-gradient-to-r from-green-900/30 to-blue-900/30 border-green-500/30 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-green-400 flex items-center">
                  <Zap className="h-5 w-5 mr-2" />
                  Auto-Track @Sploofmeme Following List
                </CardTitle>
                <CardDescription>
                  Automatically monitors ALL accounts @Sploofmeme follows (~1000 accounts) every 30 seconds
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-2">
                      <div className="flex items-center space-x-4">
                        <Badge variant={monitoringStatus.is_monitoring ? 'default' : 'secondary'} className="text-sm">
                          {monitoringStatus.is_monitoring ? '🚀 Auto-Tracking Active' : '⏸️ Auto-Tracking Stopped'}
                        </Badge>
                        <span className="text-sm text-slate-400">
                          {monitoringStatus.monitored_accounts_count} @Sploofmeme follows • 30s intervals
                        </span>
                      </div>
                      <div className="flex items-center space-x-2 text-xs text-slate-500">
                        <Shield className="h-3 w-3" />
                        <span>Smart filtering: Old tokens & CAs filtered ({monitoringStatus.known_tokens_filtered || 0})</span>
                      </div>
                      <div className="flex items-center space-x-2 text-xs text-green-400">
                        <Users className="h-3 w-3" />
                        <span>Auto-discovers ALL accounts @Sploofmeme follows (no manual setup)</span>
                      </div>
                    </div>
                    <div className="flex space-x-2">
                      {!monitoringStatus.is_monitoring ? (
                        <Button onClick={startMonitoring} className="bg-green-600 hover:bg-green-700">
                          <Zap className="h-4 w-4 mr-2" />
                          Start Auto-Track
                        </Button>
                      ) : (
                        <Button onClick={stopMonitoring} variant="outline" className="border-red-500 text-red-400 hover:bg-red-500/10">
                          <Activity className="h-4 w-4 mr-2" />
                          Stop Tracking
                        </Button>
                      )}
                    </div>
                  </div>

                  {/* Alert Threshold Configuration */}
                  <div className="flex items-center space-x-4 p-3 bg-slate-800/50 rounded-lg">
                    <Filter className="h-4 w-4 text-purple-400" />
                    <Label htmlFor="threshold" className="text-sm">Alert when</Label>
                    <Input
                      id="threshold"
                      type="number"
                      min="1"
                      max="10"
                      value={alertThresholdConfig}
                      onChange={(e) => setAlertThresholdConfig(parseInt(e.target.value))}
                      className="w-20 bg-slate-700 border-slate-600"
                    />
                    <span className="text-xs text-slate-400">accounts mention same token</span>
                    <Button onClick={updateAlertThreshold} size="sm" className="bg-purple-600 hover:bg-purple-700">
                      Update
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-blue-400">@Sploofmeme Following Status</CardTitle>
                <CardDescription>
                  Real-time count of accounts being monitored from @Sploofmeme's following list
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8">
                  <div className="text-6xl font-bold text-green-400 mb-4">
                    {monitoringStatus.real_following_count || monitoringStatus.monitored_accounts_count || 0}
                  </div>
                  <p className="text-xl text-slate-300 mb-2">@Sploofmeme Following Accounts</p>
                  <p className="text-sm text-slate-500 mb-4">
                    {monitoringStatus.monitoring_type === 'sploofmeme_auto_follow_tracking' ?
                      'Real-time sync from @Sploofmeme X account' :
                      'Using fallback accounts (browser initialization pending)'
                    }
                  </p>
                  <div className="bg-slate-700/50 p-4 rounded-lg">
                    <p className="text-xs text-slate-400 mb-2">
                      💡 To add/remove accounts: Follow or unfollow them on @Sploofmeme's X account
                    </p>
                    <p className="text-xs text-slate-500">
                      System automatically syncs every monitoring cycle (30s)
                    </p>
                    {(monitoringStatus.monitored_accounts_count || 0) <= 10 && (
                      <p className="text-xs text-yellow-400 mt-2">
                        ⚠️ Currently using fallback accounts - full @Sploofmeme sync in progress...
                      </p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Performance Tab */}
          <TabsContent value="performance">
            <div className="space-y-6">
              {/* Top Posting Accounts */}
              <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle className="text-green-400 flex items-center">
                    <TrendingUp className="h-5 w-5 mr-2" />
                    Top Posting X Accounts
                  </CardTitle>
                  <CardDescription>
                    Which @Sploofmeme following accounts post trending tokens the most
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="text-center text-slate-500 py-8">
                      <Users className="h-12 w-12 mx-auto mb-2 opacity-50" />
                      <p className="text-lg font-medium">📊 Tracking Account Performance</p>
                      <p className="text-sm">Statistics will appear as accounts post trending tokens</p>
                      <div className="mt-4 grid grid-cols-3 gap-4 text-xs">
                        <div className="bg-slate-700/30 p-3 rounded">
                          <div className="text-purple-400 font-medium">Most Posts</div>
                          <div className="text-slate-400">Track volume</div>
                        </div>
                        <div className="bg-slate-700/30 p-3 rounded">
                          <div className="text-blue-400 font-medium">Best Success Rate</div>
                          <div className="text-slate-400">Tokens → CAs</div>
                        </div>
                        <div className="bg-slate-700/30 p-3 rounded">
                          <div className="text-green-400 font-medium">CA Performance</div>
                          <div className="text-slate-400">Post-CA gains</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* CA Performance Tracking */}
              <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle className="text-blue-400 flex items-center">
                    <DollarSign className="h-5 w-5 mr-2" />
                    CA Performance Tracking
                  </CardTitle>
                  <CardDescription>
                    Track token performance after getting contract addresses
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-center text-slate-500 py-8">
                    <TrendingUp className="h-12 w-12 mx-auto mb-2 opacity-50" />
                    <p className="text-lg font-medium">⚡ CA Performance Dashboard</p>
                    <p className="text-sm">Track gains/losses after CA launches</p>
                    <div className="mt-4 grid grid-cols-2 gap-4 text-xs">
                      <div className="bg-green-900/20 p-3 rounded border border-green-500/30">
                        <div className="text-green-400 font-medium">Successful CAs</div>
                        <div className="text-slate-400">Tokens with positive gains</div>
                      </div>
                      <div className="bg-red-900/20 p-3 rounded border border-red-500/30">
                        <div className="text-red-400 font-medium">Failed CAs</div>
                        <div className="text-slate-400">Tokens with losses</div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Versions Tab */}
          <TabsContent value="versions" className="space-y-6">
            {/* GitHub Integration */}
            <Card className="bg-gradient-to-r from-purple-900/30 to-blue-900/30 border-purple-500/30 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-purple-400 flex items-center">
                  <Github className="h-5 w-5 mr-2" />
                  GitHub Integration
                </CardTitle>
                <CardDescription>
                  Backup and sync your Tweet Tracker data to GitHub repository
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {/* GitHub Token Setup Instructions */}
                  <div className="p-4 bg-gradient-to-r from-blue-900/30 to-purple-900/30 rounded-lg border border-blue-500/30">
                    <h4 className="text-sm font-medium text-blue-400 mb-3">⚠️ IMPORTANT: This is NOT your GitHub password!</h4>
                    <div className="space-y-3">
                      <div className="bg-yellow-900/20 p-3 rounded border border-yellow-500/30">
                        <p className="text-xs text-yellow-400 font-medium">📋 Step-by-step token creation:</p>
                        <ol className="text-xs text-slate-300 mt-2 space-y-1 list-decimal list-inside">
                          <li>Go to <a href="https://github.com/settings/tokens" target="_blank" rel="noopener noreferrer" className="text-blue-400 underline">github.com/settings/tokens</a></li>
                          <li>Click "Generate new token" → "Generate new token (classic)"</li>
                          <li>Name: "Tweet Tracker Backup"</li>
                          <li>✅ Check "repo" (Full control of private repositories)</li>
                          <li>Click "Generate token"</li>
                          <li>Copy the token (starts with "ghp_") - you won't see it again!</li>
                        </ol>
                      </div>
                      <div className="bg-red-900/20 p-3 rounded border border-red-500/30">
                        <p className="text-xs text-red-400">🔒 Security: Never share this token. It gives access to your repositories.</p>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <Label htmlFor="github-username">GitHub Username</Label>
                      <Input
                        id="github-username"
                        placeholder="pitch6767"
                        value={githubUsername}
                        onChange={(e) => setGithubUsername(e.target.value)}
                        className="bg-slate-700 border-slate-600"
                      />
                    </div>
                    <div>
                      <Label htmlFor="github-token">GitHub Token (ghp_xxx...)</Label>
                      <Input
                        id="github-token"
                        type="password"
                        placeholder="ghp_xxxxxxxxxxxx"
                        value={githubToken}
                        onChange={(e) => setGithubToken(e.target.value)}
                        className="bg-slate-700 border-slate-600"
                      />
                    </div>
                    <div className="flex items-end space-x-2">
                      <Button onClick={setupGitHub} className="bg-purple-600 hover:bg-purple-700">
                        <Github className="h-4 w-4 mr-2" />
                        Connect
                      </Button>
                      {githubStats.repository_name && (
                        <Button onClick={createGitHubBackup} variant="outline" className="border-green-500 text-green-400">
                          Backup Now
                        </Button>
                      )}
                    </div>
                  </div>

                  {githubStats.repository_name && (
                    <div className="p-3 bg-slate-800/50 rounded-lg border border-green-500/30">
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span className="text-slate-400">✅ Connected Repository:</span>
                        <span className="text-green-400">{githubStats.repository_name}</span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-slate-400">Total Backups:</span>
                        <span className="text-blue-400">{githubBackups.length}</span>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Local Version Management */}
            <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-purple-400">Local Version Management</CardTitle>
                <CardDescription>
                  Save and restore app states with full rollback capability
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center text-slate-500 py-8">
                  <RotateCcw className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>Local version history will appear here</p>
                </div>
              </CardContent>
            </Card>

            {/* GitHub Backups List */}
            {githubBackups.length > 0 && (
              <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle className="text-green-400">GitHub Backups ({githubBackups.length})</CardTitle>
                  <CardDescription>
                    Cloud backups stored in your GitHub repository
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {githubBackups.slice(0, 5).map((backup, index) => (
                      <div key={index} className="p-3 bg-slate-700/50 rounded-lg">
                        <div className="flex items-center justify-between">
                          <div>
                            <h4 className="font-medium text-green-300">{backup.version}</h4>
                            <p className="text-xs text-slate-400">
                              {formatTime(backup.timestamp)} • {(backup.size / 1024).toFixed(1)} KB
                            </p>
                          </div>
                          <div className="flex space-x-2">
                            <Button size="sm" variant="outline" className="border-blue-500 text-blue-400">
                              Restore
                            </Button>
                            <Button size="sm" variant="outline" className="border-red-500 text-red-400">
                              Delete
                            </Button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </div>
      <Toaster />
    </div>
  );
}

export default TweetTracker;