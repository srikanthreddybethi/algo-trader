import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AreaChart,
  Area,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import {
  Brain,
  Newspaper,
  TrendingUp,
  TrendingDown,
  Activity,
  Gauge,
  BarChart3,
  Zap,
  AlertTriangle,
  ExternalLink,
  Flame,
  ThermometerSun,
  Minus,
  Sparkles,
  Search,
  Globe,
  DollarSign,
  Wheat,
} from "lucide-react";

// ── Types ────────────────────────────────────────────────────────────────────

interface FearGreed {
  value: number;
  label: string;
  timestamp: string;
  history: { value: number; label: string; timestamp: string }[];
}

interface SocialSentiment {
  symbol: string;
  sentiment_score: number;
  bullish_pct: number;
  bearish_pct: number;
  mentions_24h: number;
  volume_change_pct: number;
  trending_keywords: string[];
}

interface Regime {
  regime: string;
  confidence: number;
  description: string;
  recommended_strategies: string[];
  metrics: Record<string, any>;
}

interface NewsItem {
  title: string;
  source: string;
  url: string;
  published: string;
  summary: string;
}

interface AiAnalysis {
  market_brief: string;
  sentiment_assessment: string;
  confidence: number;
  key_factors: string[];
  risk_level: string;
  recommended_action: string;
  recommended_strategies: string[];
  price_outlook: string;
  warnings: string[];
  provider: string;
}

interface TrendingCoin {
  name: string;
  symbol: string;
  market_cap_rank: number | null;
  score: number;
}

interface DashboardData {
  fear_greed: FearGreed;
  social_sentiment: SocialSentiment;
  market_data: { trending: TrendingCoin[]; global_data: Record<string, any> };
  news: NewsItem[];
  regime: Regime;
  ai_analysis: AiAnalysis;
  symbol: string;
  exchange: string;
}

interface ClassifyResult {
  asset_class: string;
}

interface AssetSentiment {
  symbol: string;
  asset_class: string;
  sentiment_score: number;
  confidence: number;
  data_sources: string[];
  key_factors: string[];
  risk_events: string[];
  contrarian_signal?: string;
  data_quality: string;
  // Forex
  retail_long_pct?: number;
  retail_short_pct?: number;
  carry_direction?: string;
  active_session?: string;
  // Stocks
  pe_ratio?: number;
  earnings_days?: number;
  sector?: string;
  fifty_two_week_low?: number;
  fifty_two_week_high?: number;
  current_price?: number;
  // Commodities
  seasonal_pattern?: string;
  supply_demand?: string;
  geopolitical_risk?: string;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

const fmt = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1 });
const fmtNum = new Intl.NumberFormat("en-US", { notation: "compact" });

const QUICK_SYMBOLS = ["BTC", "ETH", "SOL", "EUR/USD", "AAPL", "XAUUSD", "FTSE100"];

function getFGColor(val: number): string {
  if (val < 25) return "hsl(0, 84%, 55%)";
  if (val < 45) return "hsl(30, 90%, 50%)";
  if (val < 55) return "hsl(45, 93%, 52%)";
  if (val < 75) return "hsl(100, 60%, 45%)";
  return "hsl(142, 72%, 50%)";
}

function getRegimeColor(regime: string): string {
  switch (regime) {
    case "trending_up": return "text-[hsl(var(--profit))]";
    case "trending_down": return "text-[hsl(var(--loss))]";
    case "volatile": return "text-amber-400";
    case "breakout": return "text-[hsl(var(--chart-2))]";
    default: return "text-muted-foreground";
  }
}

function getRegimeIcon(regime: string) {
  switch (regime) {
    case "trending_up": return TrendingUp;
    case "trending_down": return TrendingDown;
    case "volatile": return Activity;
    case "breakout": return Zap;
    default: return Minus;
  }
}

function getActionColor(action: string): string {
  switch (action) {
    case "accumulate": return "bg-[hsl(var(--profit))]/10 text-[hsl(var(--profit))] border-[hsl(var(--profit))]/30";
    case "reduce": return "bg-[hsl(var(--loss))]/10 text-[hsl(var(--loss))] border-[hsl(var(--loss))]/30";
    case "hold": return "bg-primary/10 text-primary border-primary/30";
    default: return "bg-muted text-muted-foreground";
  }
}

function normalizeClass(ac: string): string {
  if (ac.startsWith("forex")) return "forex";
  if (ac.startsWith("shares")) return "stocks";
  return ac;
}

const ASSET_CLASS_COLORS: Record<string, string> = {
  crypto: "bg-teal-500/20 text-teal-300",
  forex: "bg-purple-500/20 text-purple-300",
  stocks: "bg-blue-500/20 text-blue-300",
  indices: "bg-amber-500/20 text-amber-300",
  commodities: "bg-orange-500/20 text-orange-300",
  metals: "bg-yellow-500/20 text-yellow-300",
};

function SemiCircleGauge({ value, max = 100, color, label, size = 120 }: { value: number; max?: number; color: string; label: string; size?: number }) {
  const pct = Math.min(1, Math.max(0, value / max));
  const r = size / 2 - 10;
  const circumference = Math.PI * r;
  const dashOffset = circumference * (1 - pct);

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size / 2 + 15} viewBox={`0 0 ${size} ${size / 2 + 15}`}>
        <path
          d={`M 10 ${size / 2 + 5} A ${r} ${r} 0 0 1 ${size - 10} ${size / 2 + 5}`}
          fill="none"
          stroke="hsl(0 0% 20%)"
          strokeWidth="8"
          strokeLinecap="round"
        />
        <path
          d={`M 10 ${size / 2 + 5} A ${r} ${r} 0 0 1 ${size - 10} ${size / 2 + 5}`}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          style={{ transition: "stroke-dashoffset 0.8s ease" }}
        />
        <text x={size / 2} y={size / 2 - 2} textAnchor="middle" className="fill-foreground text-xl font-mono font-bold" fontSize="22">
          {value}
        </text>
      </svg>
      <span className="text-[10px] text-muted-foreground uppercase tracking-wider -mt-1">{label}</span>
    </div>
  );
}

// ── Asset-Specific Sentiment Cards ───────────────────────────────────────────

function ForexSentimentCard({ data, isLoading }: { data: AssetSentiment | undefined; isLoading: boolean }) {
  return (
    <Card className="border-card-border bg-card border-purple-500/20" data-testid="forex-sentiment-card">
      <CardHeader className="pb-1">
        <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
          <Globe size={13} className="text-purple-400" />
          Forex Sentiment
        </CardTitle>
      </CardHeader>
      <CardContent className="p-4 pt-0 space-y-3">
        {isLoading ? <Skeleton className="h-[90px] w-full" /> : data ? (
          <>
            <div className="space-y-1.5 pt-2">
              <div className="flex justify-between text-[10px] uppercase tracking-wider">
                <span className="text-green-400">Long {(data.retail_long_pct ?? 50).toFixed(0)}%</span>
                <span className="text-red-400">Short {(data.retail_short_pct ?? 50).toFixed(0)}%</span>
              </div>
              <div className="h-3 rounded-full bg-red-500/30 overflow-hidden">
                <div className="h-full rounded-full bg-green-500 transition-all" style={{ width: `${data.retail_long_pct ?? 50}%` }} />
              </div>
            </div>
            {data.contrarian_signal && (
              <div className="text-xs text-amber-400 flex items-center gap-1">
                <AlertTriangle size={11} /> Contrarian: {data.contrarian_signal}
              </div>
            )}
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div><p className="text-[10px] text-muted-foreground uppercase">Session</p><p className="font-medium">{data.active_session ?? "—"}</p></div>
              <div><p className="text-[10px] text-muted-foreground uppercase">Carry</p><p className="font-medium text-purple-400">{data.carry_direction ?? "—"}</p></div>
            </div>
            <div className="flex flex-wrap gap-1">
              {data.key_factors.slice(0, 3).map((f, i) => (
                <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-300">{f}</span>
              ))}
            </div>
          </>
        ) : <p className="text-xs text-muted-foreground py-4 text-center">No sentiment data</p>}
      </CardContent>
    </Card>
  );
}

function StockSentimentCard({ data, isLoading }: { data: AssetSentiment | undefined; isLoading: boolean }) {
  const range52w = data?.fifty_two_week_high && data?.fifty_two_week_low && data?.current_price
    ? ((data.current_price - data.fifty_two_week_low) / (data.fifty_two_week_high - data.fifty_two_week_low)) * 100
    : null;
  return (
    <Card className="border-card-border bg-card border-blue-500/20" data-testid="stock-sentiment-card">
      <CardHeader className="pb-1">
        <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
          <DollarSign size={13} className="text-blue-400" />
          Stock Fundamentals
        </CardTitle>
      </CardHeader>
      <CardContent className="p-4 pt-0 space-y-3">
        {isLoading ? <Skeleton className="h-[90px] w-full" /> : data ? (
          <>
            <div className="grid grid-cols-2 gap-2 text-xs pt-2">
              <div><p className="text-[10px] text-muted-foreground uppercase">P/E Ratio</p><p className="text-lg font-mono font-bold text-blue-400">{data.pe_ratio?.toFixed(1) ?? "—"}</p></div>
              <div><p className="text-[10px] text-muted-foreground uppercase">Earnings In</p><p className="text-lg font-mono font-bold">{data.earnings_days != null ? `${data.earnings_days}d` : "—"}</p></div>
            </div>
            {data.sector && <Badge variant="outline" className="text-[10px]">{data.sector}</Badge>}
            {range52w != null && (
              <div>
                <p className="text-[10px] text-muted-foreground mb-1">52-Week Range</p>
                <Progress value={range52w} className="h-2" />
                <div className="flex justify-between text-[10px] text-muted-foreground mt-0.5">
                  <span>${data.fifty_two_week_low?.toFixed(0)}</span>
                  <span>${data.fifty_two_week_high?.toFixed(0)}</span>
                </div>
              </div>
            )}
            <div className="flex flex-wrap gap-1">
              {data.key_factors.slice(0, 3).map((f, i) => (
                <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-300">{f}</span>
              ))}
            </div>
          </>
        ) : <p className="text-xs text-muted-foreground py-4 text-center">No fundamentals data</p>}
      </CardContent>
    </Card>
  );
}

function CommoditySentimentCard({ data, isLoading }: { data: AssetSentiment | undefined; isLoading: boolean }) {
  return (
    <Card className="border-card-border bg-card border-orange-500/20" data-testid="commodity-sentiment-card">
      <CardHeader className="pb-1">
        <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
          <Wheat size={13} className="text-orange-400" />
          Commodity Data
        </CardTitle>
      </CardHeader>
      <CardContent className="p-4 pt-0 space-y-3">
        {isLoading ? <Skeleton className="h-[90px] w-full" /> : data ? (
          <>
            <div className="grid grid-cols-3 gap-2 text-xs pt-2">
              <div><p className="text-[10px] text-muted-foreground uppercase">Seasonal</p><p className="font-medium">{data.seasonal_pattern ?? "—"}</p></div>
              <div><p className="text-[10px] text-muted-foreground uppercase">Supply/Demand</p><p className="font-medium">{data.supply_demand ?? "—"}</p></div>
              <div>
                <p className="text-[10px] text-muted-foreground uppercase">Geopolitical</p>
                <p className={`font-medium ${data.geopolitical_risk === "high" ? "text-red-400" : data.geopolitical_risk === "moderate" ? "text-amber-400" : "text-green-400"}`}>
                  {data.geopolitical_risk ?? "—"}
                </p>
              </div>
            </div>
            <div className="flex flex-wrap gap-1">
              {data.key_factors.slice(0, 3).map((f, i) => (
                <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-orange-500/10 text-orange-300">{f}</span>
              ))}
            </div>
            {data.risk_events.length > 0 && (
              <div className="text-xs text-amber-400 flex items-center gap-1">
                <AlertTriangle size={11} /> {data.risk_events[0]}
              </div>
            )}
          </>
        ) : <p className="text-xs text-muted-foreground py-4 text-center">No commodity data</p>}
      </CardContent>
    </Card>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function Signals() {
  const [symbolInput, setSymbolInput] = useState("");
  const [symbol, setSymbol] = useState("BTC");
  const [exchange, setExchange] = useState("binance");

  const applySymbol = useCallback((sym?: string) => {
    const target = sym ?? symbolInput.trim().toUpperCase();
    if (target) {
      setSymbol(target);
      if (!sym) setSymbolInput("");
    }
  }, [symbolInput]);

  // Classify the active symbol
  const { data: classifyData } = useQuery<ClassifyResult>({
    queryKey: ["/api/asset-trading/classify", symbol],
    queryFn: async () => {
      const r = await apiRequest("GET", `/api/asset-trading/classify?symbol=${encodeURIComponent(symbol)}`);
      return r.json();
    },
  });

  const assetClass = classifyData?.asset_class ?? "crypto";
  const normalized = normalizeClass(assetClass);
  const isCrypto = normalized === "crypto";

  // Dashboard data (existing endpoint — works for all, but crypto-specific sections may be empty for non-crypto)
  const { data, isLoading } = useQuery<DashboardData>({
    queryKey: ["/api/signals/dashboard", symbol, exchange],
    queryFn: async () => {
      const res = await apiRequest("GET", `/api/signals/dashboard/${symbol}?exchange=${exchange}`);
      return res.json();
    },
    refetchInterval: 60000,
    retry: 1,
  });

  // Asset-specific sentiment (for non-crypto)
  const { data: assetSentiment, isLoading: sentimentLoading } = useQuery<AssetSentiment>({
    queryKey: ["/api/asset-trading/sentiment", symbol],
    queryFn: async () => {
      const r = await apiRequest("GET", `/api/asset-trading/sentiment?symbol=${encodeURIComponent(symbol)}`);
      return r.json();
    },
    enabled: !isCrypto,
    refetchInterval: 30000,
  });

  const fg = data?.fear_greed;
  const social = data?.social_sentiment;
  const regime = data?.regime;
  const ai = data?.ai_analysis;
  const news = data?.news ?? [];
  const trending = data?.market_data?.trending ?? [];
  const globalData = data?.market_data?.global_data ?? {};

  const RegimeIcon = regime ? getRegimeIcon(regime.regime) : Minus;
  const acBadgeColor = ASSET_CLASS_COLORS[normalized] ?? ASSET_CLASS_COLORS.crypto;

  return (
    <div className="space-y-4" data-testid="signals-page">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-semibold">Signals & AI</h1>
          {ai && (
            <Badge variant="outline" className="text-[10px] px-1.5 py-0 font-mono">
              <Sparkles size={10} className="mr-1" />
              {ai.provider}
            </Badge>
          )}
          <Badge className={`text-[10px] px-1.5 py-0 border-0 ${acBadgeColor}`}>{assetClass}</Badge>
        </div>
        <div className="flex items-center gap-2">
          {/* Symbol text input */}
          <div className="relative">
            <Search size={14} className="absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              data-testid="input-signal-symbol"
              className="h-8 w-36 pl-7 text-xs font-mono"
              placeholder="Any symbol..."
              value={symbolInput}
              onChange={(e) => setSymbolInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && applySymbol()}
            />
          </div>
          <Button size="sm" className="h-8 text-xs" onClick={() => applySymbol()} data-testid="btn-apply-symbol">
            Go
          </Button>
          <Select value={exchange} onValueChange={setExchange}>
            <SelectTrigger className="h-8 w-28 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="binance">Binance</SelectItem>
              <SelectItem value="bybit">Bybit</SelectItem>
              <SelectItem value="kraken">Kraken</SelectItem>
              <SelectItem value="coinbase">Coinbase</SelectItem>
              <SelectItem value="ig">IG</SelectItem>
              <SelectItem value="alpaca">Alpaca</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Quick Symbol Chips */}
      <div className="flex items-center gap-1.5 flex-wrap">
        {QUICK_SYMBOLS.map((qs) => (
          <Button
            key={qs}
            data-testid={`quick-${qs.replace(/\//g, "-").toLowerCase()}`}
            variant={symbol === qs ? "default" : "outline"}
            size="sm"
            className="h-6 text-[10px] px-2"
            onClick={() => applySymbol(qs)}
          >
            {qs}
          </Button>
        ))}
        <span className="text-xs text-muted-foreground ml-2 font-mono">{symbol}</span>
      </div>

      {/* AI Analysis Brief */}
      <Card className="border-card-border bg-card border-primary/20" data-testid="ai-analysis">
        <CardContent className="p-4">
          {isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-5 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          ) : ai ? (
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 space-y-2">
                  <div className="flex items-center gap-2">
                    <Brain size={16} className="text-primary" />
                    <span className="text-sm font-medium">AI Market Brief</span>
                  </div>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {ai.market_brief}
                  </p>
                </div>
                <div className="flex flex-col items-end gap-1.5 shrink-0">
                  <Badge variant="outline" className={`text-xs font-semibold ${getActionColor(ai.recommended_action)}`}>
                    {ai.recommended_action.toUpperCase()}
                  </Badge>
                  <Badge variant="outline" className={`text-[10px] ${
                    ai.risk_level === "high" ? "text-[hsl(var(--loss))] border-[hsl(var(--loss))]/30" :
                    ai.risk_level === "medium" ? "text-amber-400 border-amber-400/30" :
                    "text-[hsl(var(--profit))] border-[hsl(var(--profit))]/30"
                  }`}>
                    Risk: {ai.risk_level}
                  </Badge>
                </div>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {ai.key_factors.map((f, i) => (
                  <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-muted/50 text-muted-foreground">{f}</span>
                ))}
              </div>
              {ai.warnings.length > 0 && ai.warnings[0] !== "No significant warnings" && (
                <div className="flex items-start gap-1.5 text-xs text-amber-400/80">
                  <AlertTriangle size={12} className="mt-0.5 shrink-0" />
                  <span>{ai.warnings.join(" · ")}</span>
                </div>
              )}
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-[10px] text-muted-foreground uppercase">Strategies:</span>
                {ai.recommended_strategies.map((s, i) => (
                  <Badge key={i} variant="secondary" className="text-[10px] px-1.5 py-0">{s}</Badge>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Unable to load AI analysis</p>
          )}
        </CardContent>
      </Card>

      {/* Gauges Row — adapts per asset class */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Column 1: Fear & Greed (crypto) or Asset Sentiment */}
        {isCrypto ? (
          <Card className="border-card-border bg-card" data-testid="fear-greed-card">
            <CardHeader className="pb-1">
              <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                <ThermometerSun size={13} />
                Fear & Greed Index
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0 flex flex-col items-center">
              {isLoading ? (
                <Skeleton className="h-[90px] w-[140px]" />
              ) : fg ? (
                <>
                  <SemiCircleGauge
                    value={fg.value}
                    max={100}
                    color={getFGColor(fg.value)}
                    label={fg.label}
                    size={140}
                  />
                  {fg.history && fg.history.length > 1 && (
                    <div className="w-full mt-2">
                      <ResponsiveContainer width="100%" height={40}>
                        <AreaChart data={[...fg.history].reverse()}>
                          <Area
                            type="monotone"
                            dataKey="value"
                            stroke={getFGColor(fg.value)}
                            fill={getFGColor(fg.value)}
                            fillOpacity={0.1}
                            strokeWidth={1.5}
                          />
                          <Tooltip
                            contentStyle={{ backgroundColor: "hsl(0 0% 12%)", border: "1px solid hsl(0 0% 20%)", borderRadius: "6px", fontSize: "10px" }}
                            formatter={(v: number) => [v, "F&G"]}
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </>
              ) : null}
            </CardContent>
          </Card>
        ) : normalized === "forex" ? (
          <ForexSentimentCard data={assetSentiment} isLoading={sentimentLoading} />
        ) : normalized === "stocks" ? (
          <StockSentimentCard data={assetSentiment} isLoading={sentimentLoading} />
        ) : (
          <CommoditySentimentCard data={assetSentiment} isLoading={sentimentLoading} />
        )}

        {/* Column 2: Social Sentiment (crypto) or Sentiment Score (non-crypto) */}
        {isCrypto ? (
          <Card className="border-card-border bg-card" data-testid="social-sentiment-card">
            <CardHeader className="pb-1">
              <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                <BarChart3 size={13} />
                Social Sentiment — {symbol}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0 space-y-3">
              {isLoading ? (
                <Skeleton className="h-[90px] w-full" />
              ) : social ? (
                <>
                  <div className="space-y-1.5 pt-2">
                    <div className="flex justify-between text-[10px] uppercase tracking-wider">
                      <span className="text-[hsl(var(--profit))]">Bullish {social.bullish_pct}%</span>
                      <span className="text-[hsl(var(--loss))]">Bearish {social.bearish_pct}%</span>
                    </div>
                    <div className="h-3 rounded-full bg-[hsl(var(--loss))]/30 overflow-hidden">
                      <div className="h-full rounded-full bg-[hsl(var(--profit))] transition-all" style={{ width: `${social.bullish_pct}%` }} />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div><p className="text-[10px] text-muted-foreground uppercase">Mentions 24h</p><p className="text-sm font-mono font-medium">{fmtNum.format(social.mentions_24h)}</p></div>
                    <div>
                      <p className="text-[10px] text-muted-foreground uppercase">Vol Change</p>
                      <p className={`text-sm font-mono font-medium ${social.volume_change_pct >= 0 ? "text-[hsl(var(--profit))]" : "text-[hsl(var(--loss))]"}`}>
                        {social.volume_change_pct >= 0 ? "+" : ""}{social.volume_change_pct}%
                      </p>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {social.trending_keywords.map((kw, i) => (
                      <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary">#{kw}</span>
                    ))}
                  </div>
                </>
              ) : null}
            </CardContent>
          </Card>
        ) : (
          /* Non-crypto: show sentiment score gauge */
          <Card className="border-card-border bg-card" data-testid="asset-sentiment-score">
            <CardHeader className="pb-1">
              <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                <BarChart3 size={13} />
                Sentiment Score — {symbol}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0 flex flex-col items-center">
              {sentimentLoading ? (
                <Skeleton className="h-[90px] w-[140px]" />
              ) : assetSentiment ? (
                <>
                  <SemiCircleGauge
                    value={Math.round(assetSentiment.sentiment_score * 100)}
                    max={100}
                    color={assetSentiment.sentiment_score > 0.6 ? "hsl(142, 72%, 50%)" : assetSentiment.sentiment_score < 0.4 ? "hsl(0, 84%, 55%)" : "hsl(45, 93%, 52%)"}
                    label={assetSentiment.sentiment_score > 0.6 ? "Bullish" : assetSentiment.sentiment_score < 0.4 ? "Bearish" : "Neutral"}
                    size={140}
                  />
                  <div className="flex items-center gap-2 mt-2">
                    <Badge variant="outline" className="text-[10px]">
                      Confidence: {(assetSentiment.confidence * 100).toFixed(0)}%
                    </Badge>
                    <Badge variant="outline" className="text-[10px]">
                      Quality: {assetSentiment.data_quality}
                    </Badge>
                  </div>
                  <div className="flex flex-wrap gap-1 mt-2 justify-center">
                    {assetSentiment.data_sources.map((s, i) => (
                      <span key={i} className="text-[9px] px-1.5 py-0.5 rounded bg-muted/50 text-muted-foreground">{s}</span>
                    ))}
                  </div>
                </>
              ) : null}
            </CardContent>
          </Card>
        )}

        {/* Column 3: Market Regime (works for all) */}
        <Card className="border-card-border bg-card" data-testid="regime-card">
          <CardHeader className="pb-1">
            <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
              <Gauge size={13} />
              Market Regime
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0 space-y-3">
            {isLoading ? (
              <Skeleton className="h-[90px] w-full" />
            ) : regime ? (
              <>
                <div className="flex items-center gap-2 pt-2">
                  <RegimeIcon size={20} className={getRegimeColor(regime.regime)} />
                  <div>
                    <p className={`text-lg font-semibold capitalize ${getRegimeColor(regime.regime)}`}>
                      {regime.regime.replace("_", " ")}
                    </p>
                    <p className="text-[10px] text-muted-foreground">
                      Confidence: {(regime.confidence * 100).toFixed(0)}%
                    </p>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {regime.description}
                </p>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[10px]">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">ADX</span>
                    <span className="font-mono">{regime.metrics?.adx_approx ?? "—"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Volatility</span>
                    <span className="font-mono">{regime.metrics?.volatility_annual ?? "—"}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">BB Width</span>
                    <span className="font-mono">{regime.metrics?.bb_width ?? "—"}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">SMA Cross</span>
                    <span className={`font-mono ${regime.metrics?.sma_cross === "bullish" ? "text-[hsl(var(--profit))]" : "text-[hsl(var(--loss))]"}`}>
                      {regime.metrics?.sma_cross ?? "—"}
                    </span>
                  </div>
                </div>
              </>
            ) : null}
          </CardContent>
        </Card>
      </div>

      {/* News + Trending/Global (crypto) or Risk Events (non-crypto) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* News Feed */}
        <Card className="lg:col-span-2 border-card-border bg-card" data-testid="news-feed">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
              <Newspaper size={14} />
              Latest News — {symbol}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            {isLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : news.length > 0 ? (
              <div className="space-y-1 max-h-[360px] overflow-y-auto">
                {news.map((article, i) => (
                  <a
                    key={i}
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-start gap-3 p-2 rounded-md hover:bg-muted/30 transition-colors group"
                    data-testid={`news-item-${i}`}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium leading-snug line-clamp-2 group-hover:text-primary transition-colors">
                        {article.title}
                      </p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <Badge variant="outline" className="text-[9px] px-1 py-0 shrink-0">{article.source}</Badge>
                        <span className="text-[10px] text-muted-foreground">
                          {new Date(article.published).toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                        </span>
                      </div>
                    </div>
                    <ExternalLink size={12} className="text-muted-foreground mt-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </a>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground py-6 text-center">No news available</p>
            )}
          </CardContent>
        </Card>

        {/* Right column: crypto shows global+trending, non-crypto shows risk events */}
        <div className="space-y-4">
          {isCrypto ? (
            <>
              {/* Global Market */}
              <Card className="border-card-border bg-card" data-testid="global-market">
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                    <Activity size={13} />
                    Global Crypto Market
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-4 pt-0 space-y-2">
                  {isLoading ? (
                    <Skeleton className="h-[80px] w-full" />
                  ) : (
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div><p className="text-[10px] text-muted-foreground uppercase">Market Cap</p><p className="font-mono font-medium">{fmt.format(globalData.total_market_cap_usd || 0)}</p></div>
                      <div><p className="text-[10px] text-muted-foreground uppercase">24h Volume</p><p className="font-mono font-medium">{fmt.format(globalData.total_volume_24h || 0)}</p></div>
                      <div><p className="text-[10px] text-muted-foreground uppercase">BTC Dominance</p><p className="font-mono font-medium">{globalData.btc_dominance || 0}%</p></div>
                      <div>
                        <p className="text-[10px] text-muted-foreground uppercase">24h Change</p>
                        <p className={`font-mono font-medium ${(globalData.market_cap_change_24h ?? 0) >= 0 ? "text-[hsl(var(--profit))]" : "text-[hsl(var(--loss))]"}`}>
                          {(globalData.market_cap_change_24h ?? 0) >= 0 ? "+" : ""}{globalData.market_cap_change_24h ?? 0}%
                        </p>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Trending Coins */}
              <Card className="border-card-border bg-card" data-testid="trending-coins">
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                    <Flame size={13} className="text-amber-400" />
                    Trending Coins
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-4 pt-0">
                  {isLoading ? (
                    <div className="space-y-1.5">
                      {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-6 w-full" />)}
                    </div>
                  ) : trending.length > 0 ? (
                    <div className="space-y-1 max-h-[200px] overflow-y-auto">
                      {trending.map((coin, i) => (
                        <div key={i} className="flex items-center justify-between py-1 px-1 rounded hover:bg-muted/20 transition-colors">
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] text-muted-foreground w-4">{i + 1}</span>
                            <span className="text-xs font-medium">{coin.name}</span>
                            <Badge variant="outline" className="text-[9px] px-1 py-0 font-mono">{coin.symbol}</Badge>
                          </div>
                          {coin.market_cap_rank && <span className="text-[10px] text-muted-foreground font-mono">#{coin.market_cap_rank}</span>}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground py-4 text-center">No trending data</p>
                  )}
                </CardContent>
              </Card>
            </>
          ) : (
            /* Non-crypto: risk events + data sources */
            <>
              <Card className="border-card-border bg-card" data-testid="risk-events">
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                    <AlertTriangle size={13} className="text-amber-400" />
                    Risk Events
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-4 pt-0">
                  {sentimentLoading ? (
                    <Skeleton className="h-[80px] w-full" />
                  ) : assetSentiment?.risk_events && assetSentiment.risk_events.length > 0 ? (
                    <div className="space-y-1.5">
                      {assetSentiment.risk_events.map((evt, i) => (
                        <div key={i} className="text-xs px-2 py-1.5 rounded-md bg-amber-500/10 text-amber-300">
                          <AlertTriangle size={10} className="inline mr-1" />{evt}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground py-4 text-center">No risk events detected</p>
                  )}
                </CardContent>
              </Card>

              <Card className="border-card-border bg-card" data-testid="key-factors">
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                    <Activity size={13} />
                    Key Factors
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-4 pt-0">
                  {sentimentLoading ? (
                    <Skeleton className="h-[80px] w-full" />
                  ) : assetSentiment?.key_factors && assetSentiment.key_factors.length > 0 ? (
                    <div className="space-y-1.5">
                      {assetSentiment.key_factors.map((f, i) => (
                        <div key={i} className="text-xs px-2 py-1.5 rounded-md bg-muted/30 text-muted-foreground">{f}</div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground py-4 text-center">No key factors</p>
                  )}
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
