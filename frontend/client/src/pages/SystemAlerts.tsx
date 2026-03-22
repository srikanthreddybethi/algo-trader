import { useQuery, useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Bell, BellOff, CheckCircle2, AlertTriangle, XCircle, Info,
  Mail, Globe, Monitor, Trash2, Eye, EyeOff, Send,
} from "lucide-react";

interface SystemAlert {
  id: string;
  severity: string;
  category: string;
  message: string;
  details: Record<string, any>;
  timestamp: string;
  read: boolean;
}

interface AlertStats {
  total_alerts: number;
  by_severity: Record<string, number>;
  unread: Record<string, number>;
  plugins: Record<string, { configured: boolean; min_severity: string }>;
}

const SEVERITY_CONFIG: Record<string, { color: string; bg: string; icon: any; label: string }> = {
  critical: { color: "text-red-400", bg: "bg-red-500/10 border-red-500/20", icon: XCircle, label: "CRITICAL" },
  high:     { color: "text-orange-400", bg: "bg-orange-500/10 border-orange-500/20", icon: AlertTriangle, label: "HIGH" },
  medium:   { color: "text-amber-400", bg: "bg-amber-500/10 border-amber-500/20", icon: Info, label: "MEDIUM" },
  low:      { color: "text-blue-400", bg: "bg-blue-500/10 border-blue-500/20", icon: Info, label: "LOW" },
};

export default function SystemAlerts() {
  const { toast } = useToast();

  const { data: alerts, isLoading } = useQuery<SystemAlert[]>({
    queryKey: ["/api/system-alerts"],
    queryFn: async () => { const r = await apiRequest("GET", "/api/system-alerts/?limit=100"); return r.json(); },
    refetchInterval: 5000,
  });

  const { data: stats } = useQuery<AlertStats>({
    queryKey: ["/api/system-alerts/stats"],
    queryFn: async () => { const r = await apiRequest("GET", "/api/system-alerts/stats"); return r.json(); },
    refetchInterval: 10000,
  });

  const { data: unread } = useQuery<Record<string, number>>({
    queryKey: ["/api/system-alerts/unread"],
    queryFn: async () => { const r = await apiRequest("GET", "/api/system-alerts/unread"); return r.json(); },
    refetchInterval: 5000,
  });

  const markAllRead = useMutation({
    mutationFn: () => apiRequest("POST", "/api/system-alerts/mark-all-read"),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["/api/system-alerts"] }); queryClient.invalidateQueries({ queryKey: ["/api/system-alerts/unread"] }); },
  });

  const clearAlerts = useMutation({
    mutationFn: () => apiRequest("DELETE", "/api/system-alerts/clear"),
    onSuccess: () => { toast({ title: "Alerts cleared" }); queryClient.invalidateQueries({ queryKey: ["/api/system-alerts"] }); queryClient.invalidateQueries({ queryKey: ["/api/system-alerts/stats"] }); },
  });

  const testAlert = useMutation({
    mutationFn: () => apiRequest("POST", "/api/system-alerts/test"),
    onSuccess: () => { toast({ title: "Test alert sent" }); queryClient.invalidateQueries({ queryKey: ["/api/system-alerts"] }); },
  });

  const markRead = useMutation({
    mutationFn: (id: string) => apiRequest("POST", `/api/system-alerts/mark-read/${id}`),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["/api/system-alerts"] }); queryClient.invalidateQueries({ queryKey: ["/api/system-alerts/unread"] }); },
  });

  const totalUnread = Object.values(unread ?? {}).reduce((a, b) => a + b, 0);
  const alertList = alerts ?? [];

  return (
    <div className="space-y-4" data-testid="system-alerts-page">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold">System Alerts</h1>
          {totalUnread > 0 && (
            <Badge className="bg-[hsl(var(--loss))]/10 text-[hsl(var(--loss))] border-0">
              {totalUnread} unread
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="h-8 text-xs" onClick={() => testAlert.mutate()}>
            <Send size={14} className="mr-1" /> Test
          </Button>
          <Button variant="outline" size="sm" className="h-8 text-xs" onClick={() => markAllRead.mutate()}>
            <Eye size={14} className="mr-1" /> Mark All Read
          </Button>
          <Button variant="outline" size="sm" className="h-8 text-xs text-[hsl(var(--loss))]" onClick={() => clearAlerts.mutate()}>
            <Trash2 size={14} className="mr-1" /> Clear
          </Button>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {(["critical", "high", "medium", "low"] as const).map((sev) => {
          const cfg = SEVERITY_CONFIG[sev];
          const Icon = cfg.icon;
          const count = unread?.[sev] ?? 0;
          const total = stats?.by_severity?.[sev] ?? 0;
          return (
            <Card key={sev} className={`border ${count > 0 ? cfg.bg : "border-card-border bg-card"}`}>
              <CardContent className="p-3 flex items-center justify-between">
                <div>
                  <p className={`text-[10px] uppercase tracking-wider ${cfg.color}`}>{cfg.label}</p>
                  <p className="text-lg font-mono font-bold">{count > 0 ? count : total}</p>
                  <p className="text-[10px] text-muted-foreground">{count > 0 ? "unread" : "total"}</p>
                </div>
                <Icon size={20} className={count > 0 ? cfg.color : "text-muted-foreground/30"} />
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Plugin Status */}
      <Card className="border-card-border bg-card">
        <CardHeader className="pb-2">
          <CardTitle className="text-xs font-medium text-muted-foreground">Notification Plugins</CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="flex flex-wrap gap-3">
            {[
              { name: "In-App", icon: Monitor, key: "in_app" },
              { name: "Console", icon: Monitor, key: "console" },
              { name: "Email", icon: Mail, key: "email" },
              { name: "Webhook", icon: Globe, key: "webhook" },
            ].map(({ name, icon: Icon, key }) => {
              const plugin = stats?.plugins?.[key];
              const configured = plugin?.configured ?? false;
              return (
                <div key={key} className={`flex items-center gap-2 px-3 py-1.5 rounded-md border ${configured ? "border-[hsl(var(--profit))]/30 bg-[hsl(var(--profit))]/5" : "border-border bg-muted/10"}`}>
                  <Icon size={14} className={configured ? "text-[hsl(var(--profit))]" : "text-muted-foreground"} />
                  <span className="text-xs font-medium">{name}</span>
                  <Badge variant="outline" className={`text-[9px] px-1 py-0 ${configured ? "text-[hsl(var(--profit))]" : "text-muted-foreground"}`}>
                    {configured ? "ON" : "OFF"}
                  </Badge>
                  {plugin?.min_severity && configured && (
                    <span className="text-[9px] text-muted-foreground">{plugin.min_severity}+</span>
                  )}
                </div>
              );
            })}
          </div>
          <p className="text-[10px] text-muted-foreground mt-2">
            Configure email: set SMTP_USER, SMTP_PASS, ALERT_TO_EMAIL env vars. Webhook: set ALERT_WEBHOOK_URL.
          </p>
        </CardContent>
      </Card>

      {/* Alert List */}
      <Card className="border-card-border bg-card">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
            <Bell size={14} />
            All Alerts ({alertList.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          {isLoading ? (
            <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}</div>
          ) : alertList.length === 0 ? (
            <p className="text-sm text-muted-foreground py-8 text-center">No system alerts. The system is healthy.</p>
          ) : (
            <div className="space-y-1 max-h-[500px] overflow-y-auto">
              {alertList.map((alert) => {
                const cfg = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.low;
                const Icon = cfg.icon;
                return (
                  <div
                    key={alert.id}
                    className={`flex items-start gap-3 p-3 rounded-md border transition-colors ${
                      !alert.read ? cfg.bg : "bg-muted/5 border-border/30 opacity-60"
                    }`}
                    onClick={() => !alert.read && markRead.mutate(alert.id)}
                  >
                    <Icon size={16} className={`mt-0.5 shrink-0 ${cfg.color}`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge variant="outline" className={`text-[9px] px-1.5 py-0 ${cfg.color} border-0 ${cfg.bg.split(" ")[0]}`}>
                          {alert.severity.toUpperCase()}
                        </Badge>
                        <span className="text-xs font-mono text-muted-foreground">{alert.category}</span>
                        {!alert.read && <span className="w-1.5 h-1.5 rounded-full bg-primary" />}
                      </div>
                      <p className="text-sm mt-0.5">{alert.message}</p>
                      {alert.details && Object.keys(alert.details).length > 0 && (
                        <p className="text-[10px] text-muted-foreground mt-0.5 font-mono">
                          {Object.entries(alert.details).map(([k, v]) => `${k}: ${v}`).join(" · ")}
                        </p>
                      )}
                    </div>
                    <span className="text-[10px] text-muted-foreground shrink-0 font-mono">
                      {new Date(alert.timestamp).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
