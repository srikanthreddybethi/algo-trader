import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import {
  Card, CardContent, CardHeader, CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar, Cell, ReferenceLine,
  ComposedChart, Scatter,
} from "recharts";
import {
  Play, TrendingUp, TrendingDown, BarChart3, Target, Trophy,
  AlertTriangle, ArrowUp, ArrowDown, Loader2, Percent,
} from "lucide-react";
import { format } from "date-fns";

const fmt = new Intl.NumberFormat("en-US", {
  style: "currency", currency: "USD",
  minimumFractionDigits: 2, maximumFractionDigits: 2,
});

const fmtPct = (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;

interface StrategyInfo {
  name: string;
  description: string;
  category: string;
  params: Array<{
    name: string; label: string; type: string;
    default: number; min?: number; max?: number;
    step?: number; options?: string[];
  }>;
}

interface BacktestResult {
  strategy: string;
  strategy_info: StrategyInfo;
  symbol: string;
  exchange: string;
  timeframe: string;
  days: number;
  params: Record<string, number>;
  metrics: Record<string, number>;
  equity_curve: Array<{ timestamp: string; equity: number; drawdown: number }>;
  trades: Array<{
    entry_time: string; exit_time: string; side: string;
    entry_price: number; exit_price: number; quantity: number;
    pnl: number; pnl_pct: number; fee: number;
  }>;
  trade_markers: Array<{
    timestamp: string; side: string; price: number; quantity: number;
  }>;
  total_candles: number;
}

const SYMBOLS = [
  "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT",
  "XRP/USDT", "ADA/USDT", "DOGE/USDT", "DOT/USDT",
  "AVAX/USDT", "LINK/USDT",
];
const TIMEFRAMES = ["1h", "4h", "1d"];
const EXCHANGES = ["binance", "bybit", "kraken", "coinbase"];

function MetricCard({
  label, value, subtext, icon: Icon, trend, testId,
}: {
  label: string; value: string; subtext?: string;
  icon: typeof TrendingUp; trend?: "profit" | "loss" | "neutral";
  testId: string;
}) {
  return (
    <Card className="border-card-border bg-card" data-testid={testId}>
      <CardContent className="p-3">
        <div className="flex items-start justify-between">
          <div className="space-y-0.5">
            <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
              {label}
            </p>
            <p className={`text-base font-semibold font-mono ${
              trend === "profit" ? "text-[hsl(var(--profit))]"
              : trend === "loss" ? "text-[hsl(var(--loss))]"
              : "text-foreground"
            }`}>
              {value}
            </p>
            {subtext && (
              <p className="text-[10px] text-muted-foreground font-mono">{subtext}</p>
            )}
          </div>
          <div className="p-1.5 rounded-md bg-primary/10">
            <Icon size={12} className="text-primary" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function EquityChart({ data }: { data: BacktestResult["equity_curve"] }) {
  const chartData = data.map((d) => ({
    date: d.timestamp ? format(new Date(d.timestamp), "MMM dd") : "",
    equity: d.equity,
    drawdown: d.drawdown,
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={chartData}>
        <defs>
          <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="hsl(168 80% 42%)" stopOpacity={0.3} />
            <stop offset="100%" stopColor="hsl(168 80% 42%)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(0 0% 20%)" />
        <XAxis dataKey="date" tick={{ fontSize: 10, fill: "hsl(0 0% 55%)" }} stroke="hsl(0 0% 20%)" />
        <YAxis tick={{ fontSize: 10, fill: "hsl(0 0% 55%)" }} stroke="hsl(0 0% 20%)"
          tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`} />
        <Tooltip
          contentStyle={{ backgroundColor: "hsl(0 0% 12%)", border: "1px solid hsl(0 0% 20%)", borderRadius: "6px", fontSize: "11px" }}
          formatter={(value: number) => [fmt.format(value), "Equity"]}
        />
        <Area type="monotone" dataKey="equity" stroke="hsl(168 80% 42%)" strokeWidth={2} fill="url(#eqGrad)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function DrawdownChart({ data }: { data: BacktestResult["equity_curve"] }) {
  const chartData = data.map((d) => ({
    date: d.timestamp ? format(new Date(d.timestamp), "MMM dd") : "",
    drawdown: d.drawdown,
  }));

  return (
    <ResponsiveContainer width="100%" height={160}>
      <AreaChart data={chartData}>
        <defs>
          <linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="hsl(0 70% 50%)" stopOpacity={0.3} />
            <stop offset="100%" stopColor="hsl(0 70% 50%)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(0 0% 20%)" />
        <XAxis dataKey="date" tick={{ fontSize: 10, fill: "hsl(0 0% 55%)" }} stroke="hsl(0 0% 20%)" />
        <YAxis tick={{ fontSize: 10, fill: "hsl(0 0% 55%)" }} stroke="hsl(0 0% 20%)"
          tickFormatter={(v) => `${v.toFixed(1)}%`} />
        <Tooltip
          contentStyle={{ backgroundColor: "hsl(0 0% 12%)", border: "1px solid hsl(0 0% 20%)", borderRadius: "6px", fontSize: "11px" }}
          formatter={(value: number) => [`${value.toFixed(2)}%`, "Drawdown"]}
        />
        <ReferenceLine y={0} stroke="hsl(0 0% 30%)" />
        <Area type="monotone" dataKey="drawdown" stroke="hsl(0 70% 50%)" strokeWidth={1.5} fill="url(#ddGrad)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function TradesTable({ trades }: { trades: BacktestResult["trades"] }) {
  if (!trades.length) {
    return <p className="text-sm text-muted-foreground p-6 text-center">No trades</p>;
  }
  return (
    <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent border-border">
            <TableHead className="text-xs text-muted-foreground font-medium">Entry</TableHead>
            <TableHead className="text-xs text-muted-foreground font-medium">Exit</TableHead>
            <TableHead className="text-xs text-muted-foreground font-medium text-right">Entry Price</TableHead>
            <TableHead className="text-xs text-muted-foreground font-medium text-right">Exit Price</TableHead>
            <TableHead className="text-xs text-muted-foreground font-medium text-right">Qty</TableHead>
            <TableHead className="text-xs text-muted-foreground font-medium text-right">P&L</TableHead>
            <TableHead className="text-xs text-muted-foreground font-medium text-right">P&L %</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {trades.map((t, i) => {
            const isProfit = t.pnl >= 0;
            return (
              <TableRow key={i} className="border-border hover:bg-muted/30" data-testid={`bt-trade-${i}`}>
                <TableCell className="text-xs font-mono text-muted-foreground">
                  {t.entry_time ? format(new Date(t.entry_time), "MMM dd HH:mm") : "—"}
                </TableCell>
                <TableCell className="text-xs font-mono text-muted-foreground">
                  {t.exit_time ? format(new Date(t.exit_time), "MMM dd HH:mm") : "—"}
                </TableCell>
                <TableCell className="text-right font-mono text-sm">{fmt.format(t.entry_price)}</TableCell>
                <TableCell className="text-right font-mono text-sm">{fmt.format(t.exit_price)}</TableCell>
                <TableCell className="text-right font-mono text-xs">{t.quantity.toFixed(6)}</TableCell>
                <TableCell className={`text-right font-mono text-sm ${isProfit ? "text-[hsl(var(--profit))]" : "text-[hsl(var(--loss))]"}`}>
                  {fmt.format(t.pnl)}
                </TableCell>
                <TableCell className={`text-right font-mono text-sm ${isProfit ? "text-[hsl(var(--profit))]" : "text-[hsl(var(--loss))]"}`}>
                  {fmtPct(t.pnl_pct)}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

function PnlDistribution({ trades }: { trades: BacktestResult["trades"] }) {
  if (!trades.length) return null;
  const data = trades.map((t, i) => ({ name: `#${i + 1}`, pnl: t.pnl }));
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(0 0% 20%)" />
        <XAxis dataKey="name" tick={{ fontSize: 9, fill: "hsl(0 0% 55%)" }} stroke="hsl(0 0% 20%)" />
        <YAxis tick={{ fontSize: 10, fill: "hsl(0 0% 55%)" }} stroke="hsl(0 0% 20%)"
          tickFormatter={(v) => `$${v}`} />
        <Tooltip
          contentStyle={{ backgroundColor: "hsl(0 0% 12%)", border: "1px solid hsl(0 0% 20%)", borderRadius: "6px", fontSize: "11px" }}
          formatter={(value: number) => [fmt.format(value), "P&L"]}
        />
        <ReferenceLine y={0} stroke="hsl(0 0% 40%)" />
        <Bar dataKey="pnl" radius={[2, 2, 0, 0]}>
          {data.map((entry, index) => (
            <Cell key={index} fill={entry.pnl >= 0 ? "hsl(142 71% 45%)" : "hsl(0 70% 50%)"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export default function Backtesting() {
  const [selectedStrategy, setSelectedStrategy] = useState("sma_crossover");
  const [symbol, setSymbol] = useState("BTC/USDT");
  const [exchange, setExchange] = useState("binance");
  const [timeframe, setTimeframe] = useState("1h");
  const [days, setDays] = useState(90);
  const [balance, setBalance] = useState(10000);
  const [positionSize, setPositionSize] = useState(10);
  const [strategyParams, setStrategyParams] = useState<Record<string, number>>({});

  const { data: strategies, isLoading: strategiesLoading } = useQuery<StrategyInfo[]>({
    queryKey: ["/api/backtest/strategies"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/backtest/strategies");
      return res.json();
    },
  });

  const currentStrategy = strategies?.find((s) =>
    s.name.toLowerCase().replace(/ /g, "_") === selectedStrategy ||
    Object.entries({
      sma_crossover: "SMA Crossover", ema_crossover: "EMA Crossover",
      rsi: "RSI", macd: "MACD", bollinger_bands: "Bollinger Bands",
      mean_reversion: "Mean Reversion", momentum: "Momentum",
      vwap: "VWAP", dca: "Dollar Cost Averaging", grid_trading: "Grid Trading",
    }).find(([k]) => k === selectedStrategy)?.[1] === s.name
  );

  const backtest = useMutation({
    mutationFn: async () => {
      const params: Record<string, number> = {};
      if (currentStrategy) {
        currentStrategy.params.forEach((p) => {
          params[p.name] = strategyParams[p.name] ?? p.default;
        });
      }
      const res = await apiRequest("POST", "/api/backtest/run", {
        strategy: selectedStrategy,
        symbol, exchange, timeframe, days,
        initial_balance: balance,
        params,
        position_size_pct: positionSize,
      });
      return res.json() as Promise<BacktestResult>;
    },
  });

  const result = backtest.data;
  const m = result?.metrics;

  return (
    <div className="space-y-4" data-testid="backtesting-page">
      <h1 className="text-xl font-semibold">Backtesting</h1>

      {/* Configuration Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <Card className="border-card-border bg-card lg:col-span-1" data-testid="bt-config">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 p-4 pt-0">
            {/* Strategy */}
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Strategy</Label>
              <Select value={selectedStrategy} onValueChange={(v) => {
                setSelectedStrategy(v);
                setStrategyParams({});
              }}>
                <SelectTrigger className="h-8 text-xs" data-testid="bt-strategy-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {strategiesLoading ? (
                    <SelectItem value="_loading">Loading...</SelectItem>
                  ) : (
                    (strategies ?? []).map((s) => {
                      const key = Object.entries({
                        "SMA Crossover": "sma_crossover", "EMA Crossover": "ema_crossover",
                        "RSI": "rsi", "MACD": "macd", "Bollinger Bands": "bollinger_bands",
                        "Mean Reversion": "mean_reversion", "Momentum": "momentum",
                        "VWAP": "vwap", "Dollar Cost Averaging": "dca", "Grid Trading": "grid_trading",
                      }).find(([k]) => k === s.name)?.[1] ?? s.name.toLowerCase().replace(/ /g, "_");
                      return (
                        <SelectItem key={key} value={key}>
                          <span className="text-xs">{s.name}</span>
                          <Badge variant="outline" className="ml-2 text-[9px] py-0">{s.category}</Badge>
                        </SelectItem>
                      );
                    })
                  )}
                </SelectContent>
              </Select>
              {currentStrategy && (
                <p className="text-[10px] text-muted-foreground">{currentStrategy.description}</p>
              )}
            </div>

            {/* Symbol */}
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Symbol</Label>
              <Select value={symbol} onValueChange={setSymbol}>
                <SelectTrigger className="h-8 text-xs" data-testid="bt-symbol-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SYMBOLS.map((s) => (
                    <SelectItem key={s} value={s}>{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Exchange + Timeframe row */}
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Exchange</Label>
                <Select value={exchange} onValueChange={setExchange}>
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {EXCHANGES.map((e) => (
                      <SelectItem key={e} value={e} className="capitalize">{e}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Timeframe</Label>
                <Select value={timeframe} onValueChange={setTimeframe}>
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TIMEFRAMES.map((t) => (
                      <SelectItem key={t} value={t}>{t}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Days + Balance */}
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Period (days)</Label>
                <Input type="number" value={days} onChange={(e) => setDays(Number(e.target.value))}
                  className="h-8 text-xs" min={7} max={365} data-testid="bt-days" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Balance ($)</Label>
                <Input type="number" value={balance} onChange={(e) => setBalance(Number(e.target.value))}
                  className="h-8 text-xs" min={100} data-testid="bt-balance" />
              </div>
            </div>

            {/* Position size */}
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Position Size (%)</Label>
              <Input type="number" value={positionSize} onChange={(e) => setPositionSize(Number(e.target.value))}
                className="h-8 text-xs" min={1} max={100} step={5} data-testid="bt-position-size" />
            </div>

            {/* Strategy params */}
            {currentStrategy?.params && currentStrategy.params.length > 0 && (
              <div className="space-y-2 pt-1 border-t border-border">
                <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider pt-1">
                  Strategy Parameters
                </p>
                {currentStrategy.params.map((p) => (
                  <div key={p.name} className="space-y-1">
                    <Label className="text-xs text-muted-foreground">{p.label}</Label>
                    <Input
                      type="number"
                      value={strategyParams[p.name] ?? p.default}
                      onChange={(e) => setStrategyParams((prev) => ({
                        ...prev, [p.name]: Number(e.target.value),
                      }))}
                      className="h-8 text-xs"
                      min={p.min ?? undefined}
                      max={p.max ?? undefined}
                      step={p.step ?? 1}
                      data-testid={`bt-param-${p.name}`}
                    />
                  </div>
                ))}
              </div>
            )}

            {/* Run button */}
            <Button
              onClick={() => backtest.mutate()}
              disabled={backtest.isPending}
              className="w-full h-9 text-sm font-medium"
              data-testid="bt-run"
            >
              {backtest.isPending ? (
                <><Loader2 size={14} className="mr-2 animate-spin" /> Running...</>
              ) : (
                <><Play size={14} className="mr-2" /> Run Backtest</>
              )}
            </Button>

            {backtest.isError && (
              <p className="text-xs text-[hsl(var(--loss))]">
                Error: {(backtest.error as Error).message}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Results Panel */}
        <div className="lg:col-span-3 space-y-4">
          {!result && !backtest.isPending && (
            <Card className="border-card-border bg-card">
              <CardContent className="p-12 text-center">
                <BarChart3 size={40} className="mx-auto mb-3 text-muted-foreground/40" />
                <p className="text-sm text-muted-foreground">
                  Configure a strategy and click "Run Backtest" to see results
                </p>
              </CardContent>
            </Card>
          )}

          {backtest.isPending && (
            <Card className="border-card-border bg-card">
              <CardContent className="p-8 space-y-3">
                <Skeleton className="h-8 w-48" />
                <Skeleton className="h-[200px] w-full" />
                <div className="grid grid-cols-4 gap-3">
                  {Array.from({ length: 8 }).map((_, i) => (
                    <Skeleton key={i} className="h-16" />
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {result && m && (
            <>
              {/* Metrics Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <MetricCard testId="metric-return" label="Total Return" value={fmtPct(m.total_return_pct)}
                  subtext={fmt.format(m.net_profit)} icon={TrendingUp}
                  trend={m.total_return_pct >= 0 ? "profit" : "loss"} />
                <MetricCard testId="metric-sharpe" label="Sharpe Ratio" value={m.sharpe_ratio.toFixed(2)}
                  icon={Target} trend={m.sharpe_ratio >= 1 ? "profit" : m.sharpe_ratio >= 0 ? "neutral" : "loss"} />
                <MetricCard testId="metric-drawdown" label="Max Drawdown" value={fmtPct(m.max_drawdown)}
                  icon={AlertTriangle} trend="loss" />
                <MetricCard testId="metric-winrate" label="Win Rate" value={`${m.win_rate.toFixed(1)}%`}
                  subtext={`${m.winning_trades}W / ${m.losing_trades}L`} icon={Trophy}
                  trend={m.win_rate >= 50 ? "profit" : "loss"} />
                <MetricCard testId="metric-trades" label="Total Trades" value={m.total_trades.toString()}
                  icon={BarChart3} />
                <MetricCard testId="metric-sortino" label="Sortino Ratio" value={m.sortino_ratio.toFixed(2)}
                  icon={Percent} trend={m.sortino_ratio >= 1 ? "profit" : "neutral"} />
                <MetricCard testId="metric-pf" label="Profit Factor" value={m.profit_factor.toFixed(2)}
                  icon={ArrowUp} trend={m.profit_factor >= 1 ? "profit" : "loss"} />
                <MetricCard testId="metric-calmar" label="Calmar Ratio" value={m.calmar_ratio.toFixed(2)}
                  icon={ArrowDown} trend={m.calmar_ratio >= 1 ? "profit" : "neutral"} />
              </div>

              {/* Charts */}
              <Card className="border-card-border bg-card" data-testid="bt-equity-chart">
                <CardHeader className="pb-1">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Equity Curve — {result.strategy_info.name} on {result.symbol}
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-4 pt-0">
                  <EquityChart data={result.equity_curve} />
                </CardContent>
              </Card>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <Card className="border-card-border bg-card" data-testid="bt-drawdown-chart">
                  <CardHeader className="pb-1">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      Drawdown
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-4 pt-0">
                    <DrawdownChart data={result.equity_curve} />
                  </CardContent>
                </Card>
                <Card className="border-card-border bg-card" data-testid="bt-pnl-chart">
                  <CardHeader className="pb-1">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      Trade P&L Distribution
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-4 pt-0">
                    <PnlDistribution trades={result.trades} />
                  </CardContent>
                </Card>
              </div>

              {/* Trades table */}
              <Card className="border-card-border bg-card" data-testid="bt-trades-table">
                <CardHeader className="pb-1">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Trade Log ({result.trades.length} trades)
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <TradesTable trades={result.trades} />
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
