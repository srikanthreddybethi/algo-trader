import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
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
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Bell,
  BellOff,
  Plus,
  Trash2,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";

interface AlertItem {
  id: number;
  alert_type: string;
  symbol: string | null;
  exchange_name: string | null;
  threshold: number;
  message: string | null;
  is_active: boolean;
  is_triggered: boolean;
  triggered_at: string | null;
  created_at: string | null;
}

const fmt = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const ALERT_TYPES = [
  { value: "price_above", label: "Price Above", icon: TrendingUp, color: "text-[hsl(var(--profit))]" },
  { value: "price_below", label: "Price Below", icon: TrendingDown, color: "text-[hsl(var(--loss))]" },
  { value: "pnl_above", label: "P&L Above", icon: TrendingUp, color: "text-[hsl(var(--profit))]" },
  { value: "pnl_below", label: "P&L Below", icon: TrendingDown, color: "text-[hsl(var(--loss))]" },
  { value: "drawdown", label: "Max Drawdown", icon: AlertTriangle, color: "text-amber-400" },
];

function getAlertTypeInfo(type: string) {
  return ALERT_TYPES.find((t) => t.value === type) || ALERT_TYPES[0];
}

export default function Alerts() {
  const { toast } = useToast();
  const [showForm, setShowForm] = useState(false);
  const [alertType, setAlertType] = useState("price_above");
  const [symbol, setSymbol] = useState("BTC-USDT");
  const [exchangeName, setExchangeName] = useState("binance");
  const [threshold, setThreshold] = useState("");
  const [message, setMessage] = useState("");

  const { data: alerts, isLoading } = useQuery<AlertItem[]>({
    queryKey: ["/api/alerts"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/alerts/");
      return res.json();
    },
    refetchInterval: 10000,
  });

  const createAlert = useMutation({
    mutationFn: async () => {
      return apiRequest("POST", "/api/alerts/", {
        alert_type: alertType,
        symbol: alertType.startsWith("price") ? symbol : null,
        exchange_name: alertType.startsWith("price") ? exchangeName : null,
        threshold: parseFloat(threshold),
        message: message || null,
      });
    },
    onSuccess: () => {
      toast({ title: "Alert created" });
      queryClient.invalidateQueries({ queryKey: ["/api/alerts"] });
      setShowForm(false);
      setThreshold("");
      setMessage("");
    },
    onError: (err: Error) => {
      toast({ title: "Failed to create alert", description: err.message, variant: "destructive" });
    },
  });

  const toggleAlert = useMutation({
    mutationFn: async ({ id, is_active }: { id: number; is_active: boolean }) => {
      return apiRequest("PATCH", `/api/alerts/${id}`, { is_active });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/alerts"] });
    },
  });

  const deleteAlert = useMutation({
    mutationFn: async (id: number) => {
      return apiRequest("DELETE", `/api/alerts/${id}`);
    },
    onSuccess: () => {
      toast({ title: "Alert deleted" });
      queryClient.invalidateQueries({ queryKey: ["/api/alerts"] });
    },
  });

  const checkAlerts = useMutation({
    mutationFn: async () => {
      const res = await apiRequest("POST", "/api/alerts/check");
      return res.json();
    },
    onSuccess: (data) => {
      const triggered = data.triggered?.length ?? 0;
      toast({
        title: triggered > 0 ? `${triggered} alert(s) triggered` : "No alerts triggered",
        description: `Checked ${data.checked} active alerts`,
      });
      queryClient.invalidateQueries({ queryKey: ["/api/alerts"] });
    },
  });

  const activeAlerts = (alerts ?? []).filter((a) => a.is_active && !a.is_triggered);
  const triggeredAlerts = (alerts ?? []).filter((a) => a.is_triggered);
  const inactiveAlerts = (alerts ?? []).filter((a) => !a.is_active && !a.is_triggered);

  return (
    <div className="space-y-4" data-testid="alerts-page">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Alerts</h1>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => checkAlerts.mutate()}
            disabled={checkAlerts.isPending}
            data-testid="btn-check-alerts"
            className="h-8 text-xs"
          >
            <Bell size={14} className="mr-1" />
            {checkAlerts.isPending ? "Checking..." : "Check Now"}
          </Button>
          <Button
            size="sm"
            onClick={() => setShowForm(!showForm)}
            data-testid="btn-new-alert"
            className="h-8 text-xs"
          >
            <Plus size={14} className="mr-1" />
            New Alert
          </Button>
        </div>
      </div>

      {/* Create Alert Form */}
      {showForm && (
        <Card className="border-card-border bg-card border-primary/30" data-testid="alert-form">
          <CardContent className="p-4 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Alert Type</Label>
                <Select value={alertType} onValueChange={setAlertType}>
                  <SelectTrigger className="h-9" data-testid="select-alert-type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ALERT_TYPES.map((t) => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {alertType.startsWith("price") && (
                <>
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">Symbol</Label>
                    <Input
                      data-testid="alert-input-symbol"
                      value={symbol}
                      onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                      className="h-9 font-mono text-sm"
                      placeholder="BTC-USDT"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">Exchange</Label>
                    <Select value={exchangeName} onValueChange={setExchangeName}>
                      <SelectTrigger className="h-9">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="binance">Binance</SelectItem>
                        <SelectItem value="bybit">Bybit</SelectItem>
                        <SelectItem value="kraken">Kraken</SelectItem>
                        <SelectItem value="coinbase">Coinbase</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </>
              )}

              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Threshold</Label>
                <Input
                  data-testid="alert-input-threshold"
                  value={threshold}
                  onChange={(e) => setThreshold(e.target.value)}
                  className="h-9 font-mono text-sm"
                  placeholder="70000"
                  type="number"
                  step="any"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Note (optional)</Label>
              <Input
                data-testid="alert-input-message"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                className="h-9 text-sm"
                placeholder="Alert note..."
              />
            </div>

            <div className="flex items-center gap-2 justify-end">
              <Button variant="outline" size="sm" onClick={() => setShowForm(false)} className="h-8 text-xs">
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={() => createAlert.mutate()}
                disabled={!threshold || createAlert.isPending}
                data-testid="btn-submit-alert"
                className="h-8 text-xs"
              >
                Create Alert
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Active Alerts */}
      <Card className="border-card-border bg-card" data-testid="active-alerts">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
            <Bell size={14} className="text-primary" />
            Active Alerts ({activeAlerts.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : activeAlerts.length === 0 ? (
            <p className="text-sm text-muted-foreground py-6 text-center">
              No active alerts. Create one to get started.
            </p>
          ) : (
            <div className="space-y-2">
              {activeAlerts.map((alert) => {
                const typeInfo = getAlertTypeInfo(alert.alert_type);
                const Icon = typeInfo.icon;
                return (
                  <div
                    key={alert.id}
                    data-testid={`alert-${alert.id}`}
                    className="flex items-center justify-between p-3 rounded-md bg-muted/20 border border-border/50 hover:bg-muted/30 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <Icon size={16} className={typeInfo.color} />
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium">{typeInfo.label}</span>
                          {alert.symbol && (
                            <Badge variant="outline" className="text-[10px] px-1.5 py-0 font-mono">
                              {alert.symbol}
                            </Badge>
                          )}
                          {alert.exchange_name && (
                            <span className="text-xs text-muted-foreground">{alert.exchange_name}</span>
                          )}
                        </div>
                        <p className="text-xs font-mono text-muted-foreground">
                          Threshold: {fmt.format(alert.threshold)}
                          {alert.message && ` · ${alert.message}`}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={alert.is_active}
                        onCheckedChange={(checked) =>
                          toggleAlert.mutate({ id: alert.id, is_active: checked })
                        }
                      />
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                        onClick={() => deleteAlert.mutate(alert.id)}
                      >
                        <Trash2 size={14} />
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Triggered Alerts */}
      {triggeredAlerts.length > 0 && (
        <Card className="border-card-border bg-card" data-testid="triggered-alerts">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
              <CheckCircle2 size={14} className="text-[hsl(var(--profit))]" />
              Triggered ({triggeredAlerts.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-2">
              {triggeredAlerts.map((alert) => {
                const typeInfo = getAlertTypeInfo(alert.alert_type);
                return (
                  <div
                    key={alert.id}
                    className="flex items-center justify-between p-3 rounded-md bg-[hsl(var(--profit))]/5 border border-[hsl(var(--profit))]/10"
                  >
                    <div>
                      <span className="text-sm font-medium">{typeInfo.label}</span>
                      {alert.symbol && (
                        <span className="text-xs text-muted-foreground ml-2">{alert.symbol}</span>
                      )}
                      <p className="text-xs text-muted-foreground">
                        Triggered: {alert.triggered_at ?? "—"}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                      onClick={() => deleteAlert.mutate(alert.id)}
                    >
                      <Trash2 size={14} />
                    </Button>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Inactive Alerts */}
      {inactiveAlerts.length > 0 && (
        <Card className="border-card-border bg-card" data-testid="inactive-alerts">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
              <BellOff size={14} />
              Inactive ({inactiveAlerts.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-2">
              {inactiveAlerts.map((alert) => {
                const typeInfo = getAlertTypeInfo(alert.alert_type);
                return (
                  <div
                    key={alert.id}
                    className="flex items-center justify-between p-3 rounded-md bg-muted/10 border border-border/30 opacity-60"
                  >
                    <div>
                      <span className="text-sm">{typeInfo.label}</span>
                      {alert.symbol && (
                        <span className="text-xs text-muted-foreground ml-2">{alert.symbol}</span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={alert.is_active}
                        onCheckedChange={(checked) =>
                          toggleAlert.mutate({ id: alert.id, is_active: checked })
                        }
                      />
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                        onClick={() => deleteAlert.mutate(alert.id)}
                      >
                        <Trash2 size={14} />
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
