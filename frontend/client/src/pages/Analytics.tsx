import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  RadialBarChart,
  RadialBar,
  AreaChart,
  Area,
} from "recharts";
import {
  Shield,
  Activity,
  TrendingUp,
  PieChart as PieChartIcon,
  BarChart3,
  Target,
  AlertTriangle,
  Gauge,
} from "lucide-react";

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

interface PerformanceData {
  total_return_pct: number;
  portfolio_value: number;
  initial_balance: number;
  total_trades: number;
  snapshots: { timestamp: string; total_value: number; cash_balance: number; positions_value: number }[];
}

const fmt = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
});

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

function RiskGauge({ value, max, label, color }: { value: number; max: number; label: string; color: string }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-20 h-20">
        <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
          <circle cx="50" cy="50" r="40" fill="none" stroke="hsl(0 0% 16%)" strokeWidth="8" />
          <circle
            cx="50"
            cy="50"
            r="40"
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeDasharray={`${pct * 2.51} 251`}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-sm font-mono font-semibold">{value.toFixed(1)}%</span>
        </div>
      </div>
      <span className="text-[10px] text-muted-foreground uppercase tracking-wider">{label}</span>
    </div>
  );
}

function MetricCard({
  label,
  value,
  icon: Icon,
  color,
  trend,
}: {
  label: string;
  value: string;
  icon: typeof Shield;
  color?: string;
  trend?: "good" | "bad" | "neutral";
}) {
  return (
    <Card className="border-card-border bg-card">
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{label}</p>
            <p
              className={`text-lg font-mono font-semibold ${
                trend === "good"
                  ? "text-[hsl(var(--profit))]"
                  : trend === "bad"
                  ? "text-[hsl(var(--loss))]"
                  : "text-foreground"
              }`}
            >
              {value}
            </p>
          </div>
          <div className="p-1.5 rounded-md bg-primary/10">
            <Icon size={14} className={color || "text-primary"} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function Analytics() {
  const { data: analytics, isLoading: analyticsLoading } = useQuery<AnalyticsData>({
    queryKey: ["/api/analytics/risk-metrics"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/analytics/risk-metrics");
      return res.json();
    },
    refetchInterval: 30000,
  });

  const { data: performance, isLoading: perfLoading } = useQuery<PerformanceData>({
    queryKey: ["/api/analytics/performance"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/analytics/performance");
      return res.json();
    },
    refetchInterval: 30000,
  });

  const isLoading = analyticsLoading || perfLoading;

  // Allocation data for pie chart
  const allocationData = (analytics?.allocation ?? [])
    .filter((a) => a.weight > 0 && a.symbol !== "CASH")
    .map((a, i) => ({
      name: a.symbol,
      value: a.value,
      weight: a.weight,
      fill: PIE_COLORS[i % PIE_COLORS.length],
    }));

  // Daily returns for bar chart
  const returnsData = (analytics?.daily_returns ?? []).map((r, i) => ({
    day: i + 1,
    return: r,
    fill: r >= 0 ? "hsl(142 72% 50%)" : "hsl(0 84% 55%)",
  }));

  // Snapshot data for area chart
  const snapshotData = (performance?.snapshots ?? []).map((s) => ({
    date: s.timestamp ? new Date(s.timestamp).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "",
    total: s.total_value,
    cash: s.cash_balance,
    positions: s.positions_value,
  }));

  // Risk level indicator
  const getRiskLevel = (vol: number) => {
    if (vol < 10) return { label: "Low", color: "text-[hsl(var(--profit))]", bg: "bg-[hsl(var(--profit))]/10" };
    if (vol < 25) return { label: "Medium", color: "text-amber-400", bg: "bg-amber-400/10" };
    return { label: "High", color: "text-[hsl(var(--loss))]", bg: "bg-[hsl(var(--loss))]/10" };
  };

  const riskLevel = getRiskLevel(analytics?.volatility ?? 0);

  return (
    <div className="space-y-4" data-testid="analytics-page">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Portfolio Analytics</h1>
        <Badge className={`${riskLevel.bg} ${riskLevel.color} border-0 text-xs`}>
          Risk: {riskLevel.label}
        </Badge>
      </div>

      {/* Top Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <MetricCard
          label="Total Return"
          value={`${performance?.total_return_pct?.toFixed(2) ?? "0"}%`}
          icon={TrendingUp}
          trend={(performance?.total_return_pct ?? 0) >= 0 ? "good" : "bad"}
        />
        <MetricCard
          label="Portfolio"
          value={fmt.format(analytics?.portfolio_value ?? 0)}
          icon={BarChart3}
        />
        <MetricCard
          label="Volatility"
          value={`${analytics?.volatility?.toFixed(1) ?? "0"}%`}
          icon={Activity}
          trend={(analytics?.volatility ?? 0) > 25 ? "bad" : "neutral"}
        />
        <MetricCard
          label="Max Drawdown"
          value={`${analytics?.max_drawdown?.toFixed(1) ?? "0"}%`}
          icon={AlertTriangle}
          trend={(analytics?.max_drawdown ?? 0) > 10 ? "bad" : "neutral"}
          color="text-[hsl(var(--loss))]"
        />
        <MetricCard
          label="VaR (95%)"
          value={fmt.format(analytics?.var_95 ?? 0)}
          icon={Shield}
        />
        <MetricCard
          label="Total Trades"
          value={(performance?.total_trades ?? 0).toString()}
          icon={Target}
        />
      </div>

      {/* Risk Gauges + Allocation */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Risk Gauges */}
        <Card className="border-card-border bg-card" data-testid="risk-gauges">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
              <Gauge size={14} />
              Risk Overview
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            {isLoading ? (
              <Skeleton className="h-[180px] w-full" />
            ) : (
              <div className="flex items-center justify-around py-4">
                <RiskGauge
                  value={analytics?.volatility ?? 0}
                  max={50}
                  label="Volatility"
                  color="hsl(168 80% 42%)"
                />
                <RiskGauge
                  value={analytics?.max_drawdown ?? 0}
                  max={30}
                  label="Drawdown"
                  color="hsl(0 84% 55%)"
                />
                <RiskGauge
                  value={analytics?.diversification_score ?? 0}
                  max={100}
                  label="Diversity"
                  color="hsl(262 83% 58%)"
                />
              </div>
            )}
          </CardContent>
        </Card>

        {/* Allocation Pie */}
        <Card className="border-card-border bg-card" data-testid="allocation-chart">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
              <PieChartIcon size={14} />
              Asset Allocation
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            {isLoading ? (
              <Skeleton className="h-[180px] w-full" />
            ) : allocationData.length > 0 ? (
              <div>
                <ResponsiveContainer width="100%" height={140}>
                  <PieChart>
                    <Pie
                      data={allocationData}
                      cx="50%"
                      cy="50%"
                      innerRadius={35}
                      outerRadius={55}
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
                <div className="space-y-1">
                  {allocationData.map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-1.5">
                        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: item.fill }} />
                        <span className="text-muted-foreground">{item.name}</span>
                      </div>
                      <span className="font-mono">{item.weight.toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="h-[180px] flex items-center justify-center text-muted-foreground text-sm">
                No positions to display
              </div>
            )}
          </CardContent>
        </Card>

        {/* Cash vs Invested */}
        <Card className="border-card-border bg-card" data-testid="cash-invested">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Cash vs Invested
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            {isLoading ? (
              <Skeleton className="h-[180px] w-full" />
            ) : (
              <div className="space-y-4 py-4">
                {(() => {
                  const total = analytics?.portfolio_value ?? 0;
                  const cash = analytics?.cash_balance ?? 0;
                  const invested = total - cash;
                  const cashPct = total > 0 ? (cash / total) * 100 : 100;
                  const investedPct = total > 0 ? (invested / total) * 100 : 0;

                  return (
                    <>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground">Cash</span>
                          <span className="font-mono">{fmt.format(cash)} ({cashPct.toFixed(1)}%)</span>
                        </div>
                        <div className="h-3 rounded-full bg-muted/30 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-primary transition-all"
                            style={{ width: `${cashPct}%` }}
                          />
                        </div>
                      </div>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground">Invested</span>
                          <span className="font-mono">{fmt.format(invested)} ({investedPct.toFixed(1)}%)</span>
                        </div>
                        <div className="h-3 rounded-full bg-muted/30 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-[hsl(262,83%,58%)] transition-all"
                            style={{ width: `${investedPct}%` }}
                          />
                        </div>
                      </div>
                      <div className="pt-2 border-t border-border">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground">Total</span>
                          <span className="font-mono font-medium">{fmt.format(total)}</span>
                        </div>
                      </div>
                    </>
                  );
                })()}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Returns + Portfolio History */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Daily Returns */}
        <Card className="border-card-border bg-card" data-testid="daily-returns-chart">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Daily Returns
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            {isLoading ? (
              <Skeleton className="h-[200px] w-full" />
            ) : returnsData.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={returnsData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(0 0% 16%)" />
                  <XAxis
                    dataKey="day"
                    tick={{ fontSize: 10, fill: "hsl(0 0% 55%)" }}
                    stroke="hsl(0 0% 16%)"
                  />
                  <YAxis
                    tick={{ fontSize: 10, fill: "hsl(0 0% 55%)" }}
                    stroke="hsl(0 0% 16%)"
                    tickFormatter={(v) => `${v.toFixed(1)}%`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(0 0% 12%)",
                      border: "1px solid hsl(0 0% 20%)",
                      borderRadius: "6px",
                      fontSize: "11px",
                    }}
                    formatter={(value: number) => [`${value.toFixed(2)}%`, "Return"]}
                  />
                  <Bar dataKey="return" radius={[2, 2, 0, 0]}>
                    {returnsData.map((entry, idx) => (
                      <Cell key={idx} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[200px] flex items-center justify-center text-muted-foreground text-sm">
                No return data available yet
              </div>
            )}
          </CardContent>
        </Card>

        {/* Portfolio History */}
        <Card className="border-card-border bg-card" data-testid="portfolio-history-chart">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Portfolio History
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            {isLoading ? (
              <Skeleton className="h-[200px] w-full" />
            ) : snapshotData.length > 1 ? (
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={snapshotData}>
                  <defs>
                    <linearGradient id="totalGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="hsl(168 80% 42%)" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="hsl(168 80% 42%)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(0 0% 16%)" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 10, fill: "hsl(0 0% 55%)" }}
                    stroke="hsl(0 0% 16%)"
                  />
                  <YAxis
                    tick={{ fontSize: 10, fill: "hsl(0 0% 55%)" }}
                    stroke="hsl(0 0% 16%)"
                    tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(0 0% 12%)",
                      border: "1px solid hsl(0 0% 20%)",
                      borderRadius: "6px",
                      fontSize: "11px",
                    }}
                    formatter={(value: number) => [fmt.format(value)]}
                  />
                  <Area
                    type="monotone"
                    dataKey="total"
                    stroke="hsl(168 80% 42%)"
                    strokeWidth={2}
                    fill="url(#totalGrad)"
                    name="Total"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[200px] flex items-center justify-center text-muted-foreground text-sm">
                Need more snapshots for history
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
