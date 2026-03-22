import { useState, useMemo } from "react";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Plug,
  Unplug,
  ChevronDown,
  Key,
  Shield,
  TrendingUp,
  Wifi,
  WifiOff,
  Search,
} from "lucide-react";

// ── Formatters ───────────────────────────────────────────────────────────────

const fmt = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const fmtCompact = (n: number) => {
  if (Math.abs(n) < 1) return n.toFixed(5);
  if (Math.abs(n) < 10) return n.toFixed(4);
  return fmt.format(n);
};

const fmtPct = new Intl.NumberFormat("en-US", {
  style: "percent",
  minimumFractionDigits: 2,
  signDisplay: "always",
});

// ── Types ────────────────────────────────────────────────────────────────────

interface ConfigField {
  name: string;
  label: string;
  type: "text" | "password" | "boolean";
  required?: boolean;
  default?: boolean | string;
}

interface SupportedExchange {
  name: string;
  type: string;
  category: string;
  display_name: string;
  fca_status: string;
  has_testnet: boolean;
  default_pairs: string[];
  tax_free?: boolean;
  config_fields?: ConfigField[];
  supported_asset_types?: string[];
  status?: string;
}

interface Ticker {
  symbol: string;
  last_price?: number;
  last?: number;
  bid?: number;
  ask?: number;
  high_24h?: number;
  low_24h?: number;
  volume_24h?: number;
  change_pct_24h?: number;
  changePercent?: number;
}

// ── Category configuration ───────────────────────────────────────────────────

type Category = "all" | "crypto" | "spread_betting" | "stocks" | "forex" | "multi_asset";

const CATEGORIES: { key: Category; label: string }[] = [
  { key: "all", label: "All" },
  { key: "crypto", label: "Crypto" },
  { key: "spread_betting", label: "Spread Betting" },
  { key: "stocks", label: "Stocks" },
  { key: "forex", label: "Forex" },
  { key: "multi_asset", label: "Multi-Asset" },
];

const CATEGORY_COLORS: Record<string, { bg: string; text: string; iconBg: string }> = {
  crypto:         { bg: "bg-teal-500/15",    text: "text-teal-400",    iconBg: "bg-teal-500/20" },
  spread_betting: { bg: "bg-amber-500/15",   text: "text-amber-400",   iconBg: "bg-amber-500/20" },
  stocks:         { bg: "bg-blue-500/15",     text: "text-blue-400",    iconBg: "bg-blue-500/20" },
  forex:          { bg: "bg-purple-500/15",   text: "text-purple-400",  iconBg: "bg-purple-500/20" },
  multi_asset:    { bg: "bg-emerald-500/15",  text: "text-emerald-400", iconBg: "bg-emerald-500/20" },
};

function getCategoryStyle(category: string) {
  return CATEGORY_COLORS[category] ?? CATEGORY_COLORS.crypto;
}

// ── Exchange icon ────────────────────────────────────────────────────────────

function ExchangeIcon({ name, category }: { name: string; category: string }) {
  const style = getCategoryStyle(category);
  const abbr = name.slice(0, 2).toUpperCase();
  return (
    <div
      className={`w-9 h-9 rounded-lg ${style.iconBg} flex items-center justify-center text-xs font-bold ${style.text}`}
    >
      {abbr}
    </div>
  );
}

// ── Category label helper ────────────────────────────────────────────────────

function categoryLabel(cat: string): string {
  return cat
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

// ── Exchange Card ────────────────────────────────────────────────────────────

function ExchangeCard({
  exchange,
  isConnected,
}: {
  exchange: SupportedExchange;
  isConnected: boolean;
}) {
  const { toast } = useToast();
  const [showCreds, setShowCreds] = useState(false);
  const [formValues, setFormValues] = useState<Record<string, string | boolean>>(() => {
    const init: Record<string, string | boolean> = {};
    for (const f of exchange.config_fields ?? []) {
      if (f.type === "boolean") {
        init[f.name] = f.default ?? true;
      } else {
        init[f.name] = (f.default as string) ?? "";
      }
    }
    return init;
  });

  // Fallback config fields for ccxt exchanges without config_fields
  const configFields: ConfigField[] = useMemo(() => {
    if (exchange.config_fields && exchange.config_fields.length > 0) {
      return exchange.config_fields;
    }
    // Default ccxt fields
    return [
      { name: "api_key", label: "API Key", type: "text" as const, required: false },
      { name: "api_secret", label: "API Secret", type: "password" as const, required: false },
      { name: "is_testnet", label: "Testnet / Paper", type: "boolean" as const, default: true },
    ];
  }, [exchange.config_fields]);

  const setField = (fieldName: string, value: string | boolean) => {
    setFormValues((prev) => ({ ...prev, [fieldName]: value }));
  };

  // Build the request body from form values
  const buildBody = () => {
    const body: Record<string, unknown> = { name: exchange.name };
    for (const f of configFields) {
      const val = formValues[f.name];
      if (f.type === "boolean") {
        body[f.name] = val;
        // Map is_demo → is_testnet for the backend schema
        if (f.name === "is_demo") {
          body["is_testnet"] = val;
        }
      } else if (typeof val === "string" && val.trim() !== "") {
        body[f.name] = val;
      }
    }
    // Ensure is_testnet is always sent
    if (!("is_testnet" in body)) {
      body["is_testnet"] = formValues["is_demo"] ?? formValues["is_testnet"] ?? true;
    }
    return body;
  };

  const connectMutation = useMutation({
    mutationFn: async () => {
      return apiRequest("POST", `/api/exchanges/connect/${exchange.name}`, buildBody());
    },
    onSuccess: () => {
      toast({ title: `Connected to ${exchange.display_name}` });
      queryClient.invalidateQueries({ queryKey: ["/api/exchanges/status"] });
    },
    onError: (err: Error) => {
      toast({ title: "Connection failed", description: err.message, variant: "destructive" });
    },
  });

  const disconnectMutation = useMutation({
    mutationFn: async () => {
      return apiRequest("POST", `/api/exchanges/disconnect/${exchange.name}`);
    },
    onSuccess: () => {
      toast({ title: `Disconnected from ${exchange.display_name}` });
      queryClient.invalidateQueries({ queryKey: ["/api/exchanges/status"] });
    },
    onError: (err: Error) => {
      toast({ title: "Disconnect failed", description: err.message, variant: "destructive" });
    },
  });

  // Fetch tickers when connected
  const { data: tickers, isLoading: tickersLoading } = useQuery<Ticker[]>({
    queryKey: ["/api/exchanges/tickers", exchange.name],
    queryFn: async () => {
      const res = await apiRequest("GET", `/api/exchanges/tickers/${exchange.name}`);
      return res.json();
    },
    enabled: isConnected,
    refetchInterval: 10000,
  });

  const catStyle = getCategoryStyle(exchange.category);

  return (
    <Card
      data-testid={`exchange-card-${exchange.name}`}
      className="border-card-border bg-card"
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          {/* Left: icon + name + badges */}
          <div className="flex items-center gap-3">
            <ExchangeIcon name={exchange.display_name} category={exchange.category} />
            <div>
              <CardTitle className="text-sm font-semibold">
                {exchange.display_name}
              </CardTitle>
              <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                {/* Category badge */}
                <Badge
                  variant="secondary"
                  className={`text-[10px] px-1.5 py-0 ${catStyle.bg} ${catStyle.text} border-0`}
                >
                  {categoryLabel(exchange.category)}
                </Badge>
                {/* FCA badge */}
                <Badge
                  variant="outline"
                  className={`text-[10px] px-1.5 py-0 ${
                    exchange.fca_status.toLowerCase().includes("fca")
                      ? "text-green-400 border-green-500/30"
                      : "text-yellow-400 border-yellow-500/30"
                  }`}
                >
                  <Shield size={8} className="mr-0.5" />
                  {exchange.fca_status.length > 20
                    ? exchange.fca_status.slice(0, 18) + "…"
                    : exchange.fca_status}
                </Badge>
                {/* Tax-free badge */}
                {exchange.tax_free && (
                  <Badge
                    variant="outline"
                    className="text-[10px] px-1.5 py-0 text-green-400 border-green-500/30"
                  >
                    Tax-Free
                  </Badge>
                )}
              </div>
            </div>
          </div>

          {/* Right: status dot */}
          <div className="flex items-center gap-1.5 shrink-0">
            <div
              data-testid={`status-${exchange.name}`}
              className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-400" : "bg-red-400"}`}
            />
            <span className="text-[10px] text-muted-foreground">
              {isConnected ? "Online" : "Offline"}
            </span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Credential form (only when disconnected) */}
        {!isConnected && (
          <Collapsible open={showCreds} onOpenChange={setShowCreds}>
            <CollapsibleTrigger asChild>
              <Button
                data-testid={`toggle-keys-${exchange.name}`}
                variant="ghost"
                size="sm"
                className="h-7 text-xs text-muted-foreground px-2"
              >
                <Key size={12} className="mr-1" />
                Credentials
                <ChevronDown
                  size={12}
                  className={`ml-1 transition-transform ${showCreds ? "rotate-180" : ""}`}
                />
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-2 pt-2">
              {configFields.map((field) => (
                <div key={field.name} className="space-y-1">
                  <Label className="text-[10px] text-muted-foreground">
                    {field.label}
                    {field.required && <span className="text-red-400 ml-0.5">*</span>}
                  </Label>
                  {field.type === "boolean" ? (
                    <div className="flex items-center gap-2 h-7">
                      <Switch
                        data-testid={`input-${field.name}-${exchange.name}`}
                        checked={formValues[field.name] as boolean}
                        onCheckedChange={(v) => setField(field.name, v)}
                      />
                      <span className="text-xs text-muted-foreground">
                        {formValues[field.name] ? "Yes" : "No"}
                      </span>
                    </div>
                  ) : (
                    <Input
                      data-testid={`input-${field.name}-${exchange.name}`}
                      type={field.type === "password" ? "password" : "text"}
                      value={(formValues[field.name] as string) ?? ""}
                      onChange={(e) => setField(field.name, e.target.value)}
                      placeholder={field.required ? "Required" : "Optional"}
                      className="h-7 text-xs font-mono"
                    />
                  )}
                </div>
              ))}
            </CollapsibleContent>
          </Collapsible>
        )}

        {/* Connect / Disconnect button */}
        {isConnected ? (
          <Button
            data-testid={`disconnect-${exchange.name}`}
            variant="outline"
            size="sm"
            className="w-full h-8 text-xs"
            onClick={() => disconnectMutation.mutate()}
            disabled={disconnectMutation.isPending}
          >
            <Unplug size={12} className="mr-1.5" />
            {disconnectMutation.isPending ? "Disconnecting…" : "Disconnect"}
          </Button>
        ) : (
          <Button
            data-testid={`connect-${exchange.name}`}
            size="sm"
            className="w-full h-8 text-xs"
            onClick={() => connectMutation.mutate()}
            disabled={connectMutation.isPending}
          >
            <Plug size={12} className="mr-1.5" />
            {connectMutation.isPending ? "Connecting…" : "Connect"}
          </Button>
        )}

        {/* Tickers table when connected */}
        {isConnected && (
          <div className="border border-border rounded-md overflow-hidden">
            {tickersLoading ? (
              <div className="p-3 space-y-1.5">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-5 w-full" />
                ))}
              </div>
            ) : !tickers || tickers.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center p-4">
                No tickers available
              </p>
            ) : (
              <ScrollArea className="h-[200px]">
                <Table>
                  <TableHeader>
                    <TableRow className="hover:bg-transparent border-border">
                      <TableHead className="text-[10px] text-muted-foreground h-7">
                        Pair
                      </TableHead>
                      <TableHead className="text-[10px] text-muted-foreground h-7 text-right">
                        Price
                      </TableHead>
                      <TableHead className="text-[10px] text-muted-foreground h-7 text-right">
                        24h
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {tickers.slice(0, 20).map((t) => {
                      const price = t.last_price ?? t.last ?? 0;
                      const changePct = t.change_pct_24h ?? t.changePercent ?? 0;
                      return (
                        <TableRow
                          key={t.symbol}
                          data-testid={`ticker-${exchange.name}-${t.symbol}`}
                          className="border-border hover:bg-muted/30"
                        >
                          <TableCell className="text-xs font-medium py-1.5">
                            {t.symbol}
                          </TableCell>
                          <TableCell className="text-xs font-mono text-right py-1.5">
                            {fmtCompact(price)}
                          </TableCell>
                          <TableCell
                            className={`text-xs font-mono text-right py-1.5 ${
                              changePct >= 0
                                ? "text-[hsl(var(--profit))]"
                                : "text-[hsl(var(--loss))]"
                            }`}
                          >
                            {fmtPct.format(changePct / 100)}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </ScrollArea>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────

export default function Exchanges() {
  const [activeCategory, setActiveCategory] = useState<Category>("all");
  const [searchQuery, setSearchQuery] = useState("");

  const { data: supported, isLoading: supportedLoading } = useQuery<SupportedExchange[]>({
    queryKey: ["/api/exchanges/supported"],
  });

  const { data: statuses } = useQuery<Record<string, Record<string, unknown>>>({
    queryKey: ["/api/exchanges/status"],
    refetchInterval: 10000,
  });

  const statusObj =
    statuses && typeof statuses === "object" && !Array.isArray(statuses) ? statuses : {};

  // Merge supported list with live status
  const allExchanges = useMemo(() => {
    return (supported ?? []).map((ex) => ({
      ...ex,
      isConnected: statusObj[ex.name]?.status === "connected",
    }));
  }, [supported, statusObj]);

  // Filter by category + search
  const filtered = useMemo(() => {
    return allExchanges.filter((ex) => {
      if (activeCategory !== "all" && ex.category !== activeCategory) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        return (
          ex.display_name.toLowerCase().includes(q) ||
          ex.name.toLowerCase().includes(q) ||
          ex.category.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [allExchanges, activeCategory, searchQuery]);

  // Stats
  const totalExchanges = allExchanges.length;
  const connectedCount = allExchanges.filter((e) => e.isConnected).length;
  const categoriesAvailable = new Set(allExchanges.map((e) => e.category)).size;

  return (
    <div className="space-y-4" data-testid="exchanges-page">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Exchanges</h1>
      </div>

      {/* Summary stats bar */}
      <div
        data-testid="exchange-stats"
        className="grid grid-cols-3 gap-3"
      >
        <div className="flex items-center gap-3 p-3 rounded-md bg-muted/30 border border-border/50">
          <div className="p-1.5 rounded bg-primary/10">
            <TrendingUp size={14} className="text-primary" />
          </div>
          <div>
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
              Total Exchanges
            </p>
            <p className="text-sm font-mono font-medium">{totalExchanges}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 p-3 rounded-md bg-muted/30 border border-border/50">
          <div className="p-1.5 rounded bg-green-500/10">
            <Wifi size={14} className="text-green-400" />
          </div>
          <div>
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
              Connected
            </p>
            <p className="text-sm font-mono font-medium">
              <span className="text-green-400">{connectedCount}</span>
              <span className="text-muted-foreground"> / {totalExchanges}</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3 p-3 rounded-md bg-muted/30 border border-border/50">
          <div className="p-1.5 rounded bg-purple-500/10">
            <Shield size={14} className="text-purple-400" />
          </div>
          <div>
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
              Categories
            </p>
            <p className="text-sm font-mono font-medium">{categoriesAvailable}</p>
          </div>
        </div>
      </div>

      {/* Category filter tabs + search */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div
          data-testid="category-tabs"
          className="flex items-center gap-1 p-1 rounded-lg bg-muted/30 border border-border/50"
        >
          {CATEGORIES.map(({ key, label }) => {
            const isActive = activeCategory === key;
            const count =
              key === "all"
                ? allExchanges.length
                : allExchanges.filter((e) => e.category === key).length;
            return (
              <button
                key={key}
                data-testid={`filter-${key}`}
                onClick={() => setActiveCategory(key)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                }`}
              >
                {label}
                <span
                  className={`ml-1.5 text-[10px] ${
                    isActive ? "text-primary-foreground/70" : "text-muted-foreground/60"
                  }`}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>
        <div className="relative">
          <Search
            size={14}
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground"
          />
          <Input
            data-testid="exchange-search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search exchanges…"
            className="h-8 w-48 pl-8 text-xs"
          />
        </div>
      </div>

      {/* Exchange cards grid */}
      {supportedLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i} className="border-card-border bg-card">
              <CardContent className="p-4 space-y-3">
                <div className="flex items-center gap-3">
                  <Skeleton className="h-9 w-9 rounded-lg" />
                  <div className="space-y-1.5">
                    <Skeleton className="h-4 w-28" />
                    <Skeleton className="h-3 w-36" />
                  </div>
                </div>
                <Skeleton className="h-8 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <Card className="border-card-border bg-card">
          <CardContent className="p-8 text-center">
            <WifiOff size={24} className="mx-auto text-muted-foreground mb-2" />
            <p className="text-muted-foreground text-sm">
              {allExchanges.length === 0
                ? "No exchanges available. Make sure the backend is running."
                : "No exchanges match your filter."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((ex) => (
            <ExchangeCard
              key={ex.name}
              exchange={ex}
              isConnected={ex.isConnected}
            />
          ))}
        </div>
      )}
    </div>
  );
}
