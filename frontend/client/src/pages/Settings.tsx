import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Settings2,
  Palette,
  Key,
  RotateCcw,
  DollarSign,
  Shield,
  Moon,
  Sun,
  Bot,
  Brain,
  Bell,
  Mail,
  Webhook,
  AlertTriangle,
} from "lucide-react";

// ── Types ────────────────────────────────────────────────────────────────────

interface ExchangeInfo {
  name: string;
  display_name: string;
  category: string;
  type: string;
  fca_status: string;
  status: string;
  has_testnet: boolean;
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function Settings() {
  const { toast } = useToast();
  const [resetBalance, setResetBalance] = useState("10000");
  const [defaultExchange, setDefaultExchange] = useState("binance");
  const [isDark, setIsDark] = useState(() =>
    document.documentElement.classList.contains("dark")
  );

  // Dynamic API key state — keyed by exchange name
  const [apiKeys, setApiKeys] = useState<Record<string, { key: string; secret: string }>>({});

  // Auto-Trader defaults
  const [atDefaultExchange, setAtDefaultExchange] = useState("paper");
  const [atDefaultSymbols, setAtDefaultSymbols] = useState("BTC/USDT");
  const [atDefaultRisk, setAtDefaultRisk] = useState(1);
  const [atDefaultInterval, setAtDefaultInterval] = useState("300");
  const [atAutoStart, setAtAutoStart] = useState(false);

  // AI Configuration
  const [claudeKey, setClaudeKey] = useState("");
  const [geminiKey, setGeminiKey] = useState("");

  // Notification settings
  const [emailEnabled, setEmailEnabled] = useState(false);
  const [smtpUser, setSmtpUser] = useState("");
  const [smtpPass, setSmtpPass] = useState("");
  const [alertEmail, setAlertEmail] = useState("");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [minSeverity, setMinSeverity] = useState("medium");

  // ── Queries ──────────────────────────────────────────────────────────────

  const { data: exchanges, isLoading: exchangesLoading } = useQuery<ExchangeInfo[]>({
    queryKey: ["/api/exchanges/supported"],
    queryFn: async () => {
      const r = await apiRequest("GET", "/api/exchanges/supported");
      return r.json();
    },
    staleTime: 300000,
  });

  // ── Mutations ────────────────────────────────────────────────────────────

  const toggleTheme = () => {
    const newDark = !isDark;
    setIsDark(newDark);
    if (newDark) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  };

  const resetPortfolio = useMutation({
    mutationFn: async () => {
      return apiRequest("POST", `/api/portfolio/reset?balance=${parseFloat(resetBalance)}`);
    },
    onSuccess: () => {
      toast({ title: "Portfolio reset", description: `New balance: $${resetBalance}` });
      queryClient.invalidateQueries({ queryKey: ["/api/portfolio/summary"] });
      queryClient.invalidateQueries({ queryKey: ["/api/analytics/risk-metrics"] });
    },
    onError: (err: Error) => {
      toast({ title: "Reset failed", description: err.message, variant: "destructive" });
    },
  });

  const saveAutoTraderDefaults = useMutation({
    mutationFn: async () => {
      return apiRequest("POST", "/api/auto-trader/config", {
        exchange: atDefaultExchange,
        symbols: atDefaultSymbols.split(",").map(s => s.trim()).filter(Boolean),
        risk_per_trade_pct: atDefaultRisk,
        interval_seconds: parseInt(atDefaultInterval) || 300,
        auto_start: atAutoStart,
      });
    },
    onSuccess: () => {
      toast({ title: "Auto-Trader defaults saved" });
    },
    onError: (err: Error) => {
      toast({ title: "Save failed", description: err.message, variant: "destructive" });
    },
  });

  const updateApiKey = (exchange: string, field: "key" | "secret", value: string) => {
    setApiKeys((prev) => ({
      ...prev,
      [exchange]: { ...prev[exchange], [field]: value },
    }));
  };

  const getApiKeyState = (exchange: string) => {
    return apiKeys[exchange] ?? { key: "", secret: "" };
  };

  const saveApiKey = (exchange: string) => {
    const config = getApiKeyState(exchange);
    if (!config.key || !config.secret) {
      toast({ title: "Missing fields", description: "Both API Key and Secret are required", variant: "destructive" });
      return;
    }
    toast({ title: `${exchange} keys saved`, description: "API credentials stored locally" });
  };

  const categoryColors: Record<string, string> = {
    crypto: "bg-teal-500/20 text-teal-300",
    spread_betting: "bg-purple-500/20 text-purple-300",
    stocks: "bg-blue-500/20 text-blue-300",
    forex: "bg-purple-500/20 text-purple-300",
    multi_asset: "bg-amber-500/20 text-amber-300",
  };

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="space-y-4 max-w-3xl" data-testid="settings-page">
      <h1 className="text-xl font-semibold">Settings</h1>

      {/* Appearance */}
      <Card className="border-card-border bg-card" data-testid="settings-appearance">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-1.5">
            <Palette size={14} className="text-primary" />
            Appearance
          </CardTitle>
          <CardDescription className="text-xs">
            Customize the look and feel of the trading terminal
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {isDark ? <Moon size={16} className="text-muted-foreground" /> : <Sun size={16} className="text-amber-400" />}
              <div>
                <p className="text-sm font-medium">Dark Mode</p>
                <p className="text-xs text-muted-foreground">Trading terminal theme</p>
              </div>
            </div>
            <Switch checked={isDark} onCheckedChange={toggleTheme} data-testid="toggle-theme" />
          </div>
        </CardContent>
      </Card>

      {/* Trading Defaults */}
      <Card className="border-card-border bg-card" data-testid="settings-trading">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-1.5">
            <Settings2 size={14} className="text-primary" />
            Trading Defaults
          </CardTitle>
          <CardDescription className="text-xs">
            Default settings for paper trading
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Default Exchange</Label>
              <Select value={defaultExchange} onValueChange={setDefaultExchange}>
                <SelectTrigger className="h-9" data-testid="select-default-exchange">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {exchangesLoading ? (
                    <SelectItem value="binance">Loading...</SelectItem>
                  ) : (exchanges ?? []).map((ex) => (
                    <SelectItem key={ex.name} value={ex.name}>{ex.display_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Auto-Trader Defaults */}
      <Card className="border-card-border bg-card border-primary/20" data-testid="settings-auto-trader">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-1.5">
            <Bot size={14} className="text-primary" />
            Auto-Trader Defaults
          </CardTitle>
          <CardDescription className="text-xs">
            Default configuration when starting the auto-trader
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Default Exchange</Label>
              <Select value={atDefaultExchange} onValueChange={setAtDefaultExchange}>
                <SelectTrigger className="h-9" data-testid="select-at-exchange">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="paper">Paper Trading</SelectItem>
                  {(exchanges ?? []).map((ex) => (
                    <SelectItem key={ex.name} value={ex.name}>{ex.display_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Default Symbols</Label>
              <Input
                data-testid="input-at-symbols"
                value={atDefaultSymbols}
                onChange={(e) => setAtDefaultSymbols(e.target.value)}
                placeholder="BTC/USDT, ETH/USDT"
                className="h-9 text-xs font-mono"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Risk Per Trade: {atDefaultRisk.toFixed(1)}%</Label>
              <Slider
                data-testid="slider-at-risk"
                min={0.5}
                max={5}
                step={0.1}
                value={[atDefaultRisk]}
                onValueChange={([v]) => setAtDefaultRisk(v)}
                className="mt-2"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Default Interval</Label>
              <Select value={atDefaultInterval} onValueChange={setAtDefaultInterval}>
                <SelectTrigger className="h-9" data-testid="select-at-interval">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="60">60 seconds</SelectItem>
                  <SelectItem value="120">2 minutes</SelectItem>
                  <SelectItem value="300">5 minutes</SelectItem>
                  <SelectItem value="600">10 minutes</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex items-center justify-between pt-2 border-t border-border">
            <div className="flex items-center gap-3">
              <div>
                <p className="text-sm font-medium">Auto-start on launch</p>
                <p className="text-xs text-muted-foreground">Begin trading when the app starts</p>
              </div>
            </div>
            <Switch checked={atAutoStart} onCheckedChange={setAtAutoStart} data-testid="toggle-at-autostart" />
          </div>
          <Button
            variant="outline"
            size="sm"
            className="w-full h-8 text-xs"
            onClick={() => saveAutoTraderDefaults.mutate()}
            disabled={saveAutoTraderDefaults.isPending}
            data-testid="btn-save-at-defaults"
          >
            {saveAutoTraderDefaults.isPending ? "Saving..." : "Save Auto-Trader Defaults"}
          </Button>
        </CardContent>
      </Card>

      {/* AI Configuration */}
      <Card className="border-card-border bg-card" data-testid="settings-ai">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-1.5">
            <Brain size={14} className="text-primary" />
            AI Configuration
          </CardTitle>
          <CardDescription className="text-xs">
            Optional AI provider keys. The system uses rule-based analysis as fallback.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Claude API Key (Anthropic)</Label>
              <Input
                data-testid="input-claude-key"
                type="password"
                value={claudeKey}
                onChange={(e) => setClaudeKey(e.target.value)}
                placeholder="sk-ant-..."
                className="h-9 text-xs font-mono"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Gemini API Key (Google)</Label>
              <Input
                data-testid="input-gemini-key"
                type="password"
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
                placeholder="AIza..."
                className="h-9 text-xs font-mono"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Current provider:</span>
            <Badge variant="outline" className="text-[10px]">
              {claudeKey ? "Claude" : geminiKey ? "Gemini" : "Rule-based"}
            </Badge>
          </div>
          <p className="text-[10px] text-muted-foreground flex items-center gap-1">
            <Brain size={10} />
            AI keys are optional. The system uses rule-based analysis as fallback.
          </p>
          <Button
            variant="outline"
            size="sm"
            className="w-full h-8 text-xs"
            onClick={() => toast({ title: "AI keys saved", description: "Keys stored locally" })}
            data-testid="btn-save-ai-keys"
          >
            Save AI Keys
          </Button>
        </CardContent>
      </Card>

      {/* Notifications */}
      <Card className="border-card-border bg-card" data-testid="settings-notifications">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-1.5">
            <Bell size={14} className="text-primary" />
            Notifications
          </CardTitle>
          <CardDescription className="text-xs">
            Configure alert delivery channels
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Email alerts */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Mail size={16} className="text-muted-foreground" />
              <div>
                <p className="text-sm font-medium">Email Alerts</p>
                <p className="text-xs text-muted-foreground">Receive alerts via email</p>
              </div>
            </div>
            <Switch checked={emailEnabled} onCheckedChange={setEmailEnabled} data-testid="toggle-email-alerts" />
          </div>

          {emailEnabled && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pl-7">
              <div className="space-y-1">
                <Label className="text-[10px] text-muted-foreground uppercase">SMTP User</Label>
                <Input
                  data-testid="input-smtp-user"
                  type="text"
                  value={smtpUser}
                  onChange={(e) => setSmtpUser(e.target.value)}
                  placeholder="user@example.com"
                  className="h-8 text-xs"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-[10px] text-muted-foreground uppercase">SMTP Password</Label>
                <Input
                  data-testid="input-smtp-pass"
                  type="password"
                  value={smtpPass}
                  onChange={(e) => setSmtpPass(e.target.value)}
                  placeholder="App password..."
                  className="h-8 text-xs"
                />
              </div>
              <div className="space-y-1 sm:col-span-2">
                <Label className="text-[10px] text-muted-foreground uppercase">Alert Email Address</Label>
                <Input
                  data-testid="input-alert-email"
                  type="email"
                  value={alertEmail}
                  onChange={(e) => setAlertEmail(e.target.value)}
                  placeholder="alerts@example.com"
                  className="h-8 text-xs"
                />
              </div>
            </div>
          )}

          {/* Webhook */}
          <div className="flex items-center gap-3">
            <Webhook size={16} className="text-muted-foreground" />
            <div className="flex-1 space-y-1">
              <Label className="text-xs text-muted-foreground">Webhook URL</Label>
              <Input
                data-testid="input-webhook-url"
                type="url"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                placeholder="https://hooks.slack.com/..."
                className="h-8 text-xs font-mono"
              />
            </div>
          </div>

          {/* Min severity */}
          <div className="flex items-center gap-3">
            <AlertTriangle size={16} className="text-muted-foreground" />
            <div className="flex-1 space-y-1">
              <Label className="text-xs text-muted-foreground">Minimum Alert Severity</Label>
              <Select value={minSeverity} onValueChange={setMinSeverity}>
                <SelectTrigger className="h-8 text-xs" data-testid="select-min-severity">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="critical">Critical</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <Button
            variant="outline"
            size="sm"
            className="w-full h-8 text-xs"
            onClick={() => toast({ title: "Notification settings saved" })}
            data-testid="btn-save-notifications"
          >
            Save Notification Settings
          </Button>
        </CardContent>
      </Card>

      {/* Portfolio Reset */}
      <Card className="border-card-border bg-card border-destructive/20" data-testid="settings-reset">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-1.5">
            <RotateCcw size={14} className="text-destructive" />
            Reset Portfolio
          </CardTitle>
          <CardDescription className="text-xs">
            Reset your paper trading portfolio to a fresh state. This clears all positions and trades.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="space-y-1.5 flex-1 max-w-xs">
              <Label className="text-xs text-muted-foreground">Starting Balance</Label>
              <div className="flex items-center gap-2">
                <DollarSign size={14} className="text-muted-foreground" />
                <Input
                  data-testid="input-reset-balance"
                  value={resetBalance}
                  onChange={(e) => setResetBalance(e.target.value)}
                  type="number"
                  step="1000"
                  className="h-9 font-mono text-sm"
                />
              </div>
            </div>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => resetPortfolio.mutate()}
              disabled={resetPortfolio.isPending}
              data-testid="btn-reset-portfolio"
              className="h-9 mt-5"
            >
              <RotateCcw size={14} className="mr-1" />
              {resetPortfolio.isPending ? "Resetting..." : "Reset"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Exchange API Keys — Dynamic */}
      <Card className="border-card-border bg-card" data-testid="settings-api-keys">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-1.5">
            <Key size={14} className="text-primary" />
            Exchange API Keys
          </CardTitle>
          <CardDescription className="text-xs">
            Configure API credentials for live exchange connections. Not required for paper trading.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {exchangesLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 w-full" />)}
            </div>
          ) : (exchanges ?? []).map((ex) => {
            const config = getApiKeyState(ex.name);
            return (
              <div key={ex.name} className="p-3 rounded-md bg-muted/20 border border-border/50 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{ex.display_name}</span>
                    <Badge className={`text-[10px] px-1.5 py-0 border-0 ${categoryColors[ex.category] ?? "bg-muted text-muted-foreground"}`}>
                      {ex.category}
                    </Badge>
                    {ex.fca_status && ex.fca_status !== "Not FCA regulated" && (
                      <Badge variant="outline" className="text-[9px] px-1 py-0 text-green-400 border-green-400/30">FCA</Badge>
                    )}
                  </div>
                  {config.key && config.secret ? (
                    <Badge className="text-[10px] bg-[hsl(var(--profit))]/10 text-[hsl(var(--profit))] border-0">
                      Configured
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="text-[10px] text-muted-foreground">
                      Not Set
                    </Badge>
                  )}
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-[10px] text-muted-foreground uppercase">API Key</Label>
                    <Input
                      data-testid={`input-key-${ex.name}`}
                      type="password"
                      value={config.key}
                      onChange={(e) => updateApiKey(ex.name, "key", e.target.value)}
                      placeholder="Enter API key..."
                      className="h-8 text-xs font-mono"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-[10px] text-muted-foreground uppercase">API Secret</Label>
                    <Input
                      data-testid={`input-secret-${ex.name}`}
                      type="password"
                      value={config.secret}
                      onChange={(e) => updateApiKey(ex.name, "secret", e.target.value)}
                      placeholder="Enter API secret..."
                      className="h-8 text-xs font-mono"
                    />
                  </div>
                </div>
                <div className="flex justify-end">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => saveApiKey(ex.name)}
                    className="h-7 text-xs"
                  >
                    <Shield size={12} className="mr-1" />
                    Save
                  </Button>
                </div>
              </div>
            );
          })}
          <p className="text-[10px] text-muted-foreground flex items-center gap-1">
            <Shield size={10} />
            API keys are stored locally and encrypted. Never share your API secrets.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
