import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, PieChart, Pie, RadialBarChart, RadialBar,
} from "recharts";
import {
  Cpu, Loader2, Trophy, Target, BookOpen, Sparkles,
  CheckCircle2, Zap, BarChart3, Brain, Clock, TrendingUp,
  Activity, Shield, Gauge, Database,
} from "lucide-react";

const RANK_COLORS = [
  "hsl(45, 93%, 52%)", "hsl(0, 0%, 75%)", "hsl(25, 70%, 45%)",
  "hsl(168, 80%, 42%)", "hsl(262, 83%, 58%)", "hsl(210, 80%, 55%)",
  "hsl(0, 84%, 55%)", "hsl(320, 70%, 50%)",
];

function PriorityBadge({ priority }: { priority: string }) {
  const colors: Record<string, string> = {
    high: "bg-[hsl(var(--loss))]/10 text-[hsl(var(--loss))]",
    medium: "bg-amber-500/10 text-amber-400",
    low: "bg-primary/10 text-primary",
  };
  return <Badge variant="outline" className={`text-[9px] px-1.5 py-0 ${colors[priority] || colors.low} border-0`}>{priority}</Badge>;
}

export default function Optimizer() {
  const { toast } = useToast();

  const { data: optHistory } = useQuery<any[]>({
    queryKey: ["/api/optimizer/history"],
    queryFn: async () => { const r = await apiRequest("GET", "/api/optimizer/history?limit=5"); return r.json(); },
    refetchInterval: 10000,
  });
  const { data: improvHistory } = useQuery<any[]>({
    queryKey: ["/api/optimizer/improve/history"],
    queryFn: async () => { const r = await apiRequest("GET", "/api/optimizer/improve/history?limit=5"); return r.json(); },
    refetchInterval: 10000,
  });
  const { data: journalHistory } = useQuery<any[]>({
    queryKey: ["/api/optimizer/journal/history"],
    queryFn: async () => { const r = await apiRequest("GET", "/api/optimizer/journal/history?limit=3"); return r.json(); },
    refetchInterval: 10000,
  });
  const { data: decisions } = useQuery<any[]>({
    queryKey: ["/api/auto-trader/decisions"],
    queryFn: async () => { const r = await apiRequest("GET", "/api/auto-trader/decisions?limit=100"); return r.json(); },
    refetchInterval: 10000,
  });
  const { data: adaptiveData } = useQuery<any>({
    queryKey: ["/api/auto-trader/adaptive"],
    queryFn: async () => { const r = await apiRequest("GET", "/api/auto-trader/adaptive"); return r.json(); },
    refetchInterval: 10000,
  });

  const runFullCycle = useMutation({
    mutationFn: async () => { const r = await apiRequest("POST", "/api/optimizer/full-cycle?symbols=BTC/USDT&days=30"); return r.json(); },
    onSuccess: (d) => { toast({ title: "Optimization complete", description: `${d.optimization.total_backtests} backtests` }); queryClient.invalidateQueries({ queryKey: ["/api/optimizer/history"] }); },
  });
  const runImprove = useMutation({
    mutationFn: async () => { const r = await apiRequest("POST", "/api/optimizer/improve?symbol=BTC/USDT&days=30"); return r.json(); },
    onSuccess: () => { toast({ title: "Improvement complete" }); queryClient.invalidateQueries({ queryKey: ["/api/optimizer/improve/history"] }); },
  });
  const runJournal = useMutation({
    mutationFn: async () => { const r = await apiRequest("POST", "/api/optimizer/journal?days=7"); return r.json(); },
    onSuccess: () => { toast({ title: "Journal analyzed" }); queryClient.invalidateQueries({ queryKey: ["/api/optimizer/journal/history"] }); },
  });

  const latestOpt = optHistory?.[0];
  const latestImprov = improvHistory?.[0];
  const latestJournal = journalHistory?.[0];
  const ranking = latestOpt?.overall_ranking ?? latestImprov?.ranking ?? [];

  // Chart data
  const scoreChart = ranking.slice(0, 8).map((r: any, i: number) => ({
    name: r.strategy?.length > 10 ? r.strategy.slice(0, 10) + "…" : r.strategy,
    score: r.score || r.blended_score || 0,
    fill: RANK_COLORS[i % RANK_COLORS.length],
  }));

  // Decision distribution pie
  const decisionTypes: Record<string, number> = {};
  (decisions ?? []).forEach((d: any) => { decisionTypes[d.type] = (decisionTypes[d.type] || 0) + 1; });
  const decisionPie = Object.entries(decisionTypes)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([type, count], i) => ({
      name: type.replaceAll("_", " "),
      value: count,
      fill: RANK_COLORS[i % RANK_COLORS.length],
    }));

  // AI accuracy gauge
  const aiAccuracy = (adaptiveData?.ai_accuracy?.accuracy ?? 0.5) * 100;
  const aiGauge = [{ name: "accuracy", value: aiAccuracy, fill: aiAccuracy >= 60 ? "hsl(142 72% 50%)" : aiAccuracy >= 45 ? "hsl(45 93% 52%)" : "hsl(0 84% 55%)" }];

  return (
    <div className="space-y-4" data-testid="optimizer-page">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-semibold">Self-Optimizer</h1>
          <Badge variant="outline" className="text-[10px] px-1.5 py-0 font-mono"><Cpu size={10} className="mr-1" /> autonomous</Badge>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="h-8 text-xs" onClick={() => runJournal.mutate()} disabled={runJournal.isPending}>
            {runJournal.isPending ? <Loader2 size={14} className="mr-1 animate-spin" /> : <BookOpen size={14} className="mr-1" />} Journal
          </Button>
          <Button variant="outline" size="sm" className="h-8 text-xs" onClick={() => runImprove.mutate()} disabled={runImprove.isPending}>
            {runImprove.isPending ? <Loader2 size={14} className="mr-1 animate-spin" /> : <TrendingUp size={14} className="mr-1" />} Improve
          </Button>
          <Button size="sm" className="h-8 text-xs" onClick={() => runFullCycle.mutate()} disabled={runFullCycle.isPending}>
            {runFullCycle.isPending ? <Loader2 size={14} className="mr-1 animate-spin" /> : <Zap size={14} className="mr-1" />} Full Cycle
          </Button>
        </div>
      </div>

      {/* Latest Run Summary */}
      {(latestOpt || latestImprov) && (
        <Card className="border-card-border bg-card border-primary/20">
          <CardContent className="p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Sparkles size={16} className="text-primary" />
                  <span className="text-sm font-medium">Latest {latestImprov ? "Improvement" : "Optimization"}</span>
                  <span className="text-[10px] text-muted-foreground font-mono">
                    {new Date((latestImprov || latestOpt)?.timestamp).toLocaleString()}
                  </span>
                </div>
                <div className="flex items-center gap-4 text-xs">
                  <span className="text-muted-foreground"><strong className="text-foreground">{(latestImprov || latestOpt)?.total_backtests}</strong> backtests</span>
                  <span className="text-muted-foreground"><strong className="text-foreground">{(latestImprov || latestOpt)?.duration_seconds}s</strong></span>
                  {latestImprov?.regime && <span className="text-muted-foreground">Regime: <strong className="text-foreground">{latestImprov.regime}</strong></span>}
                  {latestImprov?.changes_applied !== undefined && <span className="text-muted-foreground"><strong className="text-foreground">{latestImprov.changes_applied}</strong> param changes</span>}
                </div>
              </div>
              <Badge className="bg-[hsl(var(--profit))]/10 text-[hsl(var(--profit))] border-0"><CheckCircle2 size={12} className="mr-1" /> Applied</Badge>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Row 1: Rankings + Score Chart + Decision Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Rankings */}
        <Card className="border-card-border bg-card">
          <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5"><Trophy size={14} className="text-amber-400" /> Strategy Rankings</CardTitle></CardHeader>
          <CardContent className="p-4 pt-0">
            {ranking.length > 0 ? (
              <div className="space-y-1.5">
                {ranking.slice(0, 8).map((r: any, i: number) => (
                  <div key={i} className={`flex items-center justify-between p-2 rounded-md border ${i === 0 ? "bg-primary/5 border-primary/20" : "bg-muted/10 border-border/30"}`}>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold w-6" style={{ color: RANK_COLORS[i] }}>#{i + 1}</span>
                      <div>
                        <span className={`text-sm ${i === 0 ? "font-semibold" : ""}`}>{r.strategy}</span>
                        <div className="flex items-center gap-2 mt-0.5">
                          {r.sharpe !== undefined && <span className="text-[10px] text-muted-foreground font-mono">Sharpe: {r.sharpe?.toFixed(2)}</span>}
                          {r.return_pct !== undefined && <span className="text-[10px] text-muted-foreground font-mono">Ret: {r.return_pct?.toFixed(1)}%</span>}
                          {r.source && <Badge variant="outline" className="text-[8px] px-1 py-0">{r.source}</Badge>}
                        </div>
                      </div>
                    </div>
                    <span className="text-xs font-mono font-bold" style={{ color: RANK_COLORS[i] }}>{(r.score || r.blended_score || 0).toFixed(0)}</span>
                  </div>
                ))}
              </div>
            ) : <p className="text-sm text-muted-foreground py-6 text-center">Run optimization to see rankings</p>}
          </CardContent>
        </Card>

        {/* Score Chart */}
        <Card className="border-card-border bg-card">
          <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5"><BarChart3 size={14} /> Scores</CardTitle></CardHeader>
          <CardContent className="p-4 pt-0">
            {scoreChart.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={scoreChart} layout="vertical" margin={{ left: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(0 0% 16%)" />
                  <XAxis type="number" tick={{ fontSize: 10, fill: "hsl(0 0% 55%)" }} stroke="hsl(0 0% 16%)" />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: "hsl(0 0% 70%)" }} stroke="hsl(0 0% 16%)" width={80} />
                  <Tooltip contentStyle={{ backgroundColor: "hsl(0 0% 12%)", border: "1px solid hsl(0 0% 20%)", borderRadius: "6px", fontSize: "11px" }} />
                  <Bar dataKey="score" radius={[0, 4, 4, 0]}>{scoreChart.map((e: any, i: number) => <Cell key={i} fill={e.fill} />)}</Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : <div className="h-[260px] flex items-center justify-center text-muted-foreground text-sm">Run optimization</div>}
          </CardContent>
        </Card>

        {/* Decision Distribution */}
        <Card className="border-card-border bg-card">
          <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5"><Activity size={14} /> Decision Distribution</CardTitle></CardHeader>
          <CardContent className="p-4 pt-0">
            {decisionPie.length > 0 ? (
              <div>
                <ResponsiveContainer width="100%" height={160}>
                  <PieChart>
                    <Pie data={decisionPie} cx="50%" cy="50%" innerRadius={35} outerRadius={60} paddingAngle={2} dataKey="value">
                      {decisionPie.map((e, i) => <Cell key={i} fill={e.fill} />)}
                    </Pie>
                    <Tooltip contentStyle={{ backgroundColor: "hsl(0 0% 12%)", border: "1px solid hsl(0 0% 20%)", borderRadius: "6px", fontSize: "10px" }} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-0.5 mt-1">
                  {decisionPie.map((item, i) => (
                    <div key={i} className="flex items-center justify-between text-[10px]">
                      <div className="flex items-center gap-1.5">
                        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: item.fill }} />
                        <span className="text-muted-foreground">{item.name}</span>
                      </div>
                      <span className="font-mono">{item.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : <div className="h-[260px] flex items-center justify-center text-muted-foreground text-sm">Run cycles to see distribution</div>}
          </CardContent>
        </Card>
      </div>

      {/* Row 2: AI Accuracy + Adaptive Levels + Time Profile */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* AI Accuracy Gauge */}
        <Card className="border-card-border bg-card">
          <CardHeader className="pb-2"><CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1.5"><Brain size={13} /> AI Prediction Accuracy</CardTitle></CardHeader>
          <CardContent className="p-4 pt-0 flex flex-col items-center">
            <div className="relative w-24 h-24">
              <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
                <circle cx="50" cy="50" r="40" fill="none" stroke="hsl(0 0% 16%)" strokeWidth="8" />
                <circle cx="50" cy="50" r="40" fill="none" stroke={aiAccuracy >= 60 ? "hsl(142 72% 50%)" : aiAccuracy >= 45 ? "hsl(45 93% 52%)" : "hsl(0 84% 55%)"} strokeWidth="8" strokeDasharray={`${aiAccuracy * 2.51} 251`} strokeLinecap="round" />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-lg font-mono font-bold">{aiAccuracy.toFixed(0)}%</span>
              </div>
            </div>
            <span className="text-[10px] text-muted-foreground mt-1 capitalize">{adaptiveData?.ai_accuracy?.trust_level ?? "unknown"}</span>
            <span className="text-[10px] text-muted-foreground">{adaptiveData?.ai_accuracy?.evaluated ?? 0} predictions evaluated</span>
          </CardContent>
        </Card>

        {/* Adaptive Exit Levels */}
        <Card className="border-card-border bg-card">
          <CardHeader className="pb-2"><CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1.5"><Shield size={13} /> Adaptive Exit Levels</CardTitle></CardHeader>
          <CardContent className="p-4 pt-0 space-y-3">
            {["stop_loss_pct", "take_profit_pct", "trailing_stop_pct"].map((key) => {
              const val = adaptiveData?.exit_levels?.[key] ?? 0;
              const label = key === "stop_loss_pct" ? "Stop Loss" : key === "take_profit_pct" ? "Take Profit" : "Trailing Stop";
              const color = key === "stop_loss_pct" ? "hsl(0 84% 55%)" : key === "take_profit_pct" ? "hsl(142 72% 50%)" : "hsl(45 93% 52%)";
              return (
                <div key={key} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">{label}</span>
                    <span className="font-mono font-medium">{val}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-muted/30">
                    <div className="h-full rounded-full transition-all" style={{ width: `${Math.min(100, val * 5)}%`, backgroundColor: color }} />
                  </div>
                </div>
              );
            })}
            <div className="text-[10px] text-muted-foreground pt-1 border-t border-border">
              Source: {adaptiveData?.exit_levels?.source ?? "default"} · AI weight: {adaptiveData?.ai_weight_modifier ?? 1}x
            </div>
          </CardContent>
        </Card>

        {/* Time-of-Day Profile */}
        <Card className="border-card-border bg-card">
          <CardHeader className="pb-2"><CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1.5"><Clock size={13} /> Trading Hours Profile</CardTitle></CardHeader>
          <CardContent className="p-4 pt-0">
            {Object.keys(adaptiveData?.time_profile ?? {}).length > 0 ? (
              <div className="space-y-1">
                {Object.entries(adaptiveData.time_profile).map(([hour, data]: [string, any]) => (
                  <div key={hour} className="flex items-center gap-2 text-[10px]">
                    <span className="text-muted-foreground w-10 font-mono">{hour}:00</span>
                    <div className="flex-1 h-2 rounded-full bg-muted/30">
                      <div className="h-full rounded-full" style={{
                        width: `${data.win_rate * 100}%`,
                        backgroundColor: data.win_rate >= 0.55 ? "hsl(142 72% 50%)" : data.win_rate >= 0.4 ? "hsl(45 93% 52%)" : "hsl(0 84% 55%)"
                      }} />
                    </div>
                    <span className="font-mono w-10 text-right">{(data.win_rate * 100).toFixed(0)}%</span>
                    <span className="text-muted-foreground w-6 text-right">{data.trades}t</span>
                  </div>
                ))}
              </div>
            ) : <p className="text-xs text-muted-foreground py-6 text-center">Trade history will build hourly profile</p>}
          </CardContent>
        </Card>
      </div>

      {/* Journal Analysis */}
      <Card className="border-card-border bg-card">
        <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5"><BookOpen size={14} /> Trade Journal Analysis {latestJournal && <Badge variant="outline" className="text-[9px] ml-2 font-mono">{latestJournal.provider}</Badge>}</CardTitle></CardHeader>
        <CardContent className="p-4 pt-0">
          {latestJournal ? (
            <div className="space-y-4">
              {latestJournal.ai_analysis?.performance_assessment && <p className="text-sm text-muted-foreground leading-relaxed">{latestJournal.ai_analysis.performance_assessment}</p>}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                {[["Trades", latestJournal.summary?.trades_executed], ["Holds", latestJournal.summary?.no_signal_events], ["Risk Blocks", latestJournal.summary?.risk_blocks], ["Errors", latestJournal.summary?.errors], ["Decisions", latestJournal.summary?.total_decisions]].map(([label, val], i) => (
                  <div key={i} className="p-2 rounded bg-muted/20 text-center">
                    <p className="text-lg font-mono font-bold">{val ?? 0}</p>
                    <p className="text-[10px] text-muted-foreground">{label}</p>
                  </div>
                ))}
              </div>
              {latestJournal.ai_analysis?.recommendations?.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Recommendations</h3>
                  {latestJournal.ai_analysis.recommendations.map((rec: any, i: number) => (
                    <div key={i} className="flex items-start gap-3 p-3 rounded-md bg-muted/15 border border-border/30">
                      <PriorityBadge priority={rec.priority} />
                      <div className="flex-1"><p className="text-sm font-medium">{rec.action}</p>{rec.reasoning && <p className="text-xs text-muted-foreground mt-0.5">{rec.reasoning}</p>}</div>
                      <Badge variant="outline" className="text-[9px] px-1.5 py-0 shrink-0">{rec.category}</Badge>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : <p className="text-sm text-muted-foreground py-6 text-center">Run journal analysis to see AI-powered insights</p>}
        </CardContent>
      </Card>
    </div>
  );
}
