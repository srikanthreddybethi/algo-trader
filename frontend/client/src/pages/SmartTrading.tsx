import { useState, useCallback, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Search,
  TrendingUp,
  TrendingDown,
  Shield,
  Clock,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Zap,
  Target,
  BarChart3,
  Activity,
  PoundSterling,
  DollarSign,
  Globe,
  Gem,
  Flame,
  Wheat,
} from "lucide-react";

// ── Asset Color Scheme ───────────────────────────────────────────────────────

const ASSET_COLORS: Record<string, { bg: string; text: string; border: string; badge: string }> = {
  crypto: { bg: "bg-teal-500/10", text: "text-teal-400", border: "border-teal-500/30", badge: "bg-teal-500/20 text-teal-300" },
  forex: { bg: "bg-purple-500/10", text: "text-purple-400", border: "border-purple-500/30", badge: "bg-purple-500/20 text-purple-300" },
  forex_major: { bg: "bg-purple-500/10", text: "text-purple-400", border: "border-purple-500/30", badge: "bg-purple-500/20 text-purple-300" },
  forex_minor: { bg: "bg-purple-500/10", text: "text-purple-400", border: "border-purple-500/30", badge: "bg-purple-500/20 text-purple-300" },
  stocks: { bg: "bg-blue-500/10", text: "text-blue-400", border: "border-blue-500/30", badge: "bg-blue-500/20 text-blue-300" },
  shares_us: { bg: "bg-blue-500/10", text: "text-blue-400", border: "border-blue-500/30", badge: "bg-blue-500/20 text-blue-300" },
  shares_uk: { bg: "bg-blue-500/10", text: "text-blue-400", border: "border-blue-500/30", badge: "bg-blue-500/20 text-blue-300" },
  indices: { bg: "bg-amber-500/10", text: "text-amber-400", border: "border-amber-500/30", badge: "bg-amber-500/20 text-amber-300" },
  commodities: { bg: "bg-orange-500/10", text: "text-orange-400", border: "border-orange-500/30", badge: "bg-orange-500/20 text-orange-300" },
  metals: { bg: "bg-yellow-500/10", text: "text-yellow-400", border: "border-yellow-500/30", badge: "bg-yellow-500/20 text-yellow-300" },
};

const QUICK_SYMBOLS = [
  { symbol: "BTC/USDT", label: "BTC" },
  { symbol: "EUR/USD", label: "EUR/USD" },
  { symbol: "AAPL", label: "AAPL" },
  { symbol: "FTSE100", label: "FTSE100" },
  { symbol: "XAUUSD", label: "Gold" },
];

const MARKET_TYPE_MAP: Record<string, string> = {
  crypto: "24/7",
  forex: "24/5",
  forex_major: "24/5",
  forex_minor: "24/5",
  stocks: "Exchange Hours",
  shares_us: "NYSE Hours",
  shares_uk: "LSE Hours",
  indices: "Exchange Hours",
  commodities: "Exchange Hours",
  metals: "23/5",
};

const ASSET_ICONS: Record<string, React.ElementType> = {
  crypto: Gem,
  forex: Globe,
  forex_major: Globe,
  forex_minor: Globe,
  stocks: DollarSign,
  shares_us: DollarSign,
  shares_uk: PoundSterling,
  indices: BarChart3,
  commodities: Flame,
  metals: Wheat,
};

// ── Types ────────────────────────────────────────────────────────────────────

interface ClassifyResult {
  symbol: string;
  asset_class: string;
  sub_class?: string;
  market_type?: string;
}

interface RulesResult {
  symbol: string;
  asset_class: string;
  regime: string;
  rules_engine: string;
  risk_params?: {
    stop_loss_pct?: number;
    take_profit_pct?: number;
    max_position_pct?: number;
    max_leverage?: number;
    [key: string]: unknown;
  };
  parameters?: {
    stop_loss_pct?: number;
    take_profit_pct?: number;
    max_position_pct?: number;
    max_leverage?: number;
    [key: string]: unknown;
  };
}

interface ValidationResult {
  symbol: string;
  direction: string;
  allowed: boolean;
  size_multiplier: number;
  warnings: Array<string | { level: string; message: string }>;
}

interface StrategyResult {
  name: string;
  weight: number;
  parameters?: Record<string, unknown>;
  params?: Record<string, unknown>;
}

interface SentimentResult {
  symbol: string;
  asset_class: string;
  sentiment_score: number;
  confidence: number;
  data_sources: string[];
  key_factors: string[];
  risk_events: string[];
  contrarian_signal?: string;
  data_quality: string;
  // Crypto-specific
  fear_greed_index?: number;
  fear_greed_label?: string;
  btc_dominance?: number;
  social_score?: number;
  // Forex-specific
  retail_long_pct?: number;
  retail_short_pct?: number;
  carry_direction?: string;
  active_session?: string;
  // Stocks-specific
  pe_ratio?: number;
  earnings_days?: number;
  sector?: string;
  fifty_two_week_low?: number;
  fifty_two_week_high?: number;
  current_price?: number;
  // Indices-specific
  advancing_pct?: number;
  declining_pct?: number;
  vix_level?: number;
  // Commodities-specific
  seasonal_pattern?: string;
  supply_demand?: string;
  geopolitical_risk?: string;
}

interface MarketHoursResult {
  is_open: boolean;
  session: string;
  next_open: string | null;
  next_close: string | null;
  gap_risk: string;
  optimal_windows?: string[];
}

interface SpreadBetResult {
  recommendation: string;
  stake_per_point: number;
  margin_required: number;
  tax_free: boolean;
  guaranteed_stop_recommended: boolean;
  daily_funding_cost: number;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function getColors(assetClass: string) {
  return ASSET_COLORS[assetClass] ?? ASSET_COLORS.crypto;
}

function normalizeClass(ac: string): string {
  if (ac.startsWith("forex")) return "forex";
  if (ac.startsWith("shares")) return "stocks";
  return ac;
}

const GBP = (n: number) => `£${n.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function formatCountdown(isoStr: string | null): string {
  if (!isoStr) return "—";
  const diff = new Date(isoStr).getTime() - Date.now();
  if (diff <= 0) return "Now";
  const h = Math.floor(diff / 3600000);
  const m = Math.floor((diff % 3600000) / 60000);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

// ── Loading Skeleton ─────────────────────────────────────────────────────────

function SectionSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <Card className="border-card-border bg-card">
      <CardHeader className="pb-3">
        <Skeleton className="h-5 w-40" />
      </CardHeader>
      <CardContent className="space-y-3">
        {Array.from({ length: rows }).map((_, i) => (
          <Skeleton key={i} className="h-4 w-full" />
        ))}
      </CardContent>
    </Card>
  );
}

// ── Section 1: Asset Intelligence ────────────────────────────────────────────

function AssetIntelligence({
  classify,
  rules,
  sentiment,
}: {
  classify: ClassifyResult;
  rules: RulesResult | undefined;
  sentiment: SentimentResult | undefined;
}) {
  const colors = getColors(classify.asset_class);
  const normalized = normalizeClass(classify.asset_class);
  const AssetIcon = ASSET_ICONS[classify.asset_class] ?? Activity;

  return (
    <Card data-testid="asset-intelligence" className={`border ${colors.border} bg-card`}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <AssetIcon size={18} className={colors.text} />
            Asset Intelligence
          </CardTitle>
          <div className="flex gap-2">
            <Badge className={colors.badge}>{classify.asset_class}</Badge>
            <Badge variant="outline">{MARKET_TYPE_MAP[classify.asset_class] ?? "Market"}</Badge>
            {rules && <Badge variant="outline">{rules.rules_engine}</Badge>}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Risk Parameters */}
        {rules && (
          <div>
            <h4 className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wider">Risk Parameters</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <ParamCell label="Stop Loss" value={`${(rules.risk_params ?? rules.parameters ?? {}).stop_loss_pct ?? '-'}%`} />
              <ParamCell label="Take Profit" value={`${(rules.risk_params ?? rules.parameters ?? {}).take_profit_pct ?? '-'}%`} />
              <ParamCell label="Max Position" value={`${(rules.risk_params ?? rules.parameters ?? {}).max_position_pct ?? '-'}%`} />
              <ParamCell label="Max Leverage" value={`${(rules.risk_params ?? rules.parameters ?? {}).max_leverage ?? '-'}x`} />
            </div>
          </div>
        )}

        {/* Asset-specific Sentiment */}
        {sentiment && (
          <div>
            <h4 className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wider">Market Sentiment</h4>
            {normalized === "crypto" && <CryptoSentiment data={sentiment} />}
            {normalized === "forex" && <ForexSentiment data={sentiment} />}
            {normalized === "stocks" && <StockSentiment data={sentiment} />}
            {normalized === "indices" && <IndexSentiment data={sentiment} />}
            {normalized === "commodities" && <CommoditySentiment data={sentiment} />}
            {normalized === "metals" && <CommoditySentiment data={sentiment} />}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ParamCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-muted/30 rounded-md p-2 text-center">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-sm font-semibold">{value}</div>
    </div>
  );
}

function CryptoSentiment({ data }: { data: SentimentResult }) {
  const fgColor = (data.fear_greed_index ?? 50) < 30 ? "text-red-400" : (data.fear_greed_index ?? 50) > 70 ? "text-green-400" : "text-yellow-400";
  return (
    <div className="grid grid-cols-3 gap-3">
      <div className="bg-muted/30 rounded-md p-3">
        <div className="text-xs text-muted-foreground">Fear & Greed</div>
        <div className={`text-xl font-bold ${fgColor}`}>{data.fear_greed_index ?? "—"}</div>
        <div className="text-xs text-muted-foreground">{data.fear_greed_label ?? ""}</div>
      </div>
      <div className="bg-muted/30 rounded-md p-3">
        <div className="text-xs text-muted-foreground">BTC Dominance</div>
        <div className="text-xl font-bold text-teal-400">{data.btc_dominance ? `${data.btc_dominance.toFixed(1)}%` : "—"}</div>
      </div>
      <div className="bg-muted/30 rounded-md p-3">
        <div className="text-xs text-muted-foreground">Social Score</div>
        <div className="text-xl font-bold">{data.social_score ?? "—"}</div>
        <Progress value={(data.social_score ?? 50)} className="mt-1 h-1" />
      </div>
    </div>
  );
}

function ForexSentiment({ data }: { data: SentimentResult }) {
  const longPct = data.retail_long_pct ?? 50;
  const shortPct = data.retail_short_pct ?? 50;
  return (
    <div className="grid grid-cols-3 gap-3">
      <div className="bg-muted/30 rounded-md p-3 col-span-2">
        <div className="text-xs text-muted-foreground mb-1">Retail Positioning</div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-green-400 w-12">{longPct.toFixed(0)}% L</span>
          <div className="flex-1 h-3 rounded-full bg-red-500/30 overflow-hidden">
            <div className="h-full bg-green-500 rounded-full transition-all" style={{ width: `${longPct}%` }} />
          </div>
          <span className="text-xs text-red-400 w-12 text-right">{shortPct.toFixed(0)}% S</span>
        </div>
        {data.contrarian_signal && (
          <div className="mt-1 text-xs text-amber-400">Contrarian: {data.contrarian_signal}</div>
        )}
      </div>
      <div className="bg-muted/30 rounded-md p-3">
        <div className="text-xs text-muted-foreground">Session</div>
        <div className="text-sm font-semibold">{data.active_session ?? "—"}</div>
        {data.carry_direction && (
          <div className="text-xs text-purple-400 mt-1">Carry: {data.carry_direction}</div>
        )}
      </div>
    </div>
  );
}

function StockSentiment({ data }: { data: SentimentResult }) {
  const range52w = data.fifty_two_week_high && data.fifty_two_week_low && data.current_price
    ? ((data.current_price - data.fifty_two_week_low) / (data.fifty_two_week_high - data.fifty_two_week_low)) * 100
    : null;
  return (
    <div className="grid grid-cols-3 gap-3">
      <div className="bg-muted/30 rounded-md p-3">
        <div className="text-xs text-muted-foreground">P/E Ratio</div>
        <div className="text-xl font-bold text-blue-400">{data.pe_ratio?.toFixed(1) ?? "—"}</div>
      </div>
      <div className="bg-muted/30 rounded-md p-3">
        <div className="text-xs text-muted-foreground">Earnings In</div>
        <div className="text-xl font-bold">{data.earnings_days != null ? `${data.earnings_days}d` : "—"}</div>
        {data.sector && <Badge variant="outline" className="mt-1 text-[10px]">{data.sector}</Badge>}
      </div>
      <div className="bg-muted/30 rounded-md p-3">
        <div className="text-xs text-muted-foreground">52W Range</div>
        {range52w != null ? (
          <>
            <Progress value={range52w} className="mt-2 h-2" />
            <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
              <span>${data.fifty_two_week_low?.toFixed(0)}</span>
              <span>${data.fifty_two_week_high?.toFixed(0)}</span>
            </div>
          </>
        ) : (
          <div className="text-sm text-muted-foreground mt-1">—</div>
        )}
      </div>
    </div>
  );
}

function IndexSentiment({ data }: { data: SentimentResult }) {
  const adv = data.advancing_pct ?? 50;
  return (
    <div className="grid grid-cols-2 gap-3">
      <div className="bg-muted/30 rounded-md p-3">
        <div className="text-xs text-muted-foreground mb-1">Market Breadth</div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-green-400 w-10">{adv.toFixed(0)}%</span>
          <div className="flex-1 h-3 rounded-full bg-red-500/30 overflow-hidden">
            <div className="h-full bg-green-500 rounded-full transition-all" style={{ width: `${adv}%` }} />
          </div>
          <span className="text-xs text-red-400 w-10 text-right">{(100 - adv).toFixed(0)}%</span>
        </div>
        <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
          <span>Advancing</span>
          <span>Declining</span>
        </div>
      </div>
      <div className="bg-muted/30 rounded-md p-3">
        <div className="text-xs text-muted-foreground">VIX Level</div>
        <div className={`text-xl font-bold ${(data.vix_level ?? 20) > 30 ? "text-red-400" : (data.vix_level ?? 20) > 20 ? "text-amber-400" : "text-green-400"}`}>
          {data.vix_level?.toFixed(1) ?? "—"}
        </div>
        <div className="text-xs text-muted-foreground">{(data.vix_level ?? 20) > 30 ? "High Fear" : (data.vix_level ?? 20) > 20 ? "Elevated" : "Calm"}</div>
      </div>
    </div>
  );
}

function CommoditySentiment({ data }: { data: SentimentResult }) {
  return (
    <div className="grid grid-cols-3 gap-3">
      <div className="bg-muted/30 rounded-md p-3">
        <div className="text-xs text-muted-foreground">Seasonal</div>
        <div className="text-sm font-semibold">{data.seasonal_pattern ?? "—"}</div>
      </div>
      <div className="bg-muted/30 rounded-md p-3">
        <div className="text-xs text-muted-foreground">Supply/Demand</div>
        <div className="text-sm font-semibold">{data.supply_demand ?? "—"}</div>
      </div>
      <div className="bg-muted/30 rounded-md p-3">
        <div className="text-xs text-muted-foreground">Geopolitical</div>
        <div className={`text-sm font-semibold ${data.geopolitical_risk === "high" ? "text-red-400" : data.geopolitical_risk === "moderate" ? "text-amber-400" : "text-green-400"}`}>
          {data.geopolitical_risk ?? "—"}
        </div>
      </div>
    </div>
  );
}

// ── Section 2: Trade Validation ──────────────────────────────────────────────

function TradeValidation({
  symbol,
  buyValidation,
  sellValidation,
  isLoading,
}: {
  symbol: string;
  buyValidation: ValidationResult | undefined;
  sellValidation: ValidationResult | undefined;
  isLoading: boolean;
}) {
  if (isLoading) return <SectionSkeleton rows={4} />;

  return (
    <Card data-testid="trade-validation" className="border-card-border bg-card">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Shield size={18} className="text-blue-400" />
          Trade Validation
          <Badge variant="outline" className="ml-auto text-[10px]">LIVE</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <ValidationColumn direction="BUY" data={buyValidation} />
          <ValidationColumn direction="SELL" data={sellValidation} />
        </div>
      </CardContent>
    </Card>
  );
}

function ValidationColumn({ direction, data }: { direction: string; data: ValidationResult | undefined }) {
  const isBuy = direction === "BUY";
  const icon = isBuy ? <TrendingUp size={16} /> : <TrendingDown size={16} />;
  const colorClass = isBuy ? "text-green-400" : "text-red-400";

  if (!data) {
    return (
      <div className="bg-muted/20 rounded-lg p-4">
        <div className={`flex items-center gap-2 mb-3 font-medium ${colorClass}`}>
          {icon} {direction}
        </div>
        <div className="text-sm text-muted-foreground">No data</div>
      </div>
    );
  }

  return (
    <div data-testid={`validation-${direction.toLowerCase()}`} className="bg-muted/20 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div className={`flex items-center gap-2 font-medium ${colorClass}`}>
          {icon} {direction}
        </div>
        {data.allowed ? (
          <Badge className="bg-green-500/20 text-green-300"><CheckCircle2 size={12} className="mr-1" /> Allowed</Badge>
        ) : (
          <Badge className="bg-red-500/20 text-red-300"><XCircle size={12} className="mr-1" /> Blocked</Badge>
        )}
      </div>

      {data.size_multiplier !== 1 && (
        <div className="text-xs text-muted-foreground mb-2">
          Size multiplier: <span className="font-mono font-semibold">{data.size_multiplier.toFixed(2)}x</span>
        </div>
      )}

      {data.warnings && data.warnings.length > 0 && (
        <div className="space-y-1.5 mt-2">
          {data.warnings.map((w, i) => {
            const msg = typeof w === "string" ? w : w.message;
            const level = typeof w === "string" ? (data.allowed ? "warning" : "error") : w.level;
            return (
              <div key={i} className={`text-xs px-2 py-1 rounded-md ${
                level === "error" || level === "blocker" ? "bg-red-500/15 text-red-300" :
                level === "warning" ? "bg-amber-500/15 text-amber-300" :
                "bg-green-500/15 text-green-300"
              }`}>
                {msg}
              </div>
            );
          })}
        </div>
      )}

      {(!data.warnings || data.warnings.length === 0) && data.allowed && (
        <div className="text-xs text-green-400/70 mt-1">All checks passed</div>
      )}
    </div>
  );
}

// ── Section 3: Optimal Strategies ────────────────────────────────────────────

function OptimalStrategies({
  strategies,
  regime,
  onRegimeChange,
  isLoading,
  assetClass,
}: {
  strategies: StrategyResult[] | undefined;
  regime: string;
  onRegimeChange: (r: string) => void;
  isLoading: boolean;
  assetClass: string;
}) {
  const colors = getColors(assetClass);

  return (
    <Card data-testid="optimal-strategies" className="border-card-border bg-card">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Target size={18} className="text-amber-400" />
            Optimal Strategies
          </CardTitle>
          <Select value={regime} onValueChange={onRegimeChange}>
            <SelectTrigger data-testid="regime-selector" className="w-40 h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="trending_up">Trending Up</SelectItem>
              <SelectItem value="trending_down">Trending Down</SelectItem>
              <SelectItem value="ranging">Ranging</SelectItem>
              <SelectItem value="volatile">Volatile</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {[1, 2, 3].map(i => <Skeleton key={i} className="h-24 w-full" />)}
          </div>
        ) : strategies && strategies.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {strategies.map((s, i) => (
              <div key={i} className={`${colors.bg} border ${colors.border} rounded-lg p-3`}>
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-sm font-medium ${colors.text}`}>{s.name}</span>
                  <span className="text-xs text-muted-foreground font-mono">{(s.weight * 100).toFixed(0)}%</span>
                </div>
                <Progress value={s.weight * 100} className="h-1.5 mb-2" />
                <div className="flex flex-wrap gap-1">
                  {Object.entries(s.params ?? s.parameters ?? {}).map(([k, v]) => (
                    <Badge key={k} variant="outline" className="text-[10px] py-0">
                      {k}: {String(v)}
                    </Badge>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-sm text-muted-foreground text-center py-6">No strategies available for this regime</div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Section 4: Market Status ─────────────────────────────────────────────────

function MarketStatus({
  marketHours,
  isLoading,
}: {
  marketHours: MarketHoursResult | undefined;
  isLoading: boolean;
}) {
  if (isLoading) return <SectionSkeleton rows={3} />;
  if (!marketHours) return null;

  return (
    <Card data-testid="market-status" className="border-card-border bg-card">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Clock size={18} className="text-cyan-400" />
          Market Status
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-muted/30 rounded-md p-3 text-center">
            <div className={`text-2xl font-bold ${marketHours.is_open ? "text-green-400" : "text-red-400"}`}>
              {marketHours.is_open ? "OPEN" : "CLOSED"}
            </div>
            <div className="text-xs text-muted-foreground mt-1">{marketHours.session}</div>
          </div>
          <div className="bg-muted/30 rounded-md p-3 text-center">
            <div className="text-xs text-muted-foreground">Next {marketHours.is_open ? "Close" : "Open"}</div>
            <div className="text-lg font-semibold mt-1">
              {formatCountdown(marketHours.is_open ? marketHours.next_close : marketHours.next_open)}
            </div>
          </div>
          <div className="bg-muted/30 rounded-md p-3 text-center">
            <div className="text-xs text-muted-foreground">Gap Risk</div>
            <Badge className={`mt-1 ${
              marketHours.gap_risk === "high" ? "bg-red-500/20 text-red-300" :
              marketHours.gap_risk === "medium" ? "bg-amber-500/20 text-amber-300" :
              "bg-green-500/20 text-green-300"
            }`}>
              {marketHours.gap_risk ?? "low"}
            </Badge>
          </div>
          {marketHours.optimal_windows && marketHours.optimal_windows.length > 0 && (
            <div className="bg-muted/30 rounded-md p-3">
              <div className="text-xs text-muted-foreground mb-1">Best Windows</div>
              <div className="space-y-1">
                {marketHours.optimal_windows.slice(0, 3).map((w, i) => (
                  <div key={i} className="text-xs font-mono">{w}</div>
                ))}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Section 5: Spread Betting Quick Panel ────────────────────────────────────

function SpreadBetPanel({
  spreadBet,
  isLoading,
  assetClass,
}: {
  spreadBet: SpreadBetResult | undefined;
  isLoading: boolean;
  assetClass: string;
}) {
  const normalized = normalizeClass(assetClass);
  const showSpreadBet = ["forex", "indices", "commodities", "metals"].includes(normalized);
  if (!showSpreadBet) return null;
  if (isLoading) return <SectionSkeleton rows={2} />;
  if (!spreadBet) return null;

  return (
    <Card data-testid="spread-bet-panel" className="border-purple-500/30 bg-card">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <PoundSterling size={18} className="text-purple-400" />
          Spread Betting
          <Badge className="bg-green-500/20 text-green-300 ml-2">Tax-Free</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div className="bg-muted/30 rounded-md p-3 text-center">
            <div className="text-xs text-muted-foreground">£/Point Stake</div>
            <div className="text-lg font-bold text-purple-400">{GBP(spreadBet.stake_per_point)}</div>
          </div>
          <div className="bg-muted/30 rounded-md p-3 text-center">
            <div className="text-xs text-muted-foreground">Margin Required</div>
            <div className="text-lg font-bold">{GBP(spreadBet.margin_required)}</div>
          </div>
          <div className="bg-muted/30 rounded-md p-3 text-center">
            <div className="text-xs text-muted-foreground">Guaranteed Stop</div>
            <div className={`text-sm font-semibold ${spreadBet.guaranteed_stop_recommended ? "text-amber-400" : "text-green-400"}`}>
              {spreadBet.guaranteed_stop_recommended ? "Recommended" : "Optional"}
            </div>
          </div>
          <div className="bg-muted/30 rounded-md p-3 text-center">
            <div className="text-xs text-muted-foreground">Daily Funding</div>
            <div className="text-lg font-bold text-amber-400">{GBP(spreadBet.daily_funding_cost)}</div>
          </div>
          <div className="bg-muted/30 rounded-md p-3 text-center">
            <div className="text-xs text-muted-foreground">Recommendation</div>
            <div className="text-sm font-semibold">{spreadBet.recommendation}</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Section 6: Quick Trade Panel ─────────────────────────────────────────────

function QuickTradePanel({
  symbol,
  assetClass,
}: {
  symbol: string;
  assetClass: string;
}) {
  const colors = getColors(assetClass);
  const [direction, setDirection] = useState<"buy" | "sell">("buy");
  const [exchange, setExchange] = useState("paper");
  const [quantity, setQuantity] = useState("1");
  const [stopLoss, setStopLoss] = useState("50");
  const [takeProfit, setTakeProfit] = useState("100");
  const [tradeStatus, setTradeStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const handleTrade = useCallback(async () => {
    try {
      setTradeStatus(null);
      // First validate
      const valRes = await apiRequest("GET", `/api/asset-trading/validate?symbol=${encodeURIComponent(symbol)}&direction=${direction}`);
      const validation = await valRes.json();

      if (!validation.allowed) {
        setTradeStatus({ type: "error", message: `Trade blocked: ${validation.warnings?.map((w: string | { message: string }) => typeof w === "string" ? w : w.message).join(", ") || "validation failed"}` });
        return;
      }

      // Then place order
      const orderRes = await apiRequest("POST", "/api/trading/execute", {
        symbol,
        side: direction,
        quantity: parseFloat(quantity),
        exchange,
        stop_loss: parseFloat(stopLoss) || undefined,
        take_profit: parseFloat(takeProfit) || undefined,
      });
      const order = await orderRes.json();
      setTradeStatus({ type: "success", message: `Order placed: ${order.order_id || "success"}` });
    } catch (err: unknown) {
      setTradeStatus({ type: "error", message: err instanceof Error ? err.message : "Trade failed" });
    }
  }, [symbol, direction, exchange, quantity, stopLoss, takeProfit]);

  return (
    <Card data-testid="quick-trade" className={`border ${colors.border} bg-card`}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Zap size={18} className="text-yellow-400" />
          Quick Trade
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3 items-end">
          {/* Direction */}
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Direction</label>
            <div className="flex gap-1">
              <Button
                data-testid="trade-buy"
                variant={direction === "buy" ? "default" : "outline"}
                size="sm"
                className={direction === "buy" ? "bg-green-600 hover:bg-green-700 flex-1" : "flex-1"}
                onClick={() => setDirection("buy")}
              >
                Buy
              </Button>
              <Button
                data-testid="trade-sell"
                variant={direction === "sell" ? "default" : "outline"}
                size="sm"
                className={direction === "sell" ? "bg-red-600 hover:bg-red-700 flex-1" : "flex-1"}
                onClick={() => setDirection("sell")}
              >
                Sell
              </Button>
            </div>
          </div>

          {/* Exchange */}
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Exchange</label>
            <Select value={exchange} onValueChange={setExchange}>
              <SelectTrigger data-testid="trade-exchange" className="h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="paper">Paper</SelectItem>
                <SelectItem value="ig">IG</SelectItem>
                <SelectItem value="capital">Capital.com</SelectItem>
                <SelectItem value="cmc">CMC</SelectItem>
                <SelectItem value="binance">Binance</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Quantity */}
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Quantity</label>
            <Input
              data-testid="trade-quantity"
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              className="h-8 text-xs"
              min="0"
              step="0.01"
            />
          </div>

          {/* Stop Loss */}
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Stop Loss</label>
            <Input
              data-testid="trade-stop-loss"
              type="number"
              value={stopLoss}
              onChange={(e) => setStopLoss(e.target.value)}
              className="h-8 text-xs"
              placeholder="pts"
            />
          </div>

          {/* Take Profit */}
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Take Profit</label>
            <Input
              data-testid="trade-take-profit"
              type="number"
              value={takeProfit}
              onChange={(e) => setTakeProfit(e.target.value)}
              className="h-8 text-xs"
              placeholder="pts"
            />
          </div>

          {/* Execute */}
          <div>
            <Button
              data-testid="trade-execute"
              onClick={handleTrade}
              className={`w-full h-8 text-xs ${direction === "buy" ? "bg-green-600 hover:bg-green-700" : "bg-red-600 hover:bg-red-700"}`}
            >
              Validate & Trade
            </Button>
          </div>
        </div>

        {tradeStatus && (
          <div data-testid="trade-status" className={`mt-3 text-xs px-3 py-2 rounded-md ${
            tradeStatus.type === "success" ? "bg-green-500/15 text-green-300" : "bg-red-500/15 text-red-300"
          }`}>
            {tradeStatus.type === "success" ? <CheckCircle2 size={12} className="inline mr-1" /> : <XCircle size={12} className="inline mr-1" />}
            {tradeStatus.message}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function SmartTrading() {
  const [inputSymbol, setInputSymbol] = useState("");
  const [activeSymbol, setActiveSymbol] = useState("BTC/USDT");
  const [regime, setRegime] = useState("trending_up");

  const analyzeSymbol = useCallback((sym?: string) => {
    const target = sym ?? inputSymbol.trim().toUpperCase();
    if (target) {
      setActiveSymbol(target);
      if (!sym) setInputSymbol("");
    }
  }, [inputSymbol]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter") analyzeSymbol();
  }, [analyzeSymbol]);

  // ── Queries ──────────────────────────────────────────────────────────────

  const { data: classify, isLoading: classifyLoading } = useQuery<ClassifyResult>({
    queryKey: ["/api/asset-trading/classify", activeSymbol],
    queryFn: async () => {
      const r = await apiRequest("GET", `/api/asset-trading/classify?symbol=${encodeURIComponent(activeSymbol)}`);
      return r.json();
    },
    refetchInterval: 30000,
  });

  const assetClass = classify?.asset_class ?? "crypto";
  const colors = useMemo(() => getColors(assetClass), [assetClass]);

  const { data: rules, isLoading: rulesLoading } = useQuery<RulesResult>({
    queryKey: ["/api/asset-trading/rules", activeSymbol, regime],
    queryFn: async () => {
      const r = await apiRequest("GET", `/api/asset-trading/rules?symbol=${encodeURIComponent(activeSymbol)}&regime=${regime}`);
      return r.json();
    },
    enabled: !!classify,
    refetchInterval: 30000,
  });

  const { data: sentiment, isLoading: sentimentLoading } = useQuery<SentimentResult>({
    queryKey: ["/api/asset-trading/sentiment", activeSymbol],
    queryFn: async () => {
      const r = await apiRequest("GET", `/api/asset-trading/sentiment?symbol=${encodeURIComponent(activeSymbol)}`);
      return r.json();
    },
    enabled: !!classify,
    refetchInterval: 15000,
  });

  const { data: buyValidation, isLoading: buyValLoading } = useQuery<ValidationResult>({
    queryKey: ["/api/asset-trading/validate", activeSymbol, "buy"],
    queryFn: async () => {
      const r = await apiRequest("GET", `/api/asset-trading/validate?symbol=${encodeURIComponent(activeSymbol)}&direction=buy`);
      return r.json();
    },
    enabled: !!classify,
    refetchInterval: 10000,
  });

  const { data: sellValidation, isLoading: sellValLoading } = useQuery<ValidationResult>({
    queryKey: ["/api/asset-trading/validate", activeSymbol, "sell"],
    queryFn: async () => {
      const r = await apiRequest("GET", `/api/asset-trading/validate?symbol=${encodeURIComponent(activeSymbol)}&direction=sell`);
      return r.json();
    },
    enabled: !!classify,
    refetchInterval: 10000,
  });

  const { data: strategiesData, isLoading: strategiesLoading } = useQuery<{ strategies: StrategyResult[] }>({
    queryKey: ["/api/asset-trading/strategies", activeSymbol, regime],
    queryFn: async () => {
      const r = await apiRequest("GET", `/api/asset-trading/strategies?symbol=${encodeURIComponent(activeSymbol)}&regime=${regime}`);
      return r.json();
    },
    enabled: !!classify,
    refetchInterval: 30000,
  });

  const { data: marketHours, isLoading: marketHoursLoading } = useQuery<MarketHoursResult>({
    queryKey: ["/api/spread-betting/market-hours", activeSymbol],
    queryFn: async () => {
      const r = await apiRequest("GET", `/api/spread-betting/market-hours/${encodeURIComponent(activeSymbol)}`);
      return r.json();
    },
    enabled: !!classify,
    refetchInterval: 30000,
  });

  const { data: spreadBet, isLoading: spreadBetLoading } = useQuery<SpreadBetResult>({
    queryKey: ["/api/spread-betting/evaluate", activeSymbol],
    queryFn: async () => {
      const r = await apiRequest("GET", `/api/spread-betting/evaluate?symbol=${encodeURIComponent(activeSymbol)}&direction=buy&account_balance=10000&risk_pct=1&stop_distance=50`);
      return r.json();
    },
    enabled: !!classify && ["forex", "forex_major", "forex_minor", "indices", "commodities", "metals"].includes(assetClass),
    refetchInterval: 30000,
  });

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div data-testid="smart-trading-page" className="p-4 md:p-6 space-y-4 max-w-[1400px] mx-auto">
      {/* ── Top Bar: Instrument Selector ── */}
      <Card data-testid="instrument-selector" className={`border ${colors.border} bg-card`}>
        <CardContent className="pt-4 pb-4">
          <div className="flex flex-col gap-3">
            {/* Search Row */}
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <Input
                  data-testid="symbol-input"
                  className="pl-9 h-10 text-base font-mono"
                  placeholder="Type any symbol — BTC/USDT, EUR/USD, AAPL, FTSE100, XAUUSD..."
                  value={inputSymbol}
                  onChange={(e) => setInputSymbol(e.target.value)}
                  onKeyDown={handleKeyDown}
                />
              </div>
              <Button
                data-testid="analyze-button"
                onClick={() => analyzeSymbol()}
                className="h-10 px-6"
              >
                <Search size={16} className="mr-2" /> Analyze
              </Button>
            </div>

            {/* Quick Select Chips + Classification */}
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-1.5">
                {QUICK_SYMBOLS.map((qs) => (
                  <Button
                    key={qs.symbol}
                    data-testid={`quick-${qs.symbol.replace(/\//g, "-").toLowerCase()}`}
                    variant={activeSymbol === qs.symbol ? "default" : "outline"}
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => analyzeSymbol(qs.symbol)}
                  >
                    {qs.label}
                  </Button>
                ))}
              </div>

              {/* Active Symbol + Classification Badges */}
              <div className="flex items-center gap-2">
                <span className="font-mono font-bold text-lg">{activeSymbol}</span>
                {classifyLoading ? (
                  <Skeleton className="h-5 w-20" />
                ) : classify ? (
                  <>
                    <Badge className={colors.badge}>{classify.asset_class}</Badge>
                    <Badge variant="outline" className="text-xs">{MARKET_TYPE_MAP[classify.asset_class] ?? "Market"}</Badge>
                  </>
                ) : null}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ── Sections ── */}
      {classifyLoading ? (
        <div className="space-y-4">
          <SectionSkeleton rows={4} />
          <SectionSkeleton rows={4} />
          <SectionSkeleton rows={3} />
        </div>
      ) : classify ? (
        <div className="space-y-4">
          {/* Section 1: Asset Intelligence */}
          {(rulesLoading || sentimentLoading) && !rules && !sentiment ? (
            <SectionSkeleton rows={5} />
          ) : (
            <AssetIntelligence classify={classify} rules={rules} sentiment={sentiment} />
          )}

          {/* Section 2: Trade Validation */}
          <TradeValidation
            symbol={activeSymbol}
            buyValidation={buyValidation}
            sellValidation={sellValidation}
            isLoading={buyValLoading && sellValLoading && !buyValidation && !sellValidation}
          />

          {/* Section 3: Optimal Strategies */}
          <OptimalStrategies
            strategies={strategiesData?.strategies}
            regime={regime}
            onRegimeChange={setRegime}
            isLoading={strategiesLoading && !strategiesData}
            assetClass={assetClass}
          />

          {/* Section 4: Market Status */}
          <MarketStatus
            marketHours={marketHours}
            isLoading={marketHoursLoading && !marketHours}
          />

          {/* Section 5: Spread Betting Panel */}
          <SpreadBetPanel
            spreadBet={spreadBet}
            isLoading={spreadBetLoading && !spreadBet}
            assetClass={assetClass}
          />

          {/* Section 6: Quick Trade Panel */}
          <QuickTradePanel symbol={activeSymbol} assetClass={assetClass} />
        </div>
      ) : (
        <Card className="border-card-border bg-card">
          <CardContent className="py-12 text-center">
            <Activity size={48} className="mx-auto mb-4 text-muted-foreground/50" />
            <h3 className="text-lg font-medium mb-2">Select an Instrument</h3>
            <p className="text-sm text-muted-foreground">
              Type any symbol above or use the quick-select chips to begin analysis
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
