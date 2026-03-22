import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  PoundSterling,
  Calculator,
  ShieldCheck,
  Clock,
  Moon,
  TrendingUp,
  TrendingDown,
  Landmark,
  BarChart3,
  Target,
  AlertTriangle,
  Activity,
  Zap,
  ChevronRight,
  CheckCircle2,
  XCircle,
} from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────

interface PositionSizeResult {
  stake_per_point: number;
  max_loss: number;
  margin_required: number;
  leverage_ratio: string;
  notional_exposure: number;
  error?: string;
}

interface MarginStatus {
  available: number;
  used: number;
  utilisation_pct: number;
  warning_level: string;
}

interface MarketHoursInfo {
  is_open: boolean;
  session: string;
  next_open: string | null;
  next_close: string | null;
  minutes_to_close: number;
  gap_risk: string;
  gap_reasons: string[];
  should_close_before_gap: boolean;
  close_warning_reason: string;
  optimal_windows: { window: string; start_utc: string; end_utc: string; quality: string; reason: string }[];
}

interface FundingCost {
  daily_cost: number;
  weekly_cost: number;
  total_cost: number;
  annual_rate_pct: number;
  days: number;
}

interface TaxRoute {
  venue: string;
  exchange: string;
  reason: string;
  tax_saving: number;
}

interface Strategy {
  key: string;
  name: string;
  description: string;
  best_for: string[];
  preferred_timeframe: string;
}

interface SimulationResult {
  symbol: string;
  direction: string;
  stake_per_point: number;
  margin_required: number;
  max_loss: number;
  max_profit: number;
  overnight_cost: number;
  guaranteed_stop_cost: number;
  net_profit_if_target_hit: number;
  risk_reward_ratio: number;
  hold_days: number;
  asset_class: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────

const GBP = (n: number) =>
  `£${n.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const ASSET_CLASSES = [
  { value: "forex_major", label: "Forex Major" },
  { value: "forex_minor", label: "Forex Minor" },
  { value: "indices", label: "Indices" },
  { value: "commodities", label: "Commodities" },
  { value: "metals", label: "Metals" },
  { value: "shares_uk", label: "UK Shares" },
  { value: "shares_us", label: "US Shares" },
  { value: "crypto", label: "Crypto" },
];

const STRATEGY_BADGES: Record<string, { label: string; variant: "default" | "secondary" | "outline" }> = {
  sb_momentum_scalper: { label: "Intraday", variant: "default" },
  sb_trend_rider: { label: "Swing", variant: "secondary" },
  sb_mean_reversion: { label: "Swing", variant: "secondary" },
  sb_breakout_guaranteed: { label: "Guaranteed Stop", variant: "outline" },
  sb_index_surfer: { label: "Intraday", variant: "default" },
};

const MARKET_SYMBOLS = [
  { symbol: "EUR_USD", label: "Forex (EUR/USD)", emoji: "💱" },
  { symbol: "UK100", label: "FTSE 100", emoji: "🇬🇧" },
  { symbol: "US500", label: "S&P 500", emoji: "🇺🇸" },
  { symbol: "XAUUSD", label: "Gold", emoji: "🥇" },
];

// ── Gauge Component ───────────────────────────────────────────────────────

function MarginGauge({ pct, level }: { pct: number; level: string }) {
  const clampedPct = Math.min(Math.max(pct, 0), 100);
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clampedPct / 100) * circumference;
  const color =
    level === "safe"
      ? "hsl(var(--profit))"
      : level === "caution"
        ? "hsl(45 93% 47%)"
        : "hsl(var(--loss))";

  return (
    <div className="relative w-36 h-36 mx-auto" data-testid="margin-gauge">
      <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
        <circle cx="60" cy="60" r={radius} fill="none" stroke="hsl(var(--muted))" strokeWidth="10" />
        <circle
          cx="60"
          cy="60"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-700"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold font-mono" style={{ color }}>
          {clampedPct.toFixed(0)}%
        </span>
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">{level}</span>
      </div>
    </div>
  );
}

// ── Stat Card ─────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  icon: Icon,
  color,
  testId,
}: {
  label: string;
  value: string;
  icon: React.ElementType;
  color?: string;
  testId: string;
}) {
  return (
    <div
      data-testid={testId}
      className="flex items-center gap-3 rounded-lg border border-card-border bg-muted/30 px-4 py-3"
    >
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary/10">
        <Icon size={18} className="text-primary" />
      </div>
      <div className="min-w-0">
        <p className="text-[11px] uppercase tracking-wider text-muted-foreground">{label}</p>
        <p className={`text-lg font-bold font-mono ${color ?? "text-foreground"}`}>{value}</p>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Main Page
// ═══════════════════════════════════════════════════════════════════════════

export default function SpreadBetting() {
  // ── Section 1 state: Position Calculator ────────────────────────────
  const [balance, setBalance] = useState(10000);
  const [riskPct, setRiskPct] = useState(1);
  const [stopDistance, setStopDistance] = useState(50);
  const [assetClass, setAssetClass] = useState("forex_major");
  const [direction, setDirection] = useState<"buy" | "sell">("buy");

  const [calcResult, setCalcResult] = useState<PositionSizeResult | null>(null);
  const [calcLoading, setCalcLoading] = useState(false);

  const handleCalculate = async () => {
    setCalcLoading(true);
    try {
      const params = new URLSearchParams({
        account_balance: balance.toString(),
        risk_pct: riskPct.toString(),
        stop_distance: stopDistance.toString(),
        asset_class: assetClass,
      });
      const res = await apiRequest("GET", `/api/spread-betting/position-size?${params}`);
      setCalcResult(await res.json());
    } catch {
      setCalcResult(null);
    } finally {
      setCalcLoading(false);
    }
  };

  // ── Section 2: Margin Monitor ───────────────────────────────────────
  const { data: marginStatus } = useQuery<MarginStatus>({
    queryKey: ["/api/spread-betting/margin-status"],
    queryFn: async () => {
      const r = await apiRequest("GET", "/api/spread-betting/margin-status");
      return r.json();
    },
    refetchInterval: 10000,
  });

  // ── Section 3: Market Hours ─────────────────────────────────────────
  const marketQueries = MARKET_SYMBOLS.map((m) => {
    const { data, isLoading } = useQuery<MarketHoursInfo>({
      queryKey: [`/api/spread-betting/market-hours/${m.symbol}`],
      queryFn: async () => {
        const r = await apiRequest("GET", `/api/spread-betting/market-hours/${m.symbol}`);
        return r.json();
      },
      refetchInterval: 30000,
    });
    return { ...m, data, isLoading };
  });

  // ── Section 4: Funding Calculator state ─────────────────────────────
  const [fundStake, setFundStake] = useState(2);
  const [fundPrice, setFundPrice] = useState(1.085);
  const [fundAsset, setFundAsset] = useState("forex_major");
  const [fundDir, setFundDir] = useState("buy");
  const [fundDays, setFundDays] = useState(7);
  const [fundResult, setFundResult] = useState<FundingCost | null>(null);

  const handleFunding = async () => {
    try {
      const params = new URLSearchParams({
        stake_per_point: fundStake.toString(),
        current_price: fundPrice.toString(),
        asset_class: fundAsset,
        direction: fundDir,
        days: fundDays.toString(),
      });
      const r = await apiRequest("GET", `/api/spread-betting/funding-cost?${params}`);
      setFundResult(await r.json());
    } catch {
      setFundResult(null);
    }
  };

  // ── Section 5: Tax Route ────────────────────────────────────────────
  const [taxSymbol, setTaxSymbol] = useState("EURUSD");
  const [taxDir, setTaxDir] = useState("buy");
  const [taxDays, setTaxDays] = useState(5);
  const [taxPnl, setTaxPnl] = useState(500);
  const [taxResult, setTaxResult] = useState<TaxRoute | null>(null);

  const handleTaxRoute = async () => {
    try {
      const params = new URLSearchParams({
        symbol: taxSymbol,
        direction: taxDir,
        hold_days: taxDays.toString(),
        expected_pnl: taxPnl.toString(),
      });
      const r = await apiRequest("GET", `/api/spread-betting/tax-route?${params}`);
      setTaxResult(await r.json());
    } catch {
      setTaxResult(null);
    }
  };

  // ── Section 6: Strategies ───────────────────────────────────────────
  const { data: strategies } = useQuery<Strategy[]>({
    queryKey: ["/api/spread-betting/strategies"],
    queryFn: async () => {
      const r = await apiRequest("GET", "/api/spread-betting/strategies");
      return r.json();
    },
  });

  // ── Section 7: Trade Simulator ──────────────────────────────────────
  const [simSymbol, setSimSymbol] = useState("EURUSD");
  const [simDir, setSimDir] = useState("buy");
  const [simStake, setSimStake] = useState(2);
  const [simStop, setSimStop] = useState(50);
  const [simTP, setSimTP] = useState(100);
  const [simGStop, setSimGStop] = useState(false);
  const [simDays, setSimDays] = useState(5);

  const simulate = useMutation<SimulationResult>({
    mutationFn: async () => {
      const r = await apiRequest("POST", "/api/spread-betting/simulate", {
        symbol: simSymbol,
        direction: simDir,
        stake: simStake,
        stop_distance: simStop,
        take_profit: simTP,
        guaranteed_stop: simGStop,
        hold_days: simDays,
      });
      return r.json();
    },
  });

  // ═══════════════════════════════════════════════════════════════════════
  // Render
  // ═══════════════════════════════════════════════════════════════════════

  return (
    <div data-testid="spread-betting-page" className="space-y-6 p-4 md:p-6 max-w-[1400px] mx-auto">
      {/* Page Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
          <PoundSterling size={22} className="text-primary" />
        </div>
        <div>
          <h1 className="text-xl font-semibold">Spread Betting</h1>
          <p className="text-sm text-muted-foreground">
            Tax-free UK spread betting — position sizing, margin, funding & gap protection
          </p>
        </div>
      </div>

      {/* ── Section 1: Position Calculator ───────────────────────────── */}
      <Card className="border-card-border bg-card" data-testid="section-calculator">
        <CardHeader className="pb-4">
          <CardTitle className="flex items-center gap-2 text-base">
            <Calculator size={18} className="text-primary" />
            Spread Bet Calculator
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-6 gap-4 items-end">
            {/* Balance */}
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Account Balance (£)</Label>
              <Input
                data-testid="input-balance"
                type="number"
                value={balance}
                onChange={(e) => setBalance(Number(e.target.value))}
                className="font-mono"
              />
            </div>
            {/* Risk % */}
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Risk Per Trade ({riskPct}%)</Label>
              <Slider
                data-testid="slider-risk"
                min={0.5}
                max={5}
                step={0.25}
                value={[riskPct]}
                onValueChange={([v]) => setRiskPct(v)}
              />
            </div>
            {/* Stop Distance */}
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Stop Distance (pts)</Label>
              <Input
                data-testid="input-stop-distance"
                type="number"
                value={stopDistance}
                onChange={(e) => setStopDistance(Number(e.target.value))}
                className="font-mono"
              />
            </div>
            {/* Asset Class */}
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Asset Class</Label>
              <Select value={assetClass} onValueChange={setAssetClass}>
                <SelectTrigger data-testid="select-asset-class">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ASSET_CLASSES.map((ac) => (
                    <SelectItem key={ac.value} value={ac.value}>
                      {ac.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {/* Direction */}
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Direction</Label>
              <div className="flex gap-1">
                <Button
                  data-testid="btn-direction-buy"
                  size="sm"
                  variant={direction === "buy" ? "default" : "outline"}
                  className={direction === "buy" ? "flex-1 bg-[hsl(var(--profit))] hover:bg-[hsl(var(--profit))]/90 text-white" : "flex-1"}
                  onClick={() => setDirection("buy")}
                >
                  <TrendingUp size={14} className="mr-1" /> Buy
                </Button>
                <Button
                  data-testid="btn-direction-sell"
                  size="sm"
                  variant={direction === "sell" ? "default" : "outline"}
                  className={direction === "sell" ? "flex-1 bg-[hsl(var(--loss))] hover:bg-[hsl(var(--loss))]/90 text-white" : "flex-1"}
                  onClick={() => setDirection("sell")}
                >
                  <TrendingDown size={14} className="mr-1" /> Sell
                </Button>
              </div>
            </div>
            {/* Calculate */}
            <div>
              <Button
                data-testid="btn-calculate"
                onClick={handleCalculate}
                disabled={calcLoading || stopDistance <= 0}
                className="w-full"
              >
                {calcLoading ? "Calculating…" : "Calculate"}
              </Button>
            </div>
          </div>

          {/* Results */}
          {calcResult && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mt-5">
              <StatCard
                testId="stat-stake"
                label="£/Point Stake"
                value={GBP(calcResult.stake_per_point)}
                icon={PoundSterling}
                color="text-primary"
              />
              <StatCard
                testId="stat-max-loss"
                label="Max Loss"
                value={GBP(calcResult.max_loss)}
                icon={AlertTriangle}
                color="text-[hsl(var(--loss))]"
              />
              <StatCard
                testId="stat-margin"
                label="Margin Required"
                value={GBP(calcResult.margin_required)}
                icon={Landmark}
              />
              <StatCard
                testId="stat-leverage"
                label="Leverage Ratio"
                value={calcResult.leverage_ratio}
                icon={BarChart3}
              />
              <StatCard
                testId="stat-notional"
                label="Notional Exposure"
                value={GBP(calcResult.notional_exposure)}
                icon={Activity}
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Row: Margin + Market Hours ───────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Section 2: Margin Monitor */}
        <Card className="border-card-border bg-card" data-testid="section-margin">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <ShieldCheck size={18} className="text-primary" />
              Margin Monitor
            </CardTitle>
          </CardHeader>
          <CardContent>
            {marginStatus ? (
              <>
                <MarginGauge pct={marginStatus.utilisation_pct} level={marginStatus.warning_level} />
                <div className="mt-4 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Available</span>
                    <span className="font-mono text-[hsl(var(--profit))]">{GBP(marginStatus.available)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Used</span>
                    <span className="font-mono">{GBP(marginStatus.used)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Status</span>
                    <Badge
                      data-testid="margin-warning-badge"
                      variant={marginStatus.warning_level === "safe" ? "default" : "destructive"}
                      className={
                        marginStatus.warning_level === "safe"
                          ? "bg-[hsl(var(--profit))]/15 text-[hsl(var(--profit))] border-[hsl(var(--profit))]/30"
                          : marginStatus.warning_level === "caution"
                            ? "bg-yellow-500/15 text-yellow-400 border-yellow-500/30"
                            : ""
                      }
                    >
                      {marginStatus.warning_level}
                    </Badge>
                  </div>
                </div>
              </>
            ) : (
              <div className="space-y-3">
                <Skeleton className="h-36 w-36 mx-auto rounded-full" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-2/3" />
              </div>
            )}
          </CardContent>
        </Card>

        {/* Section 3: Market Hours */}
        <Card className="lg:col-span-2 border-card-border bg-card" data-testid="section-market-hours">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Clock size={18} className="text-primary" />
              Market Hours & Gap Protection
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {marketQueries.map((mq) => (
                <div
                  key={mq.symbol}
                  data-testid={`market-${mq.symbol}`}
                  className="flex items-center gap-3 rounded-lg border border-card-border bg-muted/20 px-4 py-3"
                >
                  <span className="text-xl">{mq.emoji}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{mq.label}</p>
                    {mq.isLoading ? (
                      <Skeleton className="h-3 w-20 mt-1" />
                    ) : mq.data ? (
                      <div className="flex items-center gap-2 mt-0.5">
                        <span
                          className={`inline-block h-2 w-2 rounded-full ${mq.data.is_open ? "bg-[hsl(var(--profit))] animate-pulse" : "bg-[hsl(var(--loss))]"}`}
                        />
                        <span className="text-xs text-muted-foreground">
                          {mq.data.is_open ? "Open" : "Closed"}
                        </span>
                        {mq.data.is_open && mq.data.minutes_to_close > 0 && mq.data.minutes_to_close <= 120 && (
                          <span className="text-xs text-yellow-400">
                            ({mq.data.minutes_to_close}m to close)
                          </span>
                        )}
                      </div>
                    ) : null}
                    {mq.data && mq.data.gap_risk !== "low" && (
                      <div className="flex items-center gap-1 mt-1">
                        <AlertTriangle size={12} className="text-[hsl(var(--loss))]" />
                        <span className="text-[11px] text-[hsl(var(--loss))]">
                          Gap risk: {mq.data.gap_risk}
                        </span>
                      </div>
                    )}
                  </div>
                  {mq.data && (
                    <Badge variant="outline" className="text-[10px] shrink-0">
                      {mq.data.session}
                    </Badge>
                  )}
                </div>
              ))}
            </div>

            {/* Optimal windows for first market */}
            {marketQueries[0]?.data?.optimal_windows && (
              <div className="mt-4">
                <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wider">
                  Optimal Trading Windows (Forex)
                </p>
                <div className="flex flex-wrap gap-2">
                  {marketQueries[0].data.optimal_windows.map((w) => (
                    <div
                      key={w.window}
                      className="flex items-center gap-1.5 rounded-md border border-card-border bg-muted/20 px-2.5 py-1.5 text-xs"
                    >
                      <div
                        className={`h-1.5 w-1.5 rounded-full ${w.quality === "highest" ? "bg-[hsl(var(--profit))]" : w.quality === "high" ? "bg-primary" : "bg-muted-foreground"}`}
                      />
                      <span className="font-medium">{w.window}</span>
                      <span className="text-muted-foreground">
                        {w.start_utc}–{w.end_utc} UTC
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ── Row: Funding Calculator + Tax Router ────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Section 4: Overnight Funding */}
        <Card className="border-card-border bg-card" data-testid="section-funding">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Moon size={18} className="text-primary" />
              Overnight Funding Calculator
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Stake (£/pt)</Label>
                <Input
                  data-testid="fund-stake"
                  type="number"
                  value={fundStake}
                  onChange={(e) => setFundStake(Number(e.target.value))}
                  className="font-mono"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Current Price</Label>
                <Input
                  data-testid="fund-price"
                  type="number"
                  step="0.001"
                  value={fundPrice}
                  onChange={(e) => setFundPrice(Number(e.target.value))}
                  className="font-mono"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Asset Class</Label>
                <Select value={fundAsset} onValueChange={setFundAsset}>
                  <SelectTrigger data-testid="fund-asset">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ASSET_CLASSES.map((ac) => (
                      <SelectItem key={ac.value} value={ac.value}>{ac.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Direction</Label>
                <Select value={fundDir} onValueChange={setFundDir}>
                  <SelectTrigger data-testid="fund-direction">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="buy">Buy (Long)</SelectItem>
                    <SelectItem value="sell">Sell (Short)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Hold Days</Label>
                <Input
                  data-testid="fund-days"
                  type="number"
                  value={fundDays}
                  onChange={(e) => setFundDays(Number(e.target.value))}
                  className="font-mono"
                />
              </div>
              <div className="flex items-end">
                <Button data-testid="btn-fund-calc" onClick={handleFunding} className="w-full" size="sm">
                  Calculate
                </Button>
              </div>
            </div>

            {fundResult && (
              <div className="grid grid-cols-2 gap-3 mt-4">
                <div className="rounded-lg border border-card-border bg-muted/20 p-3 text-center">
                  <p className="text-[10px] uppercase text-muted-foreground">Daily Cost</p>
                  <p className="text-lg font-bold font-mono text-[hsl(var(--loss))]">{GBP(fundResult.daily_cost)}</p>
                </div>
                <div className="rounded-lg border border-card-border bg-muted/20 p-3 text-center">
                  <p className="text-[10px] uppercase text-muted-foreground">Weekly Cost</p>
                  <p className="text-lg font-bold font-mono text-[hsl(var(--loss))]">{GBP(fundResult.weekly_cost)}</p>
                </div>
                <div className="rounded-lg border border-card-border bg-muted/20 p-3 text-center">
                  <p className="text-[10px] uppercase text-muted-foreground">Total ({fundResult.days}d)</p>
                  <p className="text-lg font-bold font-mono">{GBP(fundResult.total_cost)}</p>
                </div>
                <div className="rounded-lg border border-card-border bg-muted/20 p-3 text-center">
                  <p className="text-[10px] uppercase text-muted-foreground">Annual Rate</p>
                  <p className="text-lg font-bold font-mono">{fundResult.annual_rate_pct}%</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Section 5: Tax Efficiency */}
        <Card className="border-card-border bg-card" data-testid="section-tax">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Landmark size={18} className="text-primary" />
              Tax Efficiency Router
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-3 mb-4">
              <div className="flex-1 rounded-lg border border-[hsl(var(--profit))]/30 bg-[hsl(var(--profit))]/5 p-3 text-center">
                <Badge className="bg-[hsl(var(--profit))]/15 text-[hsl(var(--profit))] border-[hsl(var(--profit))]/30 mb-1">
                  Tax Free
                </Badge>
                <p className="text-sm font-medium mt-1">Spread Betting</p>
                <p className="text-xs text-muted-foreground">0% CGT on profits</p>
              </div>
              <div className="flex-1 rounded-lg border border-yellow-500/30 bg-yellow-500/5 p-3 text-center">
                <Badge className="bg-yellow-500/15 text-yellow-400 border-yellow-500/30 mb-1">
                  20% CGT
                </Badge>
                <p className="text-sm font-medium mt-1">CFD Trading</p>
                <p className="text-xs text-muted-foreground">Losses offset gains</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Symbol</Label>
                <Input
                  data-testid="tax-symbol"
                  value={taxSymbol}
                  onChange={(e) => setTaxSymbol(e.target.value)}
                  className="font-mono"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Direction</Label>
                <Select value={taxDir} onValueChange={setTaxDir}>
                  <SelectTrigger data-testid="tax-direction">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="buy">Buy</SelectItem>
                    <SelectItem value="sell">Sell</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Hold Days</Label>
                <Input
                  data-testid="tax-days"
                  type="number"
                  value={taxDays}
                  onChange={(e) => setTaxDays(Number(e.target.value))}
                  className="font-mono"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Expected P&L (£)</Label>
                <Input
                  data-testid="tax-pnl"
                  type="number"
                  value={taxPnl}
                  onChange={(e) => setTaxPnl(Number(e.target.value))}
                  className="font-mono"
                />
              </div>
            </div>
            <Button data-testid="btn-tax-route" onClick={handleTaxRoute} className="w-full mt-3" size="sm">
              Check Best Route
            </Button>

            {taxResult && (
              <div className="mt-4 rounded-lg border border-card-border bg-muted/20 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <ChevronRight size={14} className="text-primary" />
                  <span className="font-medium text-sm">
                    Recommended: <span className="text-primary">{taxResult.venue === "spread_bet" ? "Spread Bet" : taxResult.venue === "cfd" ? "CFD" : "Stock"}</span>
                  </span>
                  <span className="text-xs text-muted-foreground ml-auto">via {taxResult.exchange}</span>
                </div>
                <p className="text-xs text-muted-foreground">{taxResult.reason}</p>
                {taxResult.tax_saving > 0 && (
                  <p className="text-xs font-medium text-[hsl(var(--profit))] mt-1">
                    Tax saving: {GBP(taxResult.tax_saving)}
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ── Section 6: Strategies ────────────────────────────────────── */}
      <Card className="border-card-border bg-card" data-testid="section-strategies">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Zap size={18} className="text-primary" />
            Spread Betting Strategies
          </CardTitle>
        </CardHeader>
        <CardContent>
          {strategies ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {strategies.map((s) => {
                const badge = STRATEGY_BADGES[s.key] ?? { label: "General", variant: "outline" as const };
                return (
                  <div
                    key={s.key}
                    data-testid={`strategy-${s.key}`}
                    className="rounded-lg border border-card-border bg-muted/20 p-4 hover:bg-muted/30 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <h3 className="text-sm font-semibold leading-tight">{s.name}</h3>
                      <Badge variant={badge.variant} className="shrink-0 text-[10px]">
                        {badge.label}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mb-3 line-clamp-3">{s.description}</p>
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant="outline" className="text-[10px]">
                        {s.preferred_timeframe}
                      </Badge>
                      {s.best_for.map((bf) => (
                        <span key={bf} className="text-[10px] text-muted-foreground">
                          {bf}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-32 rounded-lg" />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Section 7: Trade Simulator ───────────────────────────────── */}
      <Card className="border-card-border bg-card" data-testid="section-simulator">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Target size={18} className="text-primary" />
            Trade Simulator
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3 items-end">
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Symbol</Label>
              <Input
                data-testid="sim-symbol"
                value={simSymbol}
                onChange={(e) => setSimSymbol(e.target.value)}
                className="font-mono"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Direction</Label>
              <Select value={simDir} onValueChange={setSimDir}>
                <SelectTrigger data-testid="sim-direction">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="buy">Buy</SelectItem>
                  <SelectItem value="sell">Sell</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Stake (£/pt)</Label>
              <Input
                data-testid="sim-stake"
                type="number"
                value={simStake}
                onChange={(e) => setSimStake(Number(e.target.value))}
                className="font-mono"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Stop (pts)</Label>
              <Input
                data-testid="sim-stop"
                type="number"
                value={simStop}
                onChange={(e) => setSimStop(Number(e.target.value))}
                className="font-mono"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Take Profit (pts)</Label>
              <Input
                data-testid="sim-tp"
                type="number"
                value={simTP}
                onChange={(e) => setSimTP(Number(e.target.value))}
                className="font-mono"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Hold Days</Label>
              <Input
                data-testid="sim-days"
                type="number"
                value={simDays}
                onChange={(e) => setSimDays(Number(e.target.value))}
                className="font-mono"
              />
            </div>
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Checkbox
                  data-testid="sim-gstop"
                  checked={simGStop}
                  onCheckedChange={(v) => setSimGStop(v === true)}
                />
                <Label className="text-xs text-muted-foreground">Guaranteed Stop</Label>
              </div>
              <Button
                data-testid="btn-simulate"
                onClick={() => simulate.mutate()}
                disabled={simulate.isPending}
                className="w-full"
                size="sm"
              >
                {simulate.isPending ? "Simulating…" : "Simulate"}
              </Button>
            </div>
          </div>

          {simulate.data && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mt-5">
              <div className="rounded-lg border border-card-border bg-muted/20 p-3 text-center">
                <p className="text-[10px] uppercase text-muted-foreground">Margin</p>
                <p className="text-base font-bold font-mono">{GBP(simulate.data.margin_required)}</p>
              </div>
              <div className="rounded-lg border border-card-border bg-muted/20 p-3 text-center">
                <p className="text-[10px] uppercase text-muted-foreground">Max Loss</p>
                <p className="text-base font-bold font-mono text-[hsl(var(--loss))]">
                  {GBP(simulate.data.max_loss)}
                </p>
              </div>
              <div className="rounded-lg border border-card-border bg-muted/20 p-3 text-center">
                <p className="text-[10px] uppercase text-muted-foreground">Max Profit</p>
                <p className="text-base font-bold font-mono text-[hsl(var(--profit))]">
                  {GBP(simulate.data.max_profit)}
                </p>
              </div>
              <div className="rounded-lg border border-card-border bg-muted/20 p-3 text-center">
                <p className="text-[10px] uppercase text-muted-foreground">Overnight Cost</p>
                <p className="text-base font-bold font-mono">{GBP(simulate.data.overnight_cost)}</p>
              </div>
              <div className="rounded-lg border border-card-border bg-muted/20 p-3 text-center">
                <p className="text-[10px] uppercase text-muted-foreground">Net Profit</p>
                <p
                  className={`text-base font-bold font-mono ${simulate.data.net_profit_if_target_hit >= 0 ? "text-[hsl(var(--profit))]" : "text-[hsl(var(--loss))]"}`}
                >
                  {GBP(simulate.data.net_profit_if_target_hit)}
                </p>
              </div>
              <div className="rounded-lg border border-card-border bg-muted/20 p-3 text-center">
                <p className="text-[10px] uppercase text-muted-foreground">Risk:Reward</p>
                <p className="text-base font-bold font-mono">
                  1:{simulate.data.risk_reward_ratio.toFixed(1)}
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
