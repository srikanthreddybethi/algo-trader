import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { useLocation } from "wouter";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import {
  Wallet,
  DollarSign,
  TrendingUp,
  BarChart3,
  Shield,
  Activity,
  PieChart as PieChartIcon,
  Clock,
  Bot,
  Globe,
  RotateCcw,
  Brain,
  Cpu,
  Zap,
  CheckCircle2,
  XCircle,
  AlertTriangle,
} from "lucide-react";
import { format, isSameDay } from "date-fns";

// ── Formatters ───────────────────────────────────────────────────────────────

const fmt = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const fmtCrypto = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 8,
});

const fmtPct = new Intl.NumberFormat("en-US", {
  style: "percent",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  signDisplay: "always",
});

// ── Types ────────────────────────────────────────────────────────────────────

interface Position {
  id: number;
  symbol: string;
  exchange_name: string;
  side: string;
  quantity: number;
  avg_entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  realized_pnl: number;
  is_open: boolean;
}

interface Trade {
  id: number;
  symbol: string;
  exchange_name: string;
  side: string;
  quantity: number;
  price: number;
  fee: number;
  total_cost: number;
  executed_at: string;
}

interface Snapshot {
  id: number;
  total_value: number;
  cash_balance: number;
  timestamp: string;
}

interface PortfolioSummary {
  portfolio: {
    id: number;
    name: string;
    initial_balance: number;
    cash_balance: number;
    total_value: number;
    currency: string;
    is_paper: boolean;
  };
  positions: Position[];
  recent_snapshots: Snapshot[];
}

interface AnalyticsData {
  volatility: number;
  var_95: number;
  max_drawdown: number;
  diversification_score: number;
  position_count: number;
  allocation: { symbol: string; exchange: string; value: number; weight: number }[];
  daily_returns: number[];
  portfolio_value: number;
  cash_balance: number;
}

interface IntelligenceStatus {
  modules_active?: number;
  modules?: Record<string, unknown>;
  scoreboard?: Record<string, unknown>;
  memory?: Record<string, unknown>;
  [key: string]: unknown;
}

interface AdaptiveStatus {
  exit_levels?: Record<string, unknown>;
  active_symbols?: Record<string, unknown>;
  ai_accuracy?: { accuracy: number; trust_level: string; [key: string]: unknown };
  time_profile?: Record<string, unknown>;
  [key: string]: unknown;
}

interface Decision {
  type: string;
  symbol: string;
  result: string;
  timestamp: string;
  direction?: string;
  reason?: string;
  [key: string]: unknown;
}

// ── Constants ────────────────────────────────────────────────────────────────

const PIE_COLORS = [
  "hsl(168, 80%, 42%)",
  "hsl(262, 83%, 58%)",
  "hsl(45, 93%, 52%)",
  "hsl(0, 84%, 55%)",
  "hsl(210, 80%, 55%)",
  "hsl(320, 70%, 50%)",
  "hsl(180, 60%, 40%)",
  "hsl(30, 80%, 50%)",
];

// ── Sub-components ───────────────────────────────────────────────────────────

function KpiCard({
  title,
  value,
  icon: Icon,
  subtitle,
  trend,
  loading,
  testId,
}: {
  title: string;
  value: string;
  icon: typeof Wallet;
  subtitle?: string;
  trend?: "profit" | "loss" | "neutral";
  loading?: boolean;
  testId: string;
}) {
  return (
    <Card className="border-card-border bg-card" data-testid={testId}>
      <CardContent className="p-4">
        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-7 w-32" />
          </div>
        ) : (
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                {title}
              </p>
              <p
                className={`text-xl font-semibold font-mono tracking-tight ${
                  trend === "profit"
                    ? "text-[hsl(var(--profit))]"
                    : trend === "loss"
                    ? "text-[hsl(var(--loss))]"
                    : "text-foreground"
                }`}
              >
                {value}
              </p>
              {subtitle && (
                <p
                  className={`text-xs font-mono ${
                    trend === "profit"
                      ? "text-[hsl(var(--profit))]"
                      : trend === "loss"
                      ? "text-[hsl(var(--loss))]"
                      : "text-muted-foreground"
                  }`}
                >
                  {subtitle}
                </p>
              )}
            </div>
            <div className="p-2 rounded-md bg-primary/10">
              <Icon size={16} className="text-primary" />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function MiniRiskCard({
  label,
  value,
  unit,
  icon: Icon,
  color,
}: {
  label: string;
  value: string;
  unit?: string;
  icon: typeof Shield;
  color?: string;
}) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-md bg-muted/30 border border-border/50">
      <div className="p-1.5 rounded bg-primary/10">
        <Icon size={14} className={color || "text-primary"} />
      </div>
      <div>
        <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{label}</p>
        <p className="text-sm font-mono font-medium">
          {value}
          {unit && <span className="text-xs text-muted-foreground ml-0.5">{unit}</span>}
        </p>
      </div>
    </div>
  );
}

// ── Chart date formatting helper ─────────────────────────────────────────────

function formatChartData(snapshots: Snapshot[]) {
  if (snapshots.length === 0) return [];

  const dates = snapshots.map((s) => new Date(s.timestamp));
  // Check if all snapshots are from the same day
  const allSameDay = dates.length > 1 && dates.every((d) => isSameDay(d, dates[0]));
  // Check if data spans only 2 days
  const uniqueDays = new Set(dates.map((d) => format(d, "yyyy-MM-dd"))).size;
  const fewDays = uniqueDays <= 2;

  return snapshots.map((s) => {
    const d = new Date(s.timestamp);
    let dateLabel: string;
    if (allSameDay) {
      dateLabel = format(d, "HH:mm");
    } else if (fewDays) {
      dateLabel = format(d, "MMM dd HH:mm");
    } else {
      dateLabel = format(d, "MMM dd");
    }
    return { date: dateLabel, value: s.total_value, ts: d.getTime() };
  });
}

// ── Main Dashboard ───────────────────────────────────────────────────────────

export default function Dashboard() {
  const [, navigate] = useLocation();

  const { data, isLoading } = useQuery<PortfolioSummary>({
    queryKey: ["/api/portfolio/summary"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/portfolio/summary");
      return res.json();
    },
    refetchInterval: 10000,
  });

  const { data: trades, isLoading: tradesLoading } = useQuery<Trade[]>({
    queryKey: ["/api/trading/trades"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/trading/trades?limit=10");
      return res.json();
    },
    refetchInterval: 10000,
  });

  const { data: analytics } = useQuery<AnalyticsData>({
    queryKey: ["/api/analytics/risk-metrics"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/analytics/risk-metrics");
      return res.json();
    },
    refetchInterval: 30000,
  });

  const { data: intelStatus } = useQuery<IntelligenceStatus>({
    queryKey: ["/api/auto-trader/intelligence"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/auto-trader/intelligence");
      return res.json();
    },
    refetchInterval: 30000,
  });

  const { data: adaptiveStatus } = useQuery<AdaptiveStatus>({
    queryKey: ["/api/auto-trader/adaptive"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/auto-trader/adaptive");
      return res.json();
    },
    refetchInterval: 30000,
  });

  const { data: decisions } = useQuery<Decision[]>({
    queryKey: ["/api/auto-trader/decisions?limit=3"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/auto-trader/decisions?limit=3");
      return res.json();
    },
    refetchInterval: 15000,
  });

  const portfolio = data?.portfolio;
  const positions = data?.positions?.filter((p) => p.is_open) ?? [];
  const snapshots = data?.recent_snapshots ?? [];
  const recentTrades = trades ?? [];

  const totalValue = portfolio?.total_value ?? 0;
  const cashBalance = portfolio?.cash_balance ?? 0;
  const initialBalance = portfolio?.initial_balance ?? 10000;
  const totalPnl = totalValue - initialBalance;
  const totalPnlPct = initialBalance > 0 ? totalPnl / initialBalance : 0;

  // FIX #4: Smart chart date formatting
  const chartData = useMemo(() => formatChartData(snapshots), [snapshots]);

  // FIX #5: Filter out cash-only allocation for pie chart
  const allocationData = useMemo(() => {
    const raw = analytics?.allocation ?? [];
    const hasPositions = raw.some((a) => a.symbol !== "CASH" && a.weight > 0);
    if (!hasPositions) return []; // Don't show pie if only cash
    return raw
      .filter((a) => a.weight > 0)
      .map((a, i) => ({
        name: a.symbol,
        value: a.value,
        weight: a.weight,
        fill: PIE_COLORS[i % PIE_COLORS.length],
      }));
  }, [analytics?.allocation]);

  // Intelligence counts — handle actual API response shapes
  const intelModuleCount = intelStatus?.modules_active
    ?? (intelStatus?.modules ? Object.keys(intelStatus.modules).length : 0);
  const adaptiveModuleCount = adaptiveStatus
    ? Object.keys(adaptiveStatus).filter((k) => !k.startsWith("_")).length
    : 0;

  return (
    <div className="space-y-4" data-testid="dashboard-page">
      {/* Header + Quick Actions */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Dashboard</h1>
        <div className="flex items-center gap-2" data-testid="quick-actions">
          <Button
            data-testid="action-auto-trader"
            variant="outline"
            size="sm"
            className="h-8 text-xs"
            onClick={() => navigate("/auto-trader")}
          >
            <Bot size={14} className="mr-1.5" />
            Auto-Trader
          </Button>
          <Button
            data-testid="action-exchanges"
            variant="outline"
            size="sm"
            className="h-8 text-xs"
            onClick={() => navigate("/exchanges")}
          >
            <Globe size={14} className="mr-1.5" />
            Exchanges
          </Button>
          <Button
            data-testid="action-smart-trading"
            variant="outline"
            size="sm"
            className="h-8 text-xs"
            onClick={() => navigate("/smart-trading")}
          >
            <Zap size={14} className="mr-1.5" />
            Smart Trade
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiCard
          testId="kpi-portfolio-value"
          title="Portfolio Value"
          value={isLoading ? "—" : fmt.format(totalValue)}
          icon={Wallet}
          loading={isLoading}
        />
        <KpiCard
          testId="kpi-cash-balance"
          title="Cash Balance"
          value={isLoading ? "—" : fmt.format(cashBalance)}
          icon={DollarSign}
          loading={isLoading}
        />
        <KpiCard
          testId="kpi-total-pnl"
          title="Total P&L"
          value={isLoading ? "—" : fmt.format(totalPnl)}
          subtitle={isLoading ? undefined : fmtPct.format(totalPnlPct)}
          trend={totalPnl >= 0 ? "profit" : "loss"}
          icon={TrendingUp}
          loading={isLoading}
        />
        <KpiCard
          testId="kpi-open-positions"
          title="Open Positions"
          value={isLoading ? "—" : positions.length.toString()}
          icon={BarChart3}
          loading={isLoading}
        />
      </div>

      {/* Intelligence Status + Recent Decisions row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Active Intelligence Status */}
        <Card className="border-card-border bg-card" data-testid="intelligence-status">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
              <Brain size={14} />
              Intelligence Status
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-muted/30 rounded-md p-3">
                <div className="text-[10px] text-muted-foreground uppercase tracking-wider">Intelligence Modules</div>
                <div className="text-lg font-bold text-primary mt-0.5">{intelModuleCount || "—"}</div>
              </div>
              <div className="bg-muted/30 rounded-md p-3">
                <div className="text-[10px] text-muted-foreground uppercase tracking-wider">Adaptive Modules</div>
                <div className="text-lg font-bold text-purple-400 mt-0.5">{adaptiveModuleCount || "—"}</div>
              </div>
              <div className="bg-muted/30 rounded-md p-3">
                <div className="text-[10px] text-muted-foreground uppercase tracking-wider">AI Trust</div>
                <div className="text-sm font-semibold mt-0.5">
                  {adaptiveStatus?.ai_accuracy?.trust_level
                    ? String(adaptiveStatus.ai_accuracy.trust_level)
                    : "—"}
                </div>
              </div>
              <div className="bg-muted/30 rounded-md p-3">
                <div className="text-[10px] text-muted-foreground uppercase tracking-wider">Strategies Tracked</div>
                <div className="text-sm font-semibold mt-0.5">
                  {intelStatus?.scoreboard && typeof intelStatus.scoreboard === "object" && "strategies_tracked" in intelStatus.scoreboard
                    ? String(intelStatus.scoreboard.strategies_tracked)
                    : "—"}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Recent Decisions */}
        <Card className="border-card-border bg-card" data-testid="recent-decisions">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
              <Cpu size={14} />
              Recent Decisions
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            {!decisions || (Array.isArray(decisions) && decisions.length === 0) ? (
              <div className="flex items-center gap-2 py-6 justify-center text-sm text-muted-foreground">
                <Bot size={16} />
                Auto-Trader not running
              </div>
            ) : (
              <div className="space-y-2">
                {(Array.isArray(decisions) ? decisions : []).slice(0, 3).map((d, i) => (
                  <div key={i} className="flex items-center justify-between py-2 px-3 rounded-md bg-muted/20">
                    <div className="flex items-center gap-2">
                      {d.result === "executed" || d.result === "success" ? (
                        <CheckCircle2 size={14} className="text-green-400" />
                      ) : d.result === "skipped" || d.result === "filtered" ? (
                        <AlertTriangle size={14} className="text-amber-400" />
                      ) : (
                        <XCircle size={14} className="text-red-400" />
                      )}
                      <div>
                        <span className="text-xs font-medium">{d.symbol ?? "—"}</span>
                        <span className="text-[10px] text-muted-foreground ml-2">{d.type ?? "decision"}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <Badge variant="outline" className="text-[10px]">{d.result ?? "—"}</Badge>
                      {d.timestamp && (
                        <div className="text-[10px] text-muted-foreground mt-0.5">
                          {format(new Date(d.timestamp), "HH:mm:ss")}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Chart + Allocation */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Portfolio Chart */}
        <Card className="lg:col-span-2 border-card-border bg-card" data-testid="portfolio-chart">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Portfolio Value
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            {isLoading ? (
              <Skeleton className="h-[250px] w-full" />
            ) : chartData.length > 1 ? (
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="tealGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop
                        offset="0%"
                        stopColor="hsl(168 80% 42%)"
                        stopOpacity={0.3}
                      />
                      <stop
                        offset="100%"
                        stopColor="hsl(168 80% 42%)"
                        stopOpacity={0}
                      />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(0 0% 20%)" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11, fill: "hsl(0 0% 55%)" }}
                    stroke="hsl(0 0% 20%)"
                    interval="preserveStartEnd"
                    minTickGap={40}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: "hsl(0 0% 55%)" }}
                    stroke="hsl(0 0% 20%)"
                    tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`}
                    domain={["dataMin - 100", "dataMax + 100"]}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(0 0% 12%)",
                      border: "1px solid hsl(0 0% 20%)",
                      borderRadius: "6px",
                      fontSize: "12px",
                    }}
                    formatter={(value: number) => [fmt.format(value), "Value"]}
                  />
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke="hsl(168 80% 42%)"
                    strokeWidth={2}
                    fill="url(#tealGrad)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[250px] flex items-center justify-center text-muted-foreground text-sm">
                No portfolio history yet. Place some trades to see your chart.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Asset Allocation Pie */}
        <Card className="border-card-border bg-card" data-testid="asset-allocation">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
              <PieChartIcon size={14} />
              Asset Allocation
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            {allocationData.length > 0 ? (
              <div>
                <ResponsiveContainer width="100%" height={160}>
                  <PieChart>
                    <Pie
                      data={allocationData}
                      cx="50%"
                      cy="50%"
                      innerRadius={40}
                      outerRadius={65}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {allocationData.map((entry, idx) => (
                        <Cell key={idx} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "hsl(0 0% 12%)",
                        border: "1px solid hsl(0 0% 20%)",
                        borderRadius: "6px",
                        fontSize: "11px",
                      }}
                      formatter={(value: number, _: any, props: any) => [
                        `${fmt.format(value)} (${props.payload.weight.toFixed(1)}%)`,
                        props.payload.name,
                      ]}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-1 mt-1">
                  {allocationData.map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-1.5">
                        <div
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: item.fill }}
                        />
                        <span className="text-muted-foreground">{item.name}</span>
                      </div>
                      <span className="font-mono">{item.weight.toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="h-[250px] flex flex-col items-center justify-center text-muted-foreground">
                <Wallet size={32} className="mb-2 opacity-30" />
                <p className="text-sm font-medium">100% Cash</p>
                <p className="text-xs mt-1">Open positions to see allocation</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Risk Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <MiniRiskCard
          label="Volatility"
          value={analytics?.volatility?.toFixed(1) ?? "0"}
          unit="%"
          icon={Activity}
        />
        <MiniRiskCard
          label="Max Drawdown"
          value={analytics?.max_drawdown?.toFixed(1) ?? "0"}
          unit="%"
          icon={TrendingUp}
          color="text-[hsl(var(--loss))]"
        />
        <MiniRiskCard
          label="VaR (95%)"
          value={analytics?.var_95 ? fmt.format(analytics.var_95) : "$0"}
          icon={Shield}
        />
        <MiniRiskCard
          label="Diversification"
          value={positions.length > 0 ? (analytics?.diversification_score?.toString() ?? "0") : "—"}
          unit={positions.length > 0 ? "/100" : ""}
          icon={PieChartIcon}
        />
      </div>

      {/* Recent Trades + Active Positions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Recent Trades */}
        <Card className="border-card-border bg-card" data-testid="recent-trades">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
              <Clock size={14} />
              Recent Trades
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            {tradesLoading || isLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-8 w-full" />
                ))}
              </div>
            ) : recentTrades.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">
                No trades yet
              </p>
            ) : (
              <div className="space-y-1.5 max-h-[280px] overflow-y-auto">
                {recentTrades.slice(0, 10).map((trade, idx) => (
                  <div
                    key={trade.id ?? idx}
                    data-testid={`recent-trade-${trade.id ?? idx}`}
                    className="flex items-center justify-between py-1.5 px-2 rounded-md hover:bg-muted/30 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <Badge
                        variant="outline"
                        className={`text-[10px] px-1.5 py-0 font-mono uppercase ${
                          trade.side === "buy"
                            ? "text-[hsl(var(--profit))] border-[hsl(var(--profit))]/30"
                            : "text-[hsl(var(--loss))] border-[hsl(var(--loss))]/30"
                        }`}
                      >
                        {trade.side}
                      </Badge>
                      <span className="text-xs font-medium">
                        {trade.symbol}
                      </span>
                    </div>
                    <span className="text-xs font-mono text-muted-foreground">
                      {fmt.format(trade.price)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Active Positions Table */}
        <Card className="lg:col-span-2 border-card-border bg-card" data-testid="positions-table">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Active Positions
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {isLoading ? (
              <div className="p-4 space-y-2">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : positions.length === 0 ? (
              <p className="text-sm text-muted-foreground p-6 text-center">
                No open positions
              </p>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="hover:bg-transparent border-border">
                      <TableHead className="text-xs text-muted-foreground font-medium">
                        Symbol
                      </TableHead>
                      <TableHead className="text-xs text-muted-foreground font-medium">
                        Exchange
                      </TableHead>
                      <TableHead className="text-xs text-muted-foreground font-medium text-right">
                        Qty
                      </TableHead>
                      <TableHead className="text-xs text-muted-foreground font-medium text-right">
                        Entry
                      </TableHead>
                      <TableHead className="text-xs text-muted-foreground font-medium text-right">
                        Current
                      </TableHead>
                      <TableHead className="text-xs text-muted-foreground font-medium text-right">
                        P&L
                      </TableHead>
                      <TableHead className="text-xs text-muted-foreground font-medium text-right">
                        P&L %
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {positions.map((pos) => {
                      const pnl = pos.unrealized_pnl ?? 0;
                      const pnlPct = pos.unrealized_pnl_pct ?? 0;
                      const isProfitable = pnl >= 0;
                      return (
                        <TableRow
                          key={pos.id}
                          data-testid={`position-${pos.id}`}
                          className="border-border hover:bg-muted/30"
                        >
                          <TableCell className="text-sm font-medium">
                            {pos.symbol}
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground">
                            {pos.exchange_name}
                          </TableCell>
                          <TableCell className="text-right font-mono text-sm">
                            {fmtCrypto.format(pos.quantity)}
                          </TableCell>
                          <TableCell className="text-right font-mono text-sm">
                            {fmt.format(pos.avg_entry_price)}
                          </TableCell>
                          <TableCell className="text-right font-mono text-sm">
                            {fmt.format(pos.current_price)}
                          </TableCell>
                          <TableCell
                            className={`text-right font-mono text-sm ${
                              isProfitable
                                ? "text-[hsl(var(--profit))]"
                                : "text-[hsl(var(--loss))]"
                            }`}
                          >
                            {fmt.format(pnl)}
                          </TableCell>
                          <TableCell
                            className={`text-right font-mono text-sm ${
                              isProfitable
                                ? "text-[hsl(var(--profit))]"
                                : "text-[hsl(var(--loss))]"
                            }`}
                          >
                            {fmtPct.format(pnlPct / 100)}
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
    </div>
  );
}
