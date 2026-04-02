import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import {
  ShieldCheck,
  Search,
  TrendingUp,
  TrendingDown,
  Activity,
  BarChart3,
  History,
  Server,
  Info,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

// ── Types ────────────────────────────────────────────────────────────────────

interface TrustEvaluation {
  trust_score: number;
  grade: string;
  recommendation: string;
  size_modifier: number;
  components: Record<string, number>;
  weights_used: Record<string, number>;
  asset_class: string;
  symbol: string;
  exchange: string;
  direction: string;
  reasoning: string;
  timestamp: string;
}

interface VenueScore {
  score: number;
  fill_rate: number;
  avg_slippage: number;
  avg_latency: number;
  success_rate: number;
  total_trades: number;
  grade: string;
}

interface Analytics {
  history_stats: {
    total_evaluations: number;
    avg_trust_score: number;
    grade_distribution: Record<string, number>;
    executed_pct: number;
  };
  outcome_correlation: Record<
    string,
    { count: number; avg_pnl_pct: number; win_rate: number }
  >;
  venue_scores: Record<string, VenueScore>;
  recent_evaluations: HistoryEntry[];
}

interface HistoryEntry {
  symbol: string;
  asset_class: string;
  trust_score: number;
  grade: string;
  recommendation: string;
  components: Record<string, number>;
  trade_executed: boolean;
  pnl_pct: number | null;
  timestamp: string;
}

interface WeightsResponse {
  asset_class: string;
  weights: Record<string, number>;
  total: number;
}

// ── Constants ────────────────────────────────────────────────────────────────

const GRADE_COLORS: Record<string, { ring: string; text: string; bg: string }> =
  {
    A: {
      ring: "hsl(142 71% 45%)",
      text: "text-green-400",
      bg: "bg-green-500/20",
    },
    B: {
      ring: "hsl(168 80% 42%)",
      text: "text-teal-400",
      bg: "bg-teal-500/20",
    },
    C: {
      ring: "hsl(45 93% 47%)",
      text: "text-amber-400",
      bg: "bg-amber-500/20",
    },
    D: {
      ring: "hsl(25 95% 53%)",
      text: "text-orange-400",
      bg: "bg-orange-500/20",
    },
    F: {
      ring: "hsl(0 84% 60%)",
      text: "text-red-400",
      bg: "bg-red-500/20",
    },
  };

const RECOMMENDATION_STYLES: Record<
  string,
  { label: string; cls: string }
> = {
  execute: { label: "Execute", cls: "bg-green-500/20 text-green-300 border-green-500/30" },
  reduce_size: { label: "Reduce Size", cls: "bg-amber-500/20 text-amber-300 border-amber-500/30" },
  wait: { label: "Wait", cls: "bg-orange-500/20 text-orange-300 border-orange-500/30" },
  reject: { label: "Reject", cls: "bg-red-500/20 text-red-300 border-red-500/30" },
};

const COMPONENT_LABELS: Record<string, string> = {
  signal_strength: "Signal Strength",
  timeframe_agreement: "Timeframe Agreement",
  regime_confidence: "Regime Confidence",
  sentiment_alignment: "Sentiment Alignment",
  strategy_track_record: "Strategy Track Record",
  spread_quality: "Spread Quality",
  data_freshness: "Data Freshness",
  venue_quality: "Venue Quality",
  news_safety: "News Safety",
  risk_headroom: "Risk Headroom",
};

const EXCHANGES = [
  "binance",
  "coinbase",
  "kraken",
  "bybit",
  "alpaca",
  "oanda",
  "ig",
  "capital",
  "cmc",
  "ibkr",
];

const ASSET_CLASS_TABS = [
  { value: "crypto", label: "Crypto" },
  { value: "forex", label: "Forex" },
  { value: "stocks", label: "Stocks" },
  { value: "indices", label: "Indices" },
  { value: "commodities", label: "Commodities" },
  { value: "spread_betting", label: "Spread Betting" },
];

// ── Trust Gauge SVG ──────────────────────────────────────────────────────────

function TrustGauge({
  score,
  grade,
}: {
  score: number;
  grade: string;
}) {
  const pct = Math.min(Math.max(score * 100, 0), 100);
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (pct / 100) * circumference;
  const color = GRADE_COLORS[grade]?.ring ?? "hsl(var(--muted))";

  return (
    <div
      className="relative w-40 h-40 mx-auto"
      data-testid="trust-gauge"
    >
      <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
        <circle
          cx="60"
          cy="60"
          r={radius}
          fill="none"
          stroke="hsl(var(--muted))"
          strokeWidth="10"
        />
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
        <span
          className="text-3xl font-bold font-mono"
          style={{ color }}
          data-testid="trust-grade"
        >
          {grade}
        </span>
        <span
          className="text-sm font-mono"
          style={{ color }}
          data-testid="trust-score-value"
        >
          {pct.toFixed(0)}%
        </span>
      </div>
    </div>
  );
}

// ── Small Venue Gauge ────────────────────────────────────────────────────────

function VenueGauge({ score, grade }: { score: number; grade: string }) {
  const pct = Math.min(Math.max(score * 100, 0), 100);
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (pct / 100) * circumference;
  const color = GRADE_COLORS[grade]?.ring ?? "hsl(var(--muted))";

  return (
    <div className="relative w-20 h-20 mx-auto">
      <svg viewBox="0 0 64 64" className="w-full h-full -rotate-90">
        <circle cx="32" cy="32" r={radius} fill="none" stroke="hsl(var(--muted))" strokeWidth="6" />
        <circle
          cx="32"
          cy="32"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-500"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-sm font-bold font-mono" style={{ color }}>
          {grade}
        </span>
        <span className="text-[10px] font-mono text-muted-foreground">
          {pct.toFixed(0)}%
        </span>
      </div>
    </div>
  );
}

// ── Component Score Bar ──────────────────────────────────────────────────────

function ComponentBar({
  name,
  value,
  weight,
}: {
  name: string;
  value: number;
  weight: number;
}) {
  const pct = Math.min(Math.max(value * 100, 0), 100);
  const barColor =
    value >= 0.7
      ? "bg-green-500"
      : value >= 0.5
        ? "bg-amber-500"
        : "bg-red-500";

  return (
    <div className="flex items-center gap-3" data-testid={`component-${name}`}>
      <div className="w-40 shrink-0 text-xs text-muted-foreground truncate">
        {COMPONENT_LABELS[name] ?? name}
      </div>
      <div className="flex-1 h-3 bg-muted/30 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-12 text-right text-xs font-mono text-foreground">
        {pct.toFixed(0)}%
      </span>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="w-10 text-right text-[10px] font-mono text-muted-foreground cursor-help">
            w:{(weight * 100).toFixed(0)}%
          </span>
        </TooltipTrigger>
        <TooltipContent side="right">
          Weight: {(weight * 100).toFixed(0)}% of total score
        </TooltipContent>
      </Tooltip>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function TrustScore() {
  const [symbol, setSymbol] = useState("BTC/USDT");
  const [direction, setDirection] = useState<"buy" | "sell">("buy");
  const [exchange, setExchange] = useState("binance");
  const [evalResult, setEvalResult] = useState<TrustEvaluation | null>(null);
  const [evaluating, setEvaluating] = useState(false);

  // ── Queries ──────────────────────────────────────────────────────────────

  const { data: analytics } = useQuery<Analytics>({
    queryKey: ["/api/trust-score/analytics"],
    queryFn: async () => {
      const r = await apiRequest("GET", "/api/trust-score/analytics");
      return r.json();
    },
    refetchInterval: 30000,
  });

  const { data: venues } = useQuery<Record<string, VenueScore>>({
    queryKey: ["/api/trust-score/venues"],
    queryFn: async () => {
      const r = await apiRequest("GET", "/api/trust-score/venues");
      return r.json();
    },
    refetchInterval: 30000,
  });

  const { data: history } = useQuery<HistoryEntry[]>({
    queryKey: ["/api/trust-score/history", 20],
    queryFn: async () => {
      const r = await apiRequest("GET", "/api/trust-score/history?limit=20");
      return r.json();
    },
    refetchInterval: 30000,
  });

  const [weightTab, setWeightTab] = useState("crypto");
  const { data: weights } = useQuery<WeightsResponse>({
    queryKey: ["/api/trust-score/weights", weightTab],
    queryFn: async () => {
      const r = await apiRequest(
        "GET",
        `/api/trust-score/weights/${weightTab}`
      );
      return r.json();
    },
  });

  // ── Evaluate ─────────────────────────────────────────────────────────────

  async function handleEvaluate() {
    setEvaluating(true);
    try {
      const params = new URLSearchParams({
        symbol,
        direction,
        exchange,
      });
      const r = await apiRequest(
        "GET",
        `/api/trust-score/evaluate?${params}`
      );
      const data = await r.json();
      setEvalResult(data);
    } catch {
      setEvalResult(null);
    } finally {
      setEvaluating(false);
    }
  }

  // ── Derived ──────────────────────────────────────────────────────────────

  const sortedComponents = evalResult
    ? Object.entries(evalResult.components)
        .map(([key, val]) => ({
          key,
          value: val,
          weight: evalResult.weights_used[key] ?? 0,
        }))
        .sort((a, b) => b.weight - a.weight)
    : [];

  const gradeDistEntries = analytics?.history_stats?.grade_distribution
    ? Object.entries(analytics.history_stats.grade_distribution)
    : [];
  const maxGradeCount = Math.max(
    1,
    ...gradeDistEntries.map(([, v]) => v)
  );

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div
      data-testid="trust-score-page"
      className="space-y-6 p-4 md:p-6 max-w-[1400px] mx-auto"
    >
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-primary/10">
          <ShieldCheck size={24} className="text-primary" />
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tight">
            Execution Trust Score
          </h1>
          <p className="text-sm text-muted-foreground">
            Unified confidence scoring across 10 signal dimensions
          </p>
        </div>
      </div>

      {/* ═══ Live Evaluator ═══ */}
      <Card
        className="border-card-border bg-card"
        data-testid="section-evaluator"
      >
        <CardHeader className="pb-4">
          <CardTitle className="flex items-center gap-2 text-base">
            <Search size={18} className="text-primary" />
            Live Trust Evaluator
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-end">
            {/* Symbol */}
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">
                Symbol
              </label>
              <Input
                data-testid="input-symbol"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                placeholder="BTC/USDT"
                className="font-mono"
              />
            </div>

            {/* Direction */}
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">
                Direction
              </label>
              <div className="flex gap-1">
                <Button
                  data-testid="btn-direction-buy"
                  size="sm"
                  variant={direction === "buy" ? "default" : "outline"}
                  className={
                    direction === "buy"
                      ? "flex-1 bg-[hsl(var(--profit))] hover:bg-[hsl(var(--profit))]/90 text-white"
                      : "flex-1"
                  }
                  onClick={() => setDirection("buy")}
                >
                  <TrendingUp size={14} className="mr-1" /> Buy
                </Button>
                <Button
                  data-testid="btn-direction-sell"
                  size="sm"
                  variant={direction === "sell" ? "default" : "outline"}
                  className={
                    direction === "sell"
                      ? "flex-1 bg-[hsl(var(--loss))] hover:bg-[hsl(var(--loss))]/90 text-white"
                      : "flex-1"
                  }
                  onClick={() => setDirection("sell")}
                >
                  <TrendingDown size={14} className="mr-1" /> Sell
                </Button>
              </div>
            </div>

            {/* Exchange */}
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">
                Exchange
              </label>
              <Select value={exchange} onValueChange={setExchange}>
                <SelectTrigger data-testid="select-exchange">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {EXCHANGES.map((ex) => (
                    <SelectItem key={ex} value={ex}>
                      {ex.charAt(0).toUpperCase() + ex.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Evaluate button */}
            <div className="md:col-span-2">
              <Button
                data-testid="btn-evaluate"
                onClick={handleEvaluate}
                disabled={evaluating || !symbol}
                className="w-full"
              >
                <ShieldCheck size={16} className="mr-2" />
                {evaluating ? "Evaluating..." : "Evaluate Trust"}
              </Button>
            </div>
          </div>

          {/* ── Result ── */}
          {evalResult && (
            <div
              className="mt-6 grid grid-cols-1 lg:grid-cols-[240px_1fr] gap-6"
              data-testid="eval-result"
            >
              {/* Gauge + summary */}
              <div className="flex flex-col items-center gap-3">
                <TrustGauge
                  score={evalResult.trust_score}
                  grade={evalResult.grade}
                />
                <Badge
                  data-testid="recommendation-badge"
                  className={`text-xs px-3 py-1 border ${
                    RECOMMENDATION_STYLES[evalResult.recommendation]?.cls ??
                    ""
                  }`}
                >
                  {RECOMMENDATION_STYLES[evalResult.recommendation]?.label ??
                    evalResult.recommendation}
                </Badge>
                <div className="text-center space-y-1">
                  <div className="text-xs text-muted-foreground">
                    Position size
                  </div>
                  <div
                    className="text-lg font-bold font-mono"
                    data-testid="size-modifier"
                  >
                    {(evalResult.size_modifier * 100).toFixed(0)}%
                  </div>
                </div>
                <div className="text-xs text-muted-foreground text-center mt-1 max-w-[220px]">
                  {evalResult.reasoning}
                </div>
              </div>

              {/* Component breakdown */}
              <div className="space-y-2">
                <div className="flex items-center gap-2 mb-3">
                  <BarChart3
                    size={14}
                    className="text-muted-foreground"
                  />
                  <span className="text-sm font-medium">
                    Component Breakdown
                  </span>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Info
                        size={12}
                        className="text-muted-foreground cursor-help"
                      />
                    </TooltipTrigger>
                    <TooltipContent>
                      Sorted by weight (highest impact first)
                    </TooltipContent>
                  </Tooltip>
                </div>
                {sortedComponents.map((c) => (
                  <ComponentBar
                    key={c.key}
                    name={c.key}
                    value={c.value}
                    weight={c.weight}
                  />
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ═══ Weight Profiles ═══ */}
      <Card
        className="border-card-border bg-card"
        data-testid="section-weights"
      >
        <CardHeader className="pb-4">
          <CardTitle className="flex items-center gap-2 text-base">
            <Activity size={18} className="text-primary" />
            Weight Profiles by Asset Class
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs
            value={weightTab}
            onValueChange={setWeightTab}
            data-testid="weight-tabs"
          >
            <TabsList className="mb-4 flex-wrap h-auto gap-1">
              {ASSET_CLASS_TABS.map((t) => (
                <TabsTrigger
                  key={t.value}
                  value={t.value}
                  data-testid={`weight-tab-${t.value}`}
                  className="text-xs"
                >
                  {t.label}
                </TabsTrigger>
              ))}
            </TabsList>

            {ASSET_CLASS_TABS.map((t) => (
              <TabsContent key={t.value} value={t.value}>
                {weights && weights.asset_class === t.value ? (
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                    {Object.entries(weights.weights)
                      .sort(([, a], [, b]) => b - a)
                      .map(([key, val]) => (
                        <div
                          key={key}
                          className="rounded-lg border border-border bg-muted/20 p-3 text-center"
                          data-testid={`weight-${t.value}-${key}`}
                        >
                          <div className="text-lg font-bold font-mono text-primary">
                            {(val * 100).toFixed(0)}%
                          </div>
                          <div className="text-[10px] text-muted-foreground mt-1 leading-tight">
                            {COMPONENT_LABELS[key] ?? key}
                          </div>
                        </div>
                      ))}
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground py-4 text-center">
                    Loading weights...
                  </div>
                )}
              </TabsContent>
            ))}
          </Tabs>
        </CardContent>
      </Card>

      {/* ═══ Two-column: Venues + Analytics ═══ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Venue Quality */}
        <Card
          className="border-card-border bg-card"
          data-testid="section-venues"
        >
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-base">
              <Server size={18} className="text-primary" />
              Venue Quality
            </CardTitle>
          </CardHeader>
          <CardContent>
            {venues && Object.keys(venues).length > 0 ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {Object.entries(venues).map(([name, v]) => (
                  <div
                    key={name}
                    className={`rounded-lg border p-3 ${
                      GRADE_COLORS[v.grade]?.bg ?? "bg-muted/20"
                    } border-border`}
                    data-testid={`venue-${name}`}
                  >
                    <VenueGauge score={v.score} grade={v.grade} />
                    <div className="text-center mt-2">
                      <div className="text-sm font-medium capitalize">
                        {name}
                      </div>
                      <div className="text-[10px] text-muted-foreground space-y-0.5 mt-1">
                        <div>
                          Fill: {(v.fill_rate * 100).toFixed(1)}%
                        </div>
                        <div>
                          Slip: {(v.avg_slippage * 100).toFixed(2)}%
                        </div>
                        <div>{v.total_trades} trades</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-muted-foreground text-center py-8">
                No venue data yet. Execute trades to start tracking quality.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Analytics */}
        <Card
          className="border-card-border bg-card"
          data-testid="section-analytics"
        >
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-base">
              <BarChart3 size={18} className="text-primary" />
              Trust Score Analytics
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Stats row */}
            {analytics?.history_stats && (
              <div className="grid grid-cols-3 gap-3">
                <div className="rounded-lg bg-muted/20 p-3 text-center">
                  <div className="text-lg font-bold font-mono text-primary">
                    {analytics.history_stats.total_evaluations}
                  </div>
                  <div className="text-[10px] text-muted-foreground">
                    Evaluations
                  </div>
                </div>
                <div className="rounded-lg bg-muted/20 p-3 text-center">
                  <div className="text-lg font-bold font-mono text-primary">
                    {(analytics.history_stats.avg_trust_score * 100).toFixed(
                      0
                    )}
                    %
                  </div>
                  <div className="text-[10px] text-muted-foreground">
                    Avg Score
                  </div>
                </div>
                <div className="rounded-lg bg-muted/20 p-3 text-center">
                  <div className="text-lg font-bold font-mono text-primary">
                    {analytics.history_stats.executed_pct.toFixed(0)}%
                  </div>
                  <div className="text-[10px] text-muted-foreground">
                    Executed
                  </div>
                </div>
              </div>
            )}

            {/* Grade distribution */}
            {gradeDistEntries.length > 0 && (
              <div>
                <div className="text-xs text-muted-foreground mb-2">
                  Grade Distribution
                </div>
                <div className="flex items-end gap-2 h-20">
                  {["A", "B", "C", "D", "F"].map((g) => {
                    const count =
                      analytics?.history_stats?.grade_distribution?.[g] ??
                      0;
                    const heightPct = (count / maxGradeCount) * 100;
                    const gc = GRADE_COLORS[g];
                    return (
                      <div
                        key={g}
                        className="flex-1 flex flex-col items-center gap-1"
                        data-testid={`grade-bar-${g}`}
                      >
                        <span className="text-[10px] font-mono text-muted-foreground">
                          {count}
                        </span>
                        <div
                          className="w-full rounded-t transition-all duration-500"
                          style={{
                            height: `${Math.max(heightPct, 4)}%`,
                            backgroundColor: gc?.ring,
                            opacity: count > 0 ? 1 : 0.2,
                          }}
                        />
                        <span
                          className={`text-xs font-bold ${gc?.text ?? ""}`}
                        >
                          {g}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Outcome correlation */}
            {analytics?.outcome_correlation &&
              Object.keys(analytics.outcome_correlation).length > 0 && (
                <div>
                  <div className="text-xs text-muted-foreground mb-2">
                    Outcome Correlation
                  </div>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="text-xs">Grade</TableHead>
                        <TableHead className="text-xs text-right">
                          Count
                        </TableHead>
                        <TableHead className="text-xs text-right">
                          Avg P&L
                        </TableHead>
                        <TableHead className="text-xs text-right">
                          Win Rate
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {["A", "B", "C", "D", "F"].map((g) => {
                        const oc =
                          analytics?.outcome_correlation?.[g];
                        if (!oc) return null;
                        return (
                          <TableRow key={g}>
                            <TableCell>
                              <span
                                className={`font-bold ${GRADE_COLORS[g]?.text ?? ""}`}
                              >
                                {g}
                              </span>
                            </TableCell>
                            <TableCell className="text-right font-mono text-xs">
                              {oc.count}
                            </TableCell>
                            <TableCell
                              className={`text-right font-mono text-xs ${
                                oc.avg_pnl_pct > 0
                                  ? "text-[hsl(var(--profit))]"
                                  : oc.avg_pnl_pct < 0
                                    ? "text-[hsl(var(--loss))]"
                                    : ""
                              }`}
                            >
                              {oc.avg_pnl_pct > 0 ? "+" : ""}
                              {oc.avg_pnl_pct.toFixed(2)}%
                            </TableCell>
                            <TableCell className="text-right font-mono text-xs">
                              {(oc.win_rate * 100).toFixed(0)}%
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              )}
          </CardContent>
        </Card>
      </div>

      {/* ═══ Recent History ═══ */}
      <Card
        className="border-card-border bg-card"
        data-testid="section-history"
      >
        <CardHeader className="pb-4">
          <CardTitle className="flex items-center gap-2 text-base">
            <History size={18} className="text-primary" />
            Recent Evaluations
          </CardTitle>
        </CardHeader>
        <CardContent>
          {history && history.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">Time</TableHead>
                    <TableHead className="text-xs">Symbol</TableHead>
                    <TableHead className="text-xs">Asset</TableHead>
                    <TableHead className="text-xs text-center">
                      Score
                    </TableHead>
                    <TableHead className="text-xs text-center">
                      Grade
                    </TableHead>
                    <TableHead className="text-xs">Recommendation</TableHead>
                    <TableHead className="text-xs text-center">
                      Traded
                    </TableHead>
                    <TableHead className="text-xs text-right">
                      P&L
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {history.map((h, i) => {
                    const gc = GRADE_COLORS[h.grade];
                    const recStyle =
                      RECOMMENDATION_STYLES[h.recommendation];
                    return (
                      <TableRow key={i} data-testid={`history-row-${i}`}>
                        <TableCell className="text-xs font-mono text-muted-foreground whitespace-nowrap">
                          {new Date(h.timestamp).toLocaleTimeString()}
                        </TableCell>
                        <TableCell className="text-xs font-mono font-medium">
                          {h.symbol}
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {h.asset_class}
                        </TableCell>
                        <TableCell className="text-center">
                          <span className="text-xs font-mono font-medium">
                            {(h.trust_score * 100).toFixed(0)}%
                          </span>
                        </TableCell>
                        <TableCell className="text-center">
                          <span
                            className={`text-xs font-bold ${gc?.text ?? ""}`}
                          >
                            {h.grade}
                          </span>
                        </TableCell>
                        <TableCell>
                          <Badge
                            className={`text-[10px] border ${recStyle?.cls ?? ""}`}
                          >
                            {recStyle?.label ?? h.recommendation}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-center text-xs">
                          {h.trade_executed ? (
                            <span className="text-green-400">Yes</span>
                          ) : (
                            <span className="text-muted-foreground">
                              No
                            </span>
                          )}
                        </TableCell>
                        <TableCell
                          className={`text-right text-xs font-mono ${
                            h.pnl_pct !== null && h.pnl_pct > 0
                              ? "text-[hsl(var(--profit))]"
                              : h.pnl_pct !== null && h.pnl_pct < 0
                                ? "text-[hsl(var(--loss))]"
                                : "text-muted-foreground"
                          }`}
                        >
                          {h.pnl_pct !== null
                            ? `${h.pnl_pct > 0 ? "+" : ""}${h.pnl_pct.toFixed(2)}%`
                            : "—"}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="text-sm text-muted-foreground text-center py-8">
              No evaluations yet. Use the evaluator above to generate trust
              scores.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
