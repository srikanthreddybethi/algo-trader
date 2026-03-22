import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { BarChart3, TrendingUp, DollarSign } from "lucide-react";
import { format } from "date-fns";

const fmt = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const fmtNum = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 8,
});

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
  status?: string;
}

interface Order {
  id: number;
  symbol: string;
  exchange_name: string;
  side: string;
  order_type: string;
  quantity: number;
  price: number | null;
  filled_price: number | null;
  status: string;
  created_at: string;
  filled_quantity?: number;
}

function StatCard({
  title,
  value,
  icon: Icon,
  testId,
}: {
  title: string;
  value: string;
  icon: typeof BarChart3;
  testId: string;
}) {
  return (
    <Card className="border-card-border bg-card" data-testid={testId}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              {title}
            </p>
            <p className="text-lg font-semibold font-mono">{value}</p>
          </div>
          <div className="p-2 rounded-md bg-primary/10">
            <Icon size={14} className="text-primary" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function TradesTable({
  trades,
  loading,
}: {
  trades: Trade[];
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="p-4 space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  if (trades.length === 0) {
    return (
      <p className="text-sm text-muted-foreground p-8 text-center">
        No trades recorded yet
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent border-border">
            <TableHead className="text-xs text-muted-foreground font-medium">
              Date
            </TableHead>
            <TableHead className="text-xs text-muted-foreground font-medium">
              Symbol
            </TableHead>
            <TableHead className="text-xs text-muted-foreground font-medium">
              Exchange
            </TableHead>
            <TableHead className="text-xs text-muted-foreground font-medium">
              Side
            </TableHead>
            <TableHead className="text-xs text-muted-foreground font-medium text-right">
              Quantity
            </TableHead>
            <TableHead className="text-xs text-muted-foreground font-medium text-right">
              Price
            </TableHead>
            <TableHead className="text-xs text-muted-foreground font-medium text-right">
              Fee
            </TableHead>
            <TableHead className="text-xs text-muted-foreground font-medium text-right">
              Total
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {trades.map((trade) => (
            <TableRow
              key={trade.id}
              data-testid={`trade-row-${trade.id}`}
              className="border-border hover:bg-muted/30"
            >
              <TableCell className="text-xs text-muted-foreground font-mono">
                {trade.executed_at
                  ? format(new Date(trade.executed_at), "MMM dd, HH:mm")
                  : "—"}
              </TableCell>
              <TableCell className="text-sm font-medium">
                {trade.symbol}
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {trade.exchange_name}
              </TableCell>
              <TableCell>
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
              </TableCell>
              <TableCell className="text-right font-mono text-sm">
                {fmtNum.format(trade.quantity)}
              </TableCell>
              <TableCell className="text-right font-mono text-sm">
                {fmt.format(trade.price)}
              </TableCell>
              <TableCell className="text-right font-mono text-xs text-muted-foreground">
                {fmt.format(trade.fee ?? 0)}
              </TableCell>
              <TableCell className="text-right font-mono text-sm">
                {fmt.format(
                  trade.total_cost ?? trade.price * trade.quantity
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function OrdersTable({
  orders,
  loading,
}: {
  orders: Order[];
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="p-4 space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  if (orders.length === 0) {
    return (
      <p className="text-sm text-muted-foreground p-8 text-center">
        No orders recorded yet
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent border-border">
            <TableHead className="text-xs text-muted-foreground font-medium">
              Date
            </TableHead>
            <TableHead className="text-xs text-muted-foreground font-medium">
              Symbol
            </TableHead>
            <TableHead className="text-xs text-muted-foreground font-medium">
              Exchange
            </TableHead>
            <TableHead className="text-xs text-muted-foreground font-medium">
              Side
            </TableHead>
            <TableHead className="text-xs text-muted-foreground font-medium">
              Type
            </TableHead>
            <TableHead className="text-xs text-muted-foreground font-medium text-right">
              Quantity
            </TableHead>
            <TableHead className="text-xs text-muted-foreground font-medium text-right">
              Price
            </TableHead>
            <TableHead className="text-xs text-muted-foreground font-medium">
              Status
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {orders.map((order) => (
            <TableRow
              key={order.id}
              data-testid={`order-row-${order.id}`}
              className="border-border hover:bg-muted/30"
            >
              <TableCell className="text-xs text-muted-foreground font-mono">
                {order.created_at
                  ? format(new Date(order.created_at), "MMM dd, HH:mm")
                  : "—"}
              </TableCell>
              <TableCell className="text-sm font-medium">
                {order.symbol}
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {order.exchange_name}
              </TableCell>
              <TableCell>
                <Badge
                  variant="outline"
                  className={`text-[10px] px-1.5 py-0 font-mono uppercase ${
                    order.side === "buy"
                      ? "text-[hsl(var(--profit))] border-[hsl(var(--profit))]/30"
                      : "text-[hsl(var(--loss))] border-[hsl(var(--loss))]/30"
                  }`}
                >
                  {order.side}
                </Badge>
              </TableCell>
              <TableCell className="text-xs text-muted-foreground capitalize">
                {order.order_type}
              </TableCell>
              <TableCell className="text-right font-mono text-sm">
                {fmtNum.format(order.quantity)}
              </TableCell>
              <TableCell className="text-right font-mono text-sm">
                {order.filled_price
                  ? fmt.format(order.filled_price)
                  : order.price
                  ? fmt.format(order.price)
                  : "MKT"}
              </TableCell>
              <TableCell>
                <Badge
                  variant={
                    order.status === "filled"
                      ? "default"
                      : order.status === "cancelled"
                      ? "destructive"
                      : "secondary"
                  }
                  className="text-[10px] px-1.5 py-0 capitalize"
                >
                  {order.status}
                </Badge>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

export default function TradeHistory() {
  const { data: trades, isLoading: tradesLoading } = useQuery<Trade[]>({
    queryKey: ["/api/trading/trades"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/trading/trades?limit=50");
      return res.json();
    },
  });

  const { data: orders, isLoading: ordersLoading } = useQuery<Order[]>({
    queryKey: ["/api/trading/orders"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/trading/orders?limit=50");
      return res.json();
    },
  });

  const totalTrades = trades?.length ?? 0;
  const totalFees = (trades ?? []).reduce((sum, t) => sum + (t.fee ?? 0), 0);

  // Win rate placeholder
  const winRate = "—";

  return (
    <div className="space-y-4" data-testid="trade-history-page">
      <h1 className="text-xl font-semibold">Trade History</h1>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <StatCard
          testId="stat-total-trades"
          title="Total Trades"
          value={tradesLoading ? "—" : totalTrades.toString()}
          icon={BarChart3}
        />
        <StatCard
          testId="stat-win-rate"
          title="Win Rate"
          value={winRate}
          icon={TrendingUp}
        />
        <StatCard
          testId="stat-total-fees"
          title="Total Fees Paid"
          value={tradesLoading ? "—" : fmt.format(totalFees)}
          icon={DollarSign}
        />
      </div>

      {/* Tabs: Trades / Orders */}
      <Card className="border-card-border bg-card">
        <Tabs defaultValue="trades">
          <div className="px-4 pt-3">
            <TabsList className="bg-muted/50">
              <TabsTrigger
                data-testid="tab-trades"
                value="trades"
                className="text-xs"
              >
                All Trades
              </TabsTrigger>
              <TabsTrigger
                data-testid="tab-orders"
                value="orders"
                className="text-xs"
              >
                Orders
              </TabsTrigger>
            </TabsList>
          </div>
          <TabsContent value="trades" className="mt-0">
            <TradesTable trades={trades ?? []} loading={tradesLoading} />
          </TabsContent>
          <TabsContent value="orders" className="mt-0">
            <OrdersTable orders={orders ?? []} loading={ordersLoading} />
          </TabsContent>
        </Tabs>
      </Card>
    </div>
  );
}
