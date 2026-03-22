import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Play, Square, Zap, Shield, Activity, Brain, AlertTriangle,
  CheckCircle2, XCircle, Clock, BarChart3, Target, RefreshCw,
  ShieldOff, Loader2, TrendingUp, TrendingDown, DollarSign,
  Ban, Timer, Database, Gauge, Eye, Sparkles, Settings2,
} from "lucide-react";

interface ExchangeInfo {
  name: string;
  display_name: string;
  category: string;
  status: string;
}

interface ClassifyResult {
  asset_class: string;
}

interface Decision { type: string; timestamp: string; [key: string]: any; }
interface AdaptiveData {
  exit_levels: { stop_loss_pct: number; take_profit_pct: number; trailing_stop_pct: number; source: string };
  ai_accuracy: { accuracy: number; trust_level: string; evaluated: number };
  ai_weight_modifier: number;
  time_profile: Record<string, { trades: number; win_rate: number }>;
}
interface IntelData {
  modules_active: number;
  memory: { total_memories: number; with_outcomes: number };
  scoreboard: { strategies_tracked: number; total_outcomes: number; scores: Record<string, any> };
}
interface FeeData { total_fees_paid: number; total_slippage_cost: number; trades_count: number; }

const fmt = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });

const DECISION_STYLES: Record<string, { color: string; icon: any; label?: string }> = {
  trade_executed:     { color: "bg-[hsl(var(--profit))]/10 text-[hsl(var(--profit))]", icon: CheckCircle2 },
  trade_failed:       { color: "bg-[hsl(var(--loss))]/10 text-[hsl(var(--loss))]", icon: XCircle },
  auto_exit:          { color: "bg-amber-500/10 text-amber-400", icon: TrendingDown, label: "auto exit" },
  risk_block:         { color: "bg-amber-500/10 text-amber-400", icon: Shield },
  intelligence_block: { color: "bg-[hsl(var(--chart-2))]/10 text-[hsl(var(--chart-2))]", icon: Brain, label: "intel block" },
  not_worth_trading:  { color: "bg-amber-500/10 text-amber-400", icon: Ban, label: "not worth it" },
  duplicate_blocked:  { color: "bg-muted text-muted-foreground", icon: Ban, label: "duplicate" },
  streak_cooldown:    { color: "bg-[hsl(var(--loss))]/10 text-[hsl(var(--loss))]", icon: Timer, label: "cooldown" },
  extreme_sentiment:  { color: "bg-amber-500/10 text-amber-400", icon: AlertTriangle, label: "extreme F&G" },
  stale_data:         { color: "bg-muted text-muted-foreground", icon: Clock, label: "stale data" },
  time_block:         { color: "bg-muted text-muted-foreground", icon: Timer, label: "bad hour" },
  size_too_small:     { color: "bg-muted text-muted-foreground", icon: Ban, label: "too small" },
  no_signal:          { color: "bg-muted/50 text-muted-foreground", icon: Clock },
  cycle_complete:     { color: "bg-primary/10 text-primary", icon: RefreshCw },
  auto_improvement:   { color: "bg-[hsl(var(--chart-2))]/10 text-[hsl(var(--chart-2))]", icon: Sparkles, label: "self-improve" },
  system:             { color: "bg-[hsl(var(--chart-2))]/10 text-[hsl(var(--chart-2))]", icon: Zap },
  kill_switch:        { color: "bg-[hsl(var(--loss))]/10 text-[hsl(var(--loss))]", icon: ShieldOff },
  config_update:      { color: "bg-muted text-muted-foreground", icon: Activity },
  skip_sell:          { color: "bg-muted text-muted-foreground", icon: Clock },
  error:              { color: "bg-[hsl(var(--loss))]/10 text-[hsl(var(--loss))]", icon: AlertTriangle },
  cycle_error:        { color: "bg-[hsl(var(--loss))]/10 text-[hsl(var(--loss))]", icon: XCircle },
  continuous_improvement: { color: "bg-[hsl(var(--chart-2))]/10 text-[hsl(var(--chart-2))]", icon: Sparkles },
  news_halt:              { color: "bg-[hsl(var(--loss))]/10 text-[hsl(var(--loss))]", icon: Ban, label: "news halt" },
  news_caution:           { color: "bg-amber-500/10 text-amber-400", icon: AlertTriangle, label: "news caution" },
  loss_analysis:          { color: "bg-[hsl(var(--chart-2))]/10 text-[hsl(var(--chart-2))]", icon: Brain, label: "loss analysis" },
  ai_strategy_selection:  { color: "bg-primary/10 text-primary", icon: Brain, label: "AI pick" },
};

function DecisionBadge({ type }: { type: string }) {
  const cfg = DECISION_STYLES[type] || { color: "bg-muted text-muted-foreground", icon: Clock };
  const Icon = cfg.icon;
  const label = cfg.label || type.replaceAll("_", " ");
  return (
    <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${cfg.color} border-0 whitespace-nowrap`}>
      <Icon size={10} className="mr-0.5" />{label}
    </Badge>
  );
}

function DecisionText({ d }: { d: Decision }) {
  const t = d.type;
  if (t === "trade_executed") {
    return <p className="text-sm">
      <span className={d.side === "buy" ? "text-[hsl(var(--profit))] font-semibold" : "text-[hsl(var(--loss))] font-semibold"}>
        {d.direction?.toUpperCase() || d.side?.toUpperCase()}
      </span>{" "}{d.quantity} {d.symbol} @ {fmt.format(d.price || 0)}
      <span className="text-muted-foreground"> · {d.strategy}</span>
      {d.instrument && d.instrument !== "spot" && <Badge variant="outline" className="text-[9px] ml-1 px-1 py-0">{d.instrument} {d.leverage}x</Badge>}
      {d.estimated_fee > 0 && <span className="text-[10px] text-muted-foreground ml-1">fee: {fmt.format(d.estimated_fee)}</span>}
    </p>;
  }
  if (t === "auto_exit") return <p className="text-sm"><span className={d.pnl >= 0 ? "text-[hsl(var(--profit))]" : "text-[hsl(var(--loss))]"}>{d.symbol} {d.pnl >= 0 ? "+" : ""}{fmt.format(d.pnl)} ({d.pnl_pct}%)</span> — {d.reason}</p>;
  if (t === "intelligence_block") return <p className="text-xs text-[hsl(var(--chart-2))]">{d.strategy} · {(d.reasons || [])[0]?.slice(0, 80)}</p>;
  if (t === "not_worth_trading") return <p className="text-xs text-amber-400">{d.strategy} · {(d.reasoning || [])[0]?.slice(0, 80)}</p>;
  if (t === "duplicate_blocked") return <p className="text-xs text-muted-foreground">{d.reason}</p>;
  if (t === "streak_cooldown") return <p className="text-xs text-[hsl(var(--loss))]">{d.reason} ({d.consecutive_losses} losses)</p>;
  if (t === "extreme_sentiment") return <p className="text-xs text-amber-400">F&G={d.fear_greed} · {d.action}</p>;
  if (t === "stale_data") return <p className="text-xs text-muted-foreground">{d.symbol} data is {d.age_minutes}min old</p>;
  if (t === "time_block") return <p className="text-xs text-muted-foreground">{d.reason}</p>;
  if (t === "size_too_small") return <p className="text-xs text-muted-foreground">${d.value_usd} below ${d.min_usd} min</p>;
  if (t === "no_signal") return <p className="text-xs text-muted-foreground">{(d.strategies_tried || [d.strategy]).join(" → ")} · no signal ({d.regime})</p>;
  if (t === "auto_improvement") return <p className="text-xs text-[hsl(var(--chart-2))]">{d.backtests} backtests · {d.changes} changes · Top: {d.top}</p>;
  if (t === "cycle_complete") return <p className="text-xs text-muted-foreground">Cycle #{d.cycle} · {d.duration_ms}ms</p>;
  if (t === "system") return <p className="text-xs text-[hsl(var(--chart-2))]">Auto-trader {d.action}</p>;
  if (t === "kill_switch") return <p className="text-xs text-[hsl(var(--loss))]">Kill switch {d.action}</p>;
  if (t === "error" || t === "cycle_error") return <p className="text-xs text-[hsl(var(--loss))]">{d.message || d.error}</p>;
  if (t === "risk_block") return <p className="text-xs text-amber-400">{(d.warnings || []).join(" · ")}</p>;
  if (t === "news_halt") return <p className="text-xs text-[hsl(var(--loss))]">Trading halted: {d.headline} — {d.reasoning}</p>;
  if (t === "news_caution") return <p className="text-xs text-amber-400">{d.headline} · {d.action}</p>;
  if (t === "loss_analysis") return <p className="text-xs text-[hsl(var(--chart-2))]">Pattern: {d.pattern} · Cause: {d.root_cause} ({d.provider})</p>;
  if (t === "ai_strategy_selection") return <p className="text-xs text-primary">{(d.strategies || []).map((s: any) => `${s.name} (${(s.weight*100).toFixed(0)}%)`).join(" → ")}</p>;
  return <p className="text-xs text-muted-foreground">{JSON.stringify(d).slice(0, 100)}</p>;
}

export default function AutoTrader() {
  const { toast } = useToast();
  const [intervalInput, setIntervalInput] = useState("300");
  const [maxDrawdown, setMaxDrawdown] = useState("10");
  const [maxPositionPct, setMaxPositionPct] = useState("20");
  const [maxExposure, setMaxExposure] = useState("60");
  const [selectedExchange, setSelectedExchange] = useState("paper");
  const [symbolsInput, setSymbolsInput] = useState("BTC/USDT");
  const [tradingMode, setTradingMode] = useState<"paper" | "live">("paper");

  const { data: status, isLoading } = useQuery<any>({
    queryKey: ["/api/auto-trader/status"],
    queryFn: async () => { const r = await apiRequest("GET", "/api/auto-trader/status"); return r.json(); },
    refetchInterval: 3000,
  });
  const { data: decisions } = useQuery<Decision[]>({
    queryKey: ["/api/auto-trader/decisions"],
    queryFn: async () => { const r = await apiRequest("GET", "/api/auto-trader/decisions?limit=40"); return r.json(); },
    refetchInterval: 5000,
  });
  const { data: intel } = useQuery<IntelData>({
    queryKey: ["/api/auto-trader/intelligence"],
    queryFn: async () => { const r = await apiRequest("GET", "/api/auto-trader/intelligence"); return r.json(); },
    refetchInterval: 10000,
  });
  const { data: adaptiveData } = useQuery<AdaptiveData>({
    queryKey: ["/api/auto-trader/adaptive"],
    queryFn: async () => { const r = await apiRequest("GET", "/api/auto-trader/adaptive"); return r.json(); },
    refetchInterval: 10000,
  });
  const { data: fees } = useQuery<FeeData>({
    queryKey: ["/api/auto-trader/fees"],
    queryFn: async () => { const r = await apiRequest("GET", "/api/auto-trader/fees"); return r.json(); },
    refetchInterval: 10000,
  });

  // Exchanges list
  const { data: exchanges } = useQuery<ExchangeInfo[]>({
    queryKey: ["/api/exchanges/supported"],
    queryFn: async () => { const r = await apiRequest("GET", "/api/exchanges/supported"); return r.json(); },
    staleTime: 300000,
  });

  // Asset class detection for entered symbols
  const firstSymbol = symbolsInput.split(",")[0]?.trim();
  const { data: classifyData } = useQuery<ClassifyResult>({
    queryKey: ["/api/asset-trading/classify", firstSymbol],
    queryFn: async () => {
      const r = await apiRequest("GET", `/api/asset-trading/classify?symbol=${encodeURIComponent(firstSymbol!)}`);
      return r.json();
    },
    enabled: !!firstSymbol && firstSymbol.length > 0,
  });

  // Mode toggle mutation
  const toggleMode = useMutation({
    mutationFn: (mode: "paper" | "live") => apiRequest("POST", "/api/live-trading/mode", { mode }),
    onSuccess: (_, mode) => { setTradingMode(mode); toast({ title: `Switched to ${mode} mode` }); },
    onError: () => { toast({ title: "Mode switch failed", variant: "destructive" }); },
  });

  const startTrader = useMutation({ mutationFn: () => apiRequest("POST", "/api/auto-trader/start"), onSuccess: () => { toast({ title: "Started" }); queryClient.invalidateQueries({ queryKey: ["/api/auto-trader/status"] }); } });
  const stopTrader = useMutation({ mutationFn: () => apiRequest("POST", "/api/auto-trader/stop"), onSuccess: () => { toast({ title: "Stopped" }); queryClient.invalidateQueries({ queryKey: ["/api/auto-trader/status"] }); } });
  const runOnce = useMutation({ mutationFn: async () => { const r = await apiRequest("POST", "/api/auto-trader/run-once"); return r.json(); }, onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["/api/auto-trader/status"] }); queryClient.invalidateQueries({ queryKey: ["/api/auto-trader/decisions"] }); } });
  const killSwitch = useMutation({ mutationFn: (activate: boolean) => apiRequest("POST", `/api/auto-trader/kill-switch?activate=${activate}`), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["/api/auto-trader/status"] }) });
  const updateConfig = useMutation({ mutationFn: () => apiRequest("POST", "/api/auto-trader/config", { interval_seconds: parseInt(intervalInput) || 300, max_drawdown_pct: parseFloat(maxDrawdown) || 10, max_position_pct: parseFloat(maxPositionPct) || 20, max_total_exposure_pct: parseFloat(maxExposure) || 60, exchange: selectedExchange, symbols: symbolsInput.split(",").map(s => s.trim()).filter(Boolean) }), onSuccess: () => { toast({ title: "Config updated" }); queryClient.invalidateQueries({ queryKey: ["/api/auto-trader/status"] }); } });

  const isRunning = status?.running ?? false;
  const isKilled = status?.risk_manager_killed ?? false;
  const strategies = status?.active_strategies ?? [];
  const lastAnalysis = status?.last_analysis ?? {};
  const decisionList = decisions ?? [];

  return (
    <div className="space-y-4" data-testid="auto-trader-page">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold">Auto-Trader</h1>
          {isRunning ? (
            <Badge className="bg-[hsl(var(--profit))]/10 text-[hsl(var(--profit))] border-0 animate-pulse"><Activity size={12} className="mr-1" /> LIVE</Badge>
          ) : (
            <Badge variant="outline" className="text-muted-foreground text-xs">STOPPED</Badge>
          )}
          {isKilled && <Badge className="bg-[hsl(var(--loss))]/10 text-[hsl(var(--loss))] border-0"><ShieldOff size={12} className="mr-1" /> KILL SWITCH</Badge>}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="h-8 text-xs" onClick={() => runOnce.mutate()} disabled={isRunning || runOnce.isPending} data-testid="btn-run-once">
            {runOnce.isPending ? <Loader2 size={14} className="mr-1 animate-spin" /> : <RefreshCw size={14} className="mr-1" />} Run Once
          </Button>
          {!isRunning ? (
            <Button size="sm" className="h-8 text-xs bg-[hsl(var(--profit))] hover:bg-[hsl(var(--profit))]/90 text-black" onClick={() => startTrader.mutate()} disabled={startTrader.isPending || isKilled} data-testid="btn-start">
              <Play size={14} className="mr-1" /> Start
            </Button>
          ) : (
            <Button size="sm" variant="destructive" className="h-8 text-xs" onClick={() => stopTrader.mutate()} data-testid="btn-stop">
              <Square size={14} className="mr-1" /> Stop
            </Button>
          )}
          <Button size="sm" variant={isKilled ? "outline" : "destructive"} className="h-8 text-xs" onClick={() => killSwitch.mutate(!isKilled)} data-testid="btn-kill-switch">
            <ShieldOff size={14} className="mr-1" /> {isKilled ? "Unlock" : "Kill Switch"}
          </Button>
        </div>
      </div>

      {/* Trading Configuration */}
      <Card className="border-card-border bg-card border-primary/20" data-testid="trading-config">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
              <Settings2 size={14} className="text-primary" /> Trading Configuration
            </CardTitle>
            <div className="flex items-center gap-2">
              <Badge className={tradingMode === "live" ? "bg-[hsl(var(--loss))]/10 text-[hsl(var(--loss))] border-0" : "bg-primary/10 text-primary border-0"}>
                {tradingMode === "live" ? "LIVE" : "PAPER"}
              </Badge>
              <Button
                variant="outline"
                size="sm"
                className="h-7 text-xs"
                data-testid="btn-toggle-mode"
                onClick={() => toggleMode.mutate(tradingMode === "paper" ? "live" : "paper")}
                disabled={toggleMode.isPending}
              >
                Switch to {tradingMode === "paper" ? "Live" : "Paper"}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Exchange Selector */}
            <div className="space-y-1.5">
              <Label className="text-[10px] text-muted-foreground uppercase">Exchange</Label>
              <Select value={selectedExchange} onValueChange={setSelectedExchange}>
                <SelectTrigger data-testid="select-exchange" className="h-8 text-xs">
                  <SelectValue placeholder="Select exchange" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="paper">Paper Trading</SelectItem>
                  {(exchanges ?? []).map((ex) => (
                    <SelectItem key={ex.name} value={ex.name}>{ex.display_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Symbols Input */}
            <div className="space-y-1.5">
              <Label className="text-[10px] text-muted-foreground uppercase">Symbols (comma-separated)</Label>
              <Input
                data-testid="input-symbols"
                value={symbolsInput}
                onChange={(e) => setSymbolsInput(e.target.value)}
                placeholder="BTC/USDT, ETH/USDT"
                className="h-8 text-xs font-mono"
              />
            </div>

            {/* Asset Class Badges */}
            <div className="space-y-1.5">
              <Label className="text-[10px] text-muted-foreground uppercase">Detected Asset Class</Label>
              <div className="flex items-center gap-2 h-8">
                {classifyData ? (
                  <Badge variant="outline" className="text-xs">{classifyData.asset_class}</Badge>
                ) : firstSymbol ? (
                  <span className="text-xs text-muted-foreground">Detecting...</span>
                ) : (
                  <span className="text-xs text-muted-foreground">Enter a symbol</span>
                )}
                {symbolsInput.split(",").length > 1 && (
                  <Badge variant="outline" className="text-[10px]">{symbolsInput.split(",").filter(s => s.trim()).length} symbols</Badge>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Row 1: AI Status + Active Strategies + Risk Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="border-card-border bg-card">
          <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5"><Brain size={14} className="text-primary" /> AI Status</CardTitle></CardHeader>
          <CardContent className="p-4 pt-0 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div><p className="text-[10px] text-muted-foreground uppercase">Cycles</p><p className="text-lg font-mono font-semibold">{status?.cycle_count ?? 0}</p></div>
              <div><p className="text-[10px] text-muted-foreground uppercase">Interval</p><p className="text-lg font-mono font-semibold">{Math.floor((status?.config?.interval_seconds ?? 300) / 60)}m</p></div>
              <div><p className="text-[10px] text-muted-foreground uppercase">Sentiment</p><p className={`text-sm font-semibold capitalize ${lastAnalysis.sentiment_assessment === "bullish" ? "text-[hsl(var(--profit))]" : lastAnalysis.sentiment_assessment === "bearish" ? "text-[hsl(var(--loss))]" : "text-muted-foreground"}`}>{lastAnalysis.sentiment_assessment || "—"}</p></div>
              <div><p className="text-[10px] text-muted-foreground uppercase">Action</p><p className="text-sm font-semibold capitalize">{lastAnalysis.recommended_action || "—"}</p></div>
            </div>
            {lastAnalysis.market_brief && <p className="text-xs text-muted-foreground leading-relaxed border-t border-border pt-2">{lastAnalysis.market_brief}</p>}
          </CardContent>
        </Card>

        <Card className="border-card-border bg-card">
          <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5"><Target size={14} /> Active Strategies</CardTitle></CardHeader>
          <CardContent className="p-4 pt-0">
            {strategies.length > 0 ? (
              <div className="space-y-1.5">
                {strategies.map((s: any, i: number) => (
                  <div key={i} className="flex items-center justify-between p-2 rounded-md bg-muted/20 border border-border/50">
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${i === 0 ? "bg-primary" : "bg-muted-foreground/30"}`} />
                      <span className={`text-sm ${i === 0 ? "font-semibold" : "text-muted-foreground"}`}>{s.name}</span>
                      {i === 0 && <Badge className="text-[9px] px-1 py-0 bg-primary/10 text-primary border-0">TOP</Badge>}
                    </div>
                    <span className="text-xs font-mono text-muted-foreground">{(s.weight * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            ) : <p className="text-sm text-muted-foreground py-6 text-center">Run a cycle to see strategies</p>}
          </CardContent>
        </Card>

        <Card className="border-card-border bg-card">
          <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5"><Shield size={14} className="text-amber-400" /> Risk Controls</CardTitle></CardHeader>
          <CardContent className="p-4 pt-0 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1"><Label className="text-[10px] text-muted-foreground uppercase">Max Drawdown %</Label><Input value={maxDrawdown} onChange={(e) => setMaxDrawdown(e.target.value)} type="number" className="h-8 text-xs font-mono" /></div>
              <div className="space-y-1"><Label className="text-[10px] text-muted-foreground uppercase">Max Position %</Label><Input value={maxPositionPct} onChange={(e) => setMaxPositionPct(e.target.value)} type="number" className="h-8 text-xs font-mono" /></div>
              <div className="space-y-1"><Label className="text-[10px] text-muted-foreground uppercase">Max Exposure %</Label><Input value={maxExposure} onChange={(e) => setMaxExposure(e.target.value)} type="number" className="h-8 text-xs font-mono" /></div>
              <div className="space-y-1"><Label className="text-[10px] text-muted-foreground uppercase">Interval (sec)</Label><Input value={intervalInput} onChange={(e) => setIntervalInput(e.target.value)} type="number" className="h-8 text-xs font-mono" /></div>
            </div>
            <Button variant="outline" size="sm" className="w-full h-8 text-xs" onClick={() => updateConfig.mutate()}>Apply Config</Button>
          </CardContent>
        </Card>
      </div>

      {/* Row 2: Intelligence + Adaptive + Fees */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="border-card-border bg-card">
          <CardHeader className="pb-2"><CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1.5"><Database size={13} /> Intelligence</CardTitle></CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div><p className="text-[10px] text-muted-foreground uppercase">Modules</p><p className="font-mono font-medium">{intel?.modules_active ?? 5} active</p></div>
              <div><p className="text-[10px] text-muted-foreground uppercase">Memory</p><p className="font-mono font-medium">{intel?.memory?.total_memories ?? 0}</p></div>
              <div><p className="text-[10px] text-muted-foreground uppercase">Scoreboard</p><p className="font-mono font-medium">{intel?.scoreboard?.total_outcomes ?? 0} outcomes</p></div>
              <div><p className="text-[10px] text-muted-foreground uppercase">Strategies</p><p className="font-mono font-medium">{intel?.scoreboard?.strategies_tracked ?? 0} tracked</p></div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-card-border bg-card">
          <CardHeader className="pb-2"><CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1.5"><Gauge size={13} /> Adaptive</CardTitle></CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div><p className="text-[10px] text-muted-foreground uppercase">Stop-Loss</p><p className="font-mono font-medium">{adaptiveData?.exit_levels?.stop_loss_pct ?? 5}%</p></div>
              <div><p className="text-[10px] text-muted-foreground uppercase">Take-Profit</p><p className="font-mono font-medium">{adaptiveData?.exit_levels?.take_profit_pct ?? 10}%</p></div>
              <div><p className="text-[10px] text-muted-foreground uppercase">AI Accuracy</p><p className={`font-mono font-medium ${(adaptiveData?.ai_accuracy?.accuracy ?? 0.5) >= 0.6 ? "text-[hsl(var(--profit))]" : "text-muted-foreground"}`}>{((adaptiveData?.ai_accuracy?.accuracy ?? 0.5) * 100).toFixed(0)}%</p></div>
              <div><p className="text-[10px] text-muted-foreground uppercase">AI Trust</p><p className="font-mono font-medium capitalize">{adaptiveData?.ai_accuracy?.trust_level ?? "unknown"}</p></div>
            </div>
            <div className="mt-2 text-[10px] text-muted-foreground">
              Exits: {adaptiveData?.exit_levels?.source ?? "default"} · AI mod: {adaptiveData?.ai_weight_modifier ?? 1}x
            </div>
          </CardContent>
        </Card>

        <Card className="border-card-border bg-card">
          <CardHeader className="pb-2"><CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1.5"><DollarSign size={13} /> Fee Tracking</CardTitle></CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div><p className="text-[10px] text-muted-foreground uppercase">Fees Paid</p><p className="font-mono font-medium text-[hsl(var(--loss))]">{fmt.format(fees?.total_fees_paid ?? 0)}</p></div>
              <div><p className="text-[10px] text-muted-foreground uppercase">Slippage</p><p className="font-mono font-medium text-[hsl(var(--loss))]">{fmt.format(fees?.total_slippage_cost ?? 0)}</p></div>
              <div><p className="text-[10px] text-muted-foreground uppercase">Trades</p><p className="font-mono font-medium">{fees?.trades_count ?? 0}</p></div>
              <div><p className="text-[10px] text-muted-foreground uppercase">Avg Fee</p><p className="font-mono font-medium">{fees && fees.trades_count > 0 ? fmt.format(fees.total_fees_paid / fees.trades_count) : "$0.00"}</p></div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Decision Log */}
      <Card className="border-card-border bg-card" data-testid="decision-log">
        <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5"><Eye size={14} /> Decision Log ({decisionList.length})</CardTitle></CardHeader>
        <CardContent className="p-4 pt-0">
          {decisionList.length === 0 ? (
            <p className="text-sm text-muted-foreground py-6 text-center">No decisions yet. Run a cycle or start the auto-trader.</p>
          ) : (
            <div className="space-y-0.5 max-h-[400px] overflow-y-auto">
              {decisionList.map((d, i) => (
                <div key={i} className="flex items-start gap-3 py-1.5 px-2 rounded-md hover:bg-muted/20 transition-colors border-b border-border/20 last:border-0">
                  <DecisionBadge type={d.type} />
                  <div className="flex-1 min-w-0"><DecisionText d={d} /></div>
                  <span className="text-[10px] text-muted-foreground shrink-0 font-mono">
                    {d.timestamp ? new Date(d.timestamp).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : ""}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
