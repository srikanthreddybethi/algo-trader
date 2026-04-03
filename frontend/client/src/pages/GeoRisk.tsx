import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import {
  Globe,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Activity,
  Shield,
  Search,
  Bell,
  BarChart3,
  Clock,
  MapPin,
  Zap,
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

// ── Types ───────────────────────────────────────────────────────────────────

interface GeoEvent {
  event_id: string;
  event_type: string;
  title: string;
  description: string;
  source: string;
  source_url: string;
  confidence: number;
  severity: number;
  regions: string[];
  secondary_types: string[];
  tone_score: number;
  article_count: number;
  timestamp: string;
}

interface AssetRiskScore {
  asset: string;
  asset_class: string;
  geo_risk_score: number;
  geo_opportunity_score: number;
  net_signal: number;
  signal_strength: string;
  dominant_events: { type: string; description: string; contribution: number; direction: string }[];
  recommended_action: string;
  position_size_modifier: number;
  confidence: number;
  data_freshness_minutes: number;
  sources_analyzed: number;
}

interface HeatmapRegion {
  region: string;
  risk_score: number;
  event_count: number;
  dominant_event_type: string;
  trending: string;
}

interface TimelinePoint {
  timestamp: string;
  risk_score: number;
  event_count: number;
}

interface Analytics {
  total_active_events: number;
  events_by_type: Record<string, number>;
  events_by_region: Record<string, number>;
  avg_severity: number;
  avg_confidence: number;
  data_freshness_minutes: number;
  alerts_configured: number;
}

// ── Constants ───────────────────────────────────────────────────────────────

const EVENT_TYPE_STYLES: Record<string, { label: string; cls: string }> = {
  MILITARY_CONFLICT: { label: "Military Conflict", cls: "bg-red-500/20 text-red-300 border-red-500/30" },
  TERRORISM: { label: "Terrorism", cls: "bg-red-600/20 text-red-400 border-red-600/30" },
  SANCTIONS: { label: "Sanctions", cls: "bg-orange-500/20 text-orange-300 border-orange-500/30" },
  TRADE_WAR: { label: "Trade War", cls: "bg-amber-500/20 text-amber-300 border-amber-500/30" },
  ELECTION: { label: "Election", cls: "bg-blue-500/20 text-blue-300 border-blue-500/30" },
  CIVIL_UNREST: { label: "Civil Unrest", cls: "bg-orange-600/20 text-orange-400 border-orange-600/30" },
  DIPLOMATIC_CRISIS: { label: "Diplomatic Crisis", cls: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30" },
  NATURAL_DISASTER: { label: "Natural Disaster", cls: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30" },
  REGULATORY_CHANGE: { label: "Regulatory Change", cls: "bg-purple-500/20 text-purple-300 border-purple-500/30" },
  ENERGY_CRISIS: { label: "Energy Crisis", cls: "bg-rose-500/20 text-rose-300 border-rose-500/30" },
  CYBER_ATTACK: { label: "Cyber Attack", cls: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30" },
  REPUTATION_EVENT: { label: "Reputation Event", cls: "bg-pink-500/20 text-pink-300 border-pink-500/30" },
  COMMODITY_DISRUPTION: { label: "Commodity Disruption", cls: "bg-lime-500/20 text-lime-300 border-lime-500/30" },
  CURRENCY_CRISIS: { label: "Currency Crisis", cls: "bg-fuchsia-500/20 text-fuchsia-300 border-fuchsia-500/30" },
};

const RISK_LEVEL_STYLES: Record<string, { label: string; cls: string }> = {
  extreme: { label: "Extreme", cls: "bg-red-500/20 text-red-300" },
  strong: { label: "Strong", cls: "bg-orange-500/20 text-orange-300" },
  moderate: { label: "Moderate", cls: "bg-amber-500/20 text-amber-300" },
  weak: { label: "Weak", cls: "bg-green-500/20 text-green-300" },
};

const ACTION_STYLES: Record<string, { label: string; cls: string }> = {
  reduce_exposure: { label: "Reduce Exposure", cls: "bg-red-500/20 text-red-300 border-red-500/30" },
  hedge: { label: "Hedge", cls: "bg-amber-500/20 text-amber-300 border-amber-500/30" },
  hold: { label: "Hold", cls: "bg-blue-500/20 text-blue-300 border-blue-500/30" },
  increase_exposure: { label: "Increase Exposure", cls: "bg-green-500/20 text-green-300 border-green-500/30" },
};

const REGION_LABELS: Record<string, string> = {
  middle_east: "Middle East",
  us_china: "US / China",
  europe: "Europe",
  russia: "Russia / Ukraine",
  asia_pacific: "Asia Pacific",
};

const ASSET_CLASSES = ["crypto", "equities", "forex", "commodities"];

// ── Risk Gauge ──────────────────────────────────────────────────────────────

function RiskGauge({ score, label }: { score: number; label: string }) {
  const pct = Math.min(Math.max(score * 100, 0), 100);
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (pct / 100) * circumference;
  const color =
    pct >= 85 ? "hsl(0 84% 60%)" :
    pct >= 70 ? "hsl(25 95% 53%)" :
    pct >= 50 ? "hsl(45 93% 47%)" :
    pct >= 30 ? "hsl(168 80% 42%)" :
    "hsl(142 71% 45%)";

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative w-24 h-24">
        <svg viewBox="0 0 96 96" className="w-full h-full -rotate-90">
          <circle cx="48" cy="48" r={radius} fill="none" stroke="hsl(var(--muted))" strokeWidth="8" />
          <circle
            cx="48" cy="48" r={radius} fill="none"
            stroke={color} strokeWidth="8"
            strokeDasharray={circumference} strokeDashoffset={offset}
            strokeLinecap="round" className="transition-all duration-700"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-lg font-bold font-mono" style={{ color }}>{pct.toFixed(0)}%</span>
        </div>
      </div>
      <span className="text-[10px] text-muted-foreground">{label}</span>
    </div>
  );
}

// ── Severity Bar ────────────────────────────────────────────────────────────

function SeverityBar({ value }: { value: number }) {
  const pct = Math.min(Math.max(value * 100, 0), 100);
  const color = value >= 0.7 ? "bg-red-500" : value >= 0.5 ? "bg-amber-500" : "bg-green-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-muted/30 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono w-10 text-right">{pct.toFixed(0)}%</span>
    </div>
  );
}

// ── Main Page ───────────────────────────────────────────────────────────────

export default function GeoRisk() {
  const [scoreAssetClass, setScoreAssetClass] = useState("crypto");
  const [evalTitle, setEvalTitle] = useState("");
  const [evalDesc, setEvalDesc] = useState("");
  const [evalResult, setEvalResult] = useState<any>(null);

  // ── Queries ─────────────────────────────────────────────────────────

  const { data: events } = useQuery<GeoEvent[]>({
    queryKey: ["/api/v1/geo-risk/events"],
    queryFn: async () => { const r = await apiRequest("GET", "/api/v1/geo-risk/events?limit=50"); return r.json(); },
    refetchInterval: 30000,
  });

  const { data: scores } = useQuery<Record<string, AssetRiskScore>>({
    queryKey: ["/api/v1/geo-risk/scores", scoreAssetClass],
    queryFn: async () => { const r = await apiRequest("GET", `/api/v1/geo-risk/scores?asset_class=${scoreAssetClass}`); return r.json(); },
    refetchInterval: 30000,
  });

  const { data: heatmap } = useQuery<HeatmapRegion[]>({
    queryKey: ["/api/v1/geo-risk/heatmap"],
    queryFn: async () => { const r = await apiRequest("GET", "/api/v1/geo-risk/heatmap"); return r.json(); },
    refetchInterval: 60000,
  });

  const { data: timeline } = useQuery<TimelinePoint[]>({
    queryKey: ["/api/v1/geo-risk/timeline"],
    queryFn: async () => { const r = await apiRequest("GET", "/api/v1/geo-risk/timeline?hours=168"); return r.json(); },
    refetchInterval: 60000,
  });

  const { data: analytics } = useQuery<Analytics>({
    queryKey: ["/api/v1/geo-risk/analytics"],
    queryFn: async () => { const r = await apiRequest("GET", "/api/v1/geo-risk/analytics"); return r.json(); },
    refetchInterval: 30000,
  });

  // ── Evaluate Mutation ───────────────────────────────────────────────

  const evaluateMutation = useMutation({
    mutationFn: async () => {
      const r = await apiRequest("POST", "/api/v1/geo-risk/evaluate", { title: evalTitle, description: evalDesc });
      return r.json();
    },
    onSuccess: (data) => {
      setEvalResult(data);
      queryClient.invalidateQueries({ queryKey: ["/api/v1/geo-risk/events"] });
    },
  });

  // ── Derived ─────────────────────────────────────────────────────────

  const maxTimelineRisk = Math.max(0.01, ...(timeline?.map(t => t.risk_score) ?? [0]));
  const typeEntries = analytics?.events_by_type ? Object.entries(analytics.events_by_type) : [];
  const maxTypeCount = Math.max(1, ...typeEntries.map(([, v]) => v));

  // ── Render ──────────────────────────────────────────────────────────

  return (
    <div data-testid="geo-risk-page" className="space-y-6 p-4 md:p-6 max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-primary/10">
          <Globe size={24} className="text-primary" />
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tight">Geopolitical Risk Intelligence</h1>
          <p className="text-sm text-muted-foreground">
            Real-time geopolitical event monitoring and asset impact scoring
          </p>
        </div>
        {analytics && (
          <div className="ml-auto flex items-center gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <Activity size={12} /> {analytics.total_active_events} events
            </span>
            <span className="flex items-center gap-1">
              <Clock size={12} /> {analytics.data_freshness_minutes.toFixed(0)}m ago
            </span>
          </div>
        )}
      </div>

      {/* ═══ Top Row: Heatmap + Analytics ═══ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Geographic Risk Heatmap */}
        <Card className="border-card-border bg-card" data-testid="section-heatmap">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-base">
              <MapPin size={18} className="text-primary" />
              Regional Risk Heatmap
            </CardTitle>
          </CardHeader>
          <CardContent>
            {heatmap && heatmap.length > 0 ? (
              <div className="space-y-3">
                {heatmap.map((region) => {
                  const style = EVENT_TYPE_STYLES[region.dominant_event_type];
                  return (
                    <div key={region.region} className="flex items-center gap-3 rounded-lg border border-border p-3" data-testid={`heatmap-${region.region}`}>
                      <div className="w-28 shrink-0">
                        <div className="text-sm font-medium">{REGION_LABELS[region.region] ?? region.region}</div>
                        <div className="text-[10px] text-muted-foreground">{region.event_count} events</div>
                      </div>
                      <div className="flex-1">
                        <SeverityBar value={region.risk_score} />
                      </div>
                      <Badge className={`text-[10px] border ${style?.cls ?? "bg-muted/20 text-muted-foreground"}`}>
                        {style?.label ?? region.dominant_event_type}
                      </Badge>
                      <Badge className={`text-[10px] ${region.trending === "rising" ? "bg-red-500/20 text-red-300" : "bg-muted/20 text-muted-foreground"}`}>
                        {region.trending}
                      </Badge>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-sm text-muted-foreground text-center py-8">
                No regional risk data yet. Events will appear as they are detected.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Analytics Summary */}
        <Card className="border-card-border bg-card" data-testid="section-analytics">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-base">
              <BarChart3 size={18} className="text-primary" />
              Event Analytics
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            {/* Stats row */}
            {analytics && (
              <div className="grid grid-cols-3 gap-3">
                <div className="rounded-lg bg-muted/20 p-3 text-center">
                  <div className="text-lg font-bold font-mono text-primary">{analytics.total_active_events}</div>
                  <div className="text-[10px] text-muted-foreground">Active Events</div>
                </div>
                <div className="rounded-lg bg-muted/20 p-3 text-center">
                  <div className="text-lg font-bold font-mono text-primary">{(analytics.avg_severity * 100).toFixed(0)}%</div>
                  <div className="text-[10px] text-muted-foreground">Avg Severity</div>
                </div>
                <div className="rounded-lg bg-muted/20 p-3 text-center">
                  <div className="text-lg font-bold font-mono text-primary">{(analytics.avg_confidence * 100).toFixed(0)}%</div>
                  <div className="text-[10px] text-muted-foreground">Avg Confidence</div>
                </div>
              </div>
            )}

            {/* Event type distribution */}
            {typeEntries.length > 0 && (
              <div>
                <div className="text-xs text-muted-foreground mb-2">Events by Type</div>
                <div className="space-y-1.5">
                  {typeEntries.slice(0, 8).map(([type, count]) => {
                    const style = EVENT_TYPE_STYLES[type];
                    const pct = (count / maxTypeCount) * 100;
                    return (
                      <div key={type} className="flex items-center gap-2">
                        <div className="w-32 shrink-0 text-[10px] text-muted-foreground truncate">
                          {style?.label ?? type}
                        </div>
                        <div className="flex-1 h-2 bg-muted/30 rounded-full overflow-hidden">
                          <div className="h-full rounded-full bg-primary/60 transition-all duration-500" style={{ width: `${pct}%` }} />
                        </div>
                        <span className="text-[10px] font-mono text-muted-foreground w-6 text-right">{count}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ═══ Asset Impact Grid ═══ */}
      <Card className="border-card-border bg-card" data-testid="section-scores">
        <CardHeader className="pb-4">
          <CardTitle className="flex items-center gap-2 text-base">
            <Shield size={18} className="text-primary" />
            Asset Impact Grid
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs value={scoreAssetClass} onValueChange={setScoreAssetClass}>
            <TabsList className="mb-4 flex-wrap h-auto gap-1">
              {ASSET_CLASSES.map((ac) => (
                <TabsTrigger key={ac} value={ac} className="text-xs capitalize">{ac}</TabsTrigger>
              ))}
            </TabsList>

            {ASSET_CLASSES.map((ac) => (
              <TabsContent key={ac} value={ac}>
                {scores && Object.keys(scores).length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {Object.entries(scores).map(([symbol, score]) => {
                      const actionStyle = ACTION_STYLES[score.recommended_action];
                      const riskStyle = RISK_LEVEL_STYLES[score.signal_strength];
                      return (
                        <div key={symbol} className="rounded-lg border border-border p-4 space-y-3" data-testid={`score-${symbol}`}>
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-bold font-mono">{symbol}</span>
                            <Badge className={`text-[10px] border ${actionStyle?.cls ?? ""}`}>
                              {actionStyle?.label ?? score.recommended_action}
                            </Badge>
                          </div>
                          <div className="flex justify-around">
                            <RiskGauge score={score.geo_risk_score} label="Risk" />
                            <RiskGauge score={score.geo_opportunity_score} label="Opportunity" />
                          </div>
                          <div className="grid grid-cols-3 gap-2 text-center">
                            <div>
                              <div className={`text-sm font-bold font-mono ${score.net_signal < 0 ? "text-[hsl(var(--loss))]" : score.net_signal > 0 ? "text-[hsl(var(--profit))]" : ""}`}>
                                {score.net_signal > 0 ? "+" : ""}{(score.net_signal * 100).toFixed(0)}%
                              </div>
                              <div className="text-[10px] text-muted-foreground">Net Signal</div>
                            </div>
                            <div>
                              <div className="text-sm font-bold font-mono text-primary">{(score.position_size_modifier * 100).toFixed(0)}%</div>
                              <div className="text-[10px] text-muted-foreground">Position Size</div>
                            </div>
                            <div>
                              <Badge className={`text-[10px] ${riskStyle?.cls ?? ""}`}>{riskStyle?.label ?? score.signal_strength}</Badge>
                              <div className="text-[10px] text-muted-foreground mt-1">Strength</div>
                            </div>
                          </div>
                          {score.dominant_events.length > 0 && (
                            <div className="border-t border-border pt-2">
                              <div className="text-[10px] text-muted-foreground mb-1">Top Drivers</div>
                              {score.dominant_events.slice(0, 2).map((de, i) => (
                                <div key={i} className="flex items-center gap-1 text-[10px]">
                                  {de.direction === "bearish" ? <TrendingDown size={10} className="text-[hsl(var(--loss))] shrink-0" /> : <TrendingUp size={10} className="text-[hsl(var(--profit))] shrink-0" />}
                                  <span className="truncate text-muted-foreground">{de.description}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground text-center py-8">
                    No scores available. Refresh geo risk data to generate scores.
                  </div>
                )}
              </TabsContent>
            ))}
          </Tabs>
        </CardContent>
      </Card>

      {/* ═══ Risk Timeline ═══ */}
      <Card className="border-card-border bg-card" data-testid="section-timeline">
        <CardHeader className="pb-4">
          <CardTitle className="flex items-center gap-2 text-base">
            <Activity size={18} className="text-primary" />
            Risk Timeline (7 days)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {timeline && timeline.length > 0 ? (
            <div className="h-32 flex items-end gap-px">
              {timeline.slice(-96).map((point, i) => {
                const heightPct = (point.risk_score / maxTimelineRisk) * 100;
                const color =
                  point.risk_score >= 0.7 ? "bg-red-500" :
                  point.risk_score >= 0.5 ? "bg-amber-500" :
                  point.risk_score >= 0.3 ? "bg-yellow-500" :
                  "bg-green-500";
                return (
                  <Tooltip key={i}>
                    <TooltipTrigger asChild>
                      <div
                        className={`flex-1 rounded-t transition-all duration-300 ${color} cursor-help min-w-[2px]`}
                        style={{ height: `${Math.max(heightPct, 2)}%`, opacity: point.risk_score > 0 ? 1 : 0.15 }}
                      />
                    </TooltipTrigger>
                    <TooltipContent>
                      <div className="text-xs">
                        <div>{point.timestamp}</div>
                        <div>Risk: {(point.risk_score * 100).toFixed(0)}%</div>
                        <div>Events: {point.event_count}</div>
                      </div>
                    </TooltipContent>
                  </Tooltip>
                );
              })}
            </div>
          ) : (
            <div className="text-sm text-muted-foreground text-center py-8">
              No timeline data yet.
            </div>
          )}
        </CardContent>
      </Card>

      {/* ═══ Active Events Feed + Manual Evaluator ═══ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Events Feed */}
        <Card className="border-card-border bg-card lg:col-span-2" data-testid="section-events">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-base">
              <Zap size={18} className="text-primary" />
              Active Events Feed
            </CardTitle>
          </CardHeader>
          <CardContent>
            {events && events.length > 0 ? (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-xs">Time</TableHead>
                      <TableHead className="text-xs">Type</TableHead>
                      <TableHead className="text-xs">Title</TableHead>
                      <TableHead className="text-xs text-center">Severity</TableHead>
                      <TableHead className="text-xs text-center">Confidence</TableHead>
                      <TableHead className="text-xs">Regions</TableHead>
                      <TableHead className="text-xs">Source</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {events.slice(0, 25).map((ev) => {
                      const style = EVENT_TYPE_STYLES[ev.event_type];
                      return (
                        <TableRow key={ev.event_id} data-testid={`event-${ev.event_id}`}>
                          <TableCell className="text-xs font-mono text-muted-foreground whitespace-nowrap">
                            {ev.timestamp ? new Date(ev.timestamp).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—"}
                          </TableCell>
                          <TableCell>
                            <Badge className={`text-[10px] border whitespace-nowrap ${style?.cls ?? ""}`}>
                              {style?.label ?? ev.event_type}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-xs max-w-[300px] truncate" title={ev.title}>
                            {ev.title}
                          </TableCell>
                          <TableCell className="text-center">
                            <span className={`text-xs font-mono font-medium ${ev.severity >= 0.7 ? "text-red-400" : ev.severity >= 0.5 ? "text-amber-400" : "text-green-400"}`}>
                              {(ev.severity * 100).toFixed(0)}%
                            </span>
                          </TableCell>
                          <TableCell className="text-center text-xs font-mono">
                            {(ev.confidence * 100).toFixed(0)}%
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground">
                            {ev.regions.map(r => REGION_LABELS[r] ?? r).join(", ") || "—"}
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground">
                            {ev.source}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <div className="text-sm text-muted-foreground text-center py-8">
                No active events. The monitor will detect events as they occur.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Manual Evaluator */}
        <Card className="border-card-border bg-card" data-testid="section-evaluator">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-base">
              <Search size={18} className="text-primary" />
              Event Evaluator
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Event Title</label>
              <Input
                data-testid="eval-title"
                value={evalTitle}
                onChange={(e) => setEvalTitle(e.target.value)}
                placeholder="e.g. US imposes new sanctions on Iran"
                className="text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Description (optional)</label>
              <Input
                data-testid="eval-desc"
                value={evalDesc}
                onChange={(e) => setEvalDesc(e.target.value)}
                placeholder="Additional context..."
                className="text-sm"
              />
            </div>
            <Button
              data-testid="btn-evaluate"
              onClick={() => evaluateMutation.mutate()}
              disabled={evaluateMutation.isPending || !evalTitle}
              className="w-full"
            >
              <Shield size={16} className="mr-2" />
              {evaluateMutation.isPending ? "Classifying..." : "Classify Event"}
            </Button>

            {evalResult && (
              <div className="border border-border rounded-lg p-3 space-y-2" data-testid="eval-result">
                {evalResult.classified ? (
                  <>
                    <div className="flex items-center gap-2">
                      <Badge className={`text-[10px] border ${EVENT_TYPE_STYLES[evalResult.event?.event_type]?.cls ?? ""}`}>
                        {EVENT_TYPE_STYLES[evalResult.event?.event_type]?.label ?? evalResult.event?.event_type}
                      </Badge>
                      {evalResult.event?.secondary_types?.map((t: string) => (
                        <Badge key={t} className={`text-[10px] border ${EVENT_TYPE_STYLES[t]?.cls ?? ""}`}>
                          {EVENT_TYPE_STYLES[t]?.label ?? t}
                        </Badge>
                      ))}
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-center">
                      <div>
                        <div className="text-sm font-bold font-mono text-primary">{(evalResult.event?.severity * 100).toFixed(0)}%</div>
                        <div className="text-[10px] text-muted-foreground">Severity</div>
                      </div>
                      <div>
                        <div className="text-sm font-bold font-mono text-primary">{(evalResult.event?.confidence * 100).toFixed(0)}%</div>
                        <div className="text-[10px] text-muted-foreground">Confidence</div>
                      </div>
                    </div>
                    {evalResult.event?.regions?.length > 0 && (
                      <div className="text-[10px] text-muted-foreground">
                        Regions: {evalResult.event.regions.map((r: string) => REGION_LABELS[r] ?? r).join(", ")}
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-xs text-muted-foreground text-center py-2">
                    {evalResult.message}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
