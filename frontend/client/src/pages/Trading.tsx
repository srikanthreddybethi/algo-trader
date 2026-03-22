import { useState, useMemo, useRef, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useWebSocket, type PriceTicker } from "@/hooks/useWebSocket";
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
import { Skeleton } from "@/components/ui/skeleton";
import { Label } from "@/components/ui/label";
import { ArrowUpDown, X, TrendingUp, TrendingDown, CandlestickChart } from "lucide-react";
import { createChart, ColorType, CandlestickSeries, HistogramSeries, LineSeries } from "lightweight-charts";

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

const fmtPct = new Intl.NumberFormat("en-US", {
  style: "percent",
  minimumFractionDigits: 2,
  signDisplay: "always",
});

interface ExchangeStatus {
  name: string;
  connected: boolean;
  exchange_type: string;
}

interface Order {
  id: number;
  symbol: string;
  exchange_name: string;
  side: string;
  order_type: string;
  quantity: number;
  price: number | null;
  status: string;
  timestamp: string;
}

interface OrderBookEntry {
  price: number;
  quantity: number;
  amount?: number;
}

interface OrderBook {
  bids: OrderBookEntry[];
  asks: OrderBookEntry[];
  symbol: string;
  exchange: string;
}

interface OHLCVCandle {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

function CandlestickChartComponent({
  exchange,
  symbol,
  timeframe,
}: {
  exchange: string;
  symbol: string;
  timeframe: string;
}) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<any>(null);

  const { data: ohlcv } = useQuery<OHLCVCandle[]>({
    queryKey: ["/api/exchanges/ohlcv", exchange, symbol, timeframe],
    queryFn: async () => {
      const res = await apiRequest(
        "GET",
        `/api/exchanges/ohlcv/${exchange}/${symbol}?timeframe=${timeframe}&limit=200`
      );
      return res.json();
    },
    enabled: !!exchange && !!symbol,
    refetchInterval: 30000,
  });

  useEffect(() => {
    if (!chartRef.current || !ohlcv || ohlcv.length === 0) return;

    // Cleanup previous chart
    if (chartInstanceRef.current) {
      chartInstanceRef.current.remove();
      chartInstanceRef.current = null;
    }

    const chart = createChart(chartRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "hsl(0 0% 55%)",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "hsl(0 0% 16%)" },
        horzLines: { color: "hsl(0 0% 16%)" },
      },
      crosshair: {
        mode: 0,
      },
      rightPriceScale: {
        borderColor: "hsl(0 0% 16%)",
      },
      timeScale: {
        borderColor: "hsl(0 0% 16%)",
        timeVisible: true,
      },
      width: chartRef.current.clientWidth,
      height: 380,
    });

    chartInstanceRef.current = chart;

    // Candlestick series
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "hsl(142 72% 50%)",
      downColor: "hsl(0 84% 55%)",
      borderUpColor: "hsl(142 72% 50%)",
      borderDownColor: "hsl(0 84% 55%)",
      wickUpColor: "hsl(142 72% 50%)",
      wickDownColor: "hsl(0 84% 55%)",
    });

    const candleData = ohlcv.map((c) => ({
      time: Math.floor(c.timestamp / 1000) as any,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));
    candleSeries.setData(candleData);

    // Volume series (using Histogram)
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });

    const volumeData = ohlcv.map((c) => ({
      time: Math.floor(c.timestamp / 1000) as any,
      value: c.volume,
      color: c.close >= c.open ? "rgba(56, 199, 132, 0.2)" : "rgba(217, 48, 37, 0.2)",
    }));
    volumeSeries.setData(volumeData);

    // Simple moving average overlay (20-period)
    if (ohlcv.length >= 20) {
      const smaSeries = chart.addSeries(LineSeries, {
        color: "hsl(45 93% 55%)",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      const smaData: { time: any; value: number }[] = [];
      for (let i = 19; i < ohlcv.length; i++) {
        const sum = ohlcv.slice(i - 19, i + 1).reduce((s, c) => s + c.close, 0);
        smaData.push({
          time: Math.floor(ohlcv[i].timestamp / 1000) as any,
          value: sum / 20,
        });
      }
      smaSeries.setData(smaData);
    }

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartRef.current) {
        chart.applyOptions({ width: chartRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartInstanceRef.current = null;
    };
  }, [ohlcv]);

  return (
    <div ref={chartRef} className="w-full" data-testid="candlestick-chart" />
  );
}

export default function Trading() {
  const { toast } = useToast();
  const { getPrice } = useWebSocket();

  const [exchange, setExchange] = useState("");
  const [symbol, setSymbol] = useState("BTC-USDT");
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [orderType, setOrderType] = useState("market");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [timeframe, setTimeframe] = useState("1h");

  // Normalized symbol for exchange API (BTC-USDT -> BTC/USDT)
  const normalizedSymbol = symbol.replace("-", "/");

  // Available exchanges
  const { data: supportedExchanges } = useQuery<any[]>({
    queryKey: ["/api/exchanges/supported"],
  });

  const exchangeList = useMemo(
    () => (Array.isArray(supportedExchanges) ? supportedExchanges : []),
    [supportedExchanges]
  );

  // Auto-select first exchange
  useMemo(() => {
    if (!exchange && exchangeList.length > 0) {
      setExchange(exchangeList[0].name);
    }
  }, [exchangeList, exchange]);

  // Live price for selected pair
  const livePrice: PriceTicker | undefined = exchange
    ? getPrice(exchange, symbol)
    : undefined;

  // Fetch ticker from REST as fallback
  const { data: restTicker } = useQuery<PriceTicker>({
    queryKey: ["/api/exchanges/ticker", exchange, symbol],
    queryFn: async () => {
      const res = await apiRequest(
        "GET",
        `/api/exchanges/ticker/${exchange}/${symbol}`
      );
      return res.json();
    },
    enabled: !!exchange && !!symbol,
    refetchInterval: 5000,
  });

  const ticker = livePrice ?? restTicker;

  // Order book
  const { data: orderBook } = useQuery<OrderBook>({
    queryKey: ["/api/exchanges/orderbook", exchange, symbol],
    queryFn: async () => {
      const res = await apiRequest(
        "GET",
        `/api/exchanges/orderbook/${exchange}/${symbol}`
      );
      return res.json();
    },
    enabled: !!exchange && !!symbol,
    refetchInterval: 5000,
  });

  // Open orders
  const { data: orders, isLoading: ordersLoading } = useQuery<Order[]>({
    queryKey: ["/api/trading/orders"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/trading/orders?limit=50");
      return res.json();
    },
    refetchInterval: 5000,
  });

  const openOrders = (orders ?? []).filter(
    (o) => o.status === "open" || o.status === "pending"
  );

  // Place order mutation
  const placeOrder = useMutation({
    mutationFn: async () => {
      const body: Record<string, unknown> = {
        exchange_name: exchange,
        symbol,
        order_type: orderType,
        side,
        quantity: parseFloat(quantity),
      };
      if (orderType === "limit" && price) {
        body.price = parseFloat(price);
      }
      return apiRequest("POST", "/api/trading/orders", body);
    },
    onSuccess: () => {
      toast({ title: "Order placed", description: `${side.toUpperCase()} ${quantity} ${symbol}` });
      queryClient.invalidateQueries({ queryKey: ["/api/trading/orders"] });
      queryClient.invalidateQueries({ queryKey: ["/api/portfolio/summary"] });
      setQuantity("");
      setPrice("");
    },
    onError: (err: Error) => {
      toast({ title: "Order failed", description: err.message, variant: "destructive" });
    },
  });

  // Cancel order mutation
  const cancelOrder = useMutation({
    mutationFn: async (orderId: number) => {
      return apiRequest("POST", `/api/trading/orders/${orderId}/cancel`);
    },
    onSuccess: () => {
      toast({ title: "Order cancelled" });
      queryClient.invalidateQueries({ queryKey: ["/api/trading/orders"] });
      queryClient.invalidateQueries({ queryKey: ["/api/portfolio/summary"] });
    },
    onError: (err: Error) => {
      toast({ title: "Cancel failed", description: err.message, variant: "destructive" });
    },
  });

  // Order book viz helpers
  const maxBidVol = useMemo(() => {
    if (!orderBook?.bids?.length) return 1;
    return Math.max(...orderBook.bids.map((b) => (b.quantity ?? b.amount ?? 0)));
  }, [orderBook]);

  const maxAskVol = useMemo(() => {
    if (!orderBook?.asks?.length) return 1;
    return Math.max(...orderBook.asks.map((a) => (a.quantity ?? a.amount ?? 0)));
  }, [orderBook]);

  return (
    <div className="space-y-4" data-testid="trading-page">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Paper Trading</h1>
        <div className="flex items-center gap-2">
          <Select value={timeframe} onValueChange={setTimeframe}>
            <SelectTrigger className="h-8 w-20 text-xs" data-testid="select-timeframe">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1m">1m</SelectItem>
              <SelectItem value="5m">5m</SelectItem>
              <SelectItem value="15m">15m</SelectItem>
              <SelectItem value="1h">1H</SelectItem>
              <SelectItem value="4h">4H</SelectItem>
              <SelectItem value="1d">1D</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Candlestick Chart */}
      <Card className="border-card-border bg-card" data-testid="chart-card">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
            <CandlestickChart size={14} />
            {normalizedSymbol} · {exchange || "—"} · {timeframe}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-2">
          {exchange ? (
            <CandlestickChartComponent
              exchange={exchange}
              symbol={symbol}
              timeframe={timeframe}
            />
          ) : (
            <div className="h-[380px] flex items-center justify-center text-muted-foreground text-sm">
              Select an exchange to view chart
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left: Order Entry */}
        <Card className="border-card-border bg-card" data-testid="order-form">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Place Order
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Exchange */}
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Exchange</Label>
              <Select value={exchange} onValueChange={setExchange}>
                <SelectTrigger data-testid="select-exchange" className="h-9">
                  <SelectValue placeholder="Select exchange" />
                </SelectTrigger>
                <SelectContent>
                  {exchangeList.map((ex: any) => (
                    <SelectItem key={ex.name} value={ex.name}>
                      {ex.name}
                    </SelectItem>
                  ))}
                  {exchangeList.length === 0 && (
                    <SelectItem value="__none" disabled>
                      No exchanges available
                    </SelectItem>
                  )}
                </SelectContent>
              </Select>
            </div>

            {/* Symbol */}
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Symbol</Label>
              <Input
                data-testid="input-symbol"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                placeholder="BTC-USDT"
                className="h-9 font-mono text-sm"
              />
            </div>

            {/* Buy/Sell Toggle */}
            <div className="grid grid-cols-2 gap-2">
              <Button
                data-testid="btn-buy"
                variant={side === "buy" ? "default" : "outline"}
                onClick={() => setSide("buy")}
                className={`h-9 text-sm font-semibold ${
                  side === "buy"
                    ? "bg-[hsl(var(--profit))] hover:bg-[hsl(var(--profit))]/90 text-black"
                    : ""
                }`}
              >
                <TrendingUp size={14} className="mr-1" />
                Buy
              </Button>
              <Button
                data-testid="btn-sell"
                variant={side === "sell" ? "default" : "outline"}
                onClick={() => setSide("sell")}
                className={`h-9 text-sm font-semibold ${
                  side === "sell"
                    ? "bg-[hsl(var(--loss))] hover:bg-[hsl(var(--loss))]/90 text-white"
                    : ""
                }`}
              >
                <TrendingDown size={14} className="mr-1" />
                Sell
              </Button>
            </div>

            {/* Order Type */}
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">
                Order Type
              </Label>
              <Select value={orderType} onValueChange={setOrderType}>
                <SelectTrigger data-testid="select-order-type" className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="market">Market</SelectItem>
                  <SelectItem value="limit">Limit</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Quantity */}
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Quantity</Label>
              <Input
                data-testid="input-quantity"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                placeholder="0.001"
                type="number"
                step="any"
                className="h-9 font-mono text-sm"
              />
            </div>

            {/* Price (limit only) */}
            {orderType === "limit" && (
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Price</Label>
                <Input
                  data-testid="input-price"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  placeholder="0.00"
                  type="number"
                  step="any"
                  className="h-9 font-mono text-sm"
                />
              </div>
            )}

            {/* Submit */}
            <Button
              data-testid="btn-submit-order"
              className="w-full h-10 font-semibold"
              disabled={!exchange || !symbol || !quantity || placeOrder.isPending}
              onClick={() => placeOrder.mutate()}
            >
              {placeOrder.isPending ? (
                "Placing..."
              ) : (
                <>
                  <ArrowUpDown size={14} className="mr-1.5" />
                  {side === "buy" ? "Buy" : "Sell"} {symbol}
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Right: Price Ticker + Orderbook */}
        <div className="lg:col-span-2 space-y-4">
          {/* Live Ticker */}
          <Card className="border-card-border bg-card" data-testid="live-ticker">
            <CardContent className="p-4">
              {!ticker ? (
                <div className="flex items-center gap-6">
                  <Skeleton className="h-10 w-32" />
                  <Skeleton className="h-6 w-20" />
                  <Skeleton className="h-6 w-20" />
                </div>
              ) : (
                <div className="flex flex-wrap items-center gap-6">
                  <div>
                    <p className="text-xs text-muted-foreground mb-0.5">
                      {symbol} · {exchange}
                    </p>
                    <p className="text-xl font-mono font-semibold">
                      {fmt.format((ticker as any).last_price ?? ticker.last ?? 0)}
                    </p>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                    <div>
                      <p className="text-[10px] text-muted-foreground uppercase">
                        Bid
                      </p>
                      <p className="font-mono text-[hsl(var(--profit))]">
                        {fmt.format(ticker.bid ?? 0)}
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] text-muted-foreground uppercase">
                        Ask
                      </p>
                      <p className="font-mono text-[hsl(var(--loss))]">
                        {fmt.format(ticker.ask ?? 0)}
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] text-muted-foreground uppercase">
                        24h High
                      </p>
                      <p className="font-mono">{fmt.format((ticker as any).high_24h ?? ticker.high ?? 0)}</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-muted-foreground uppercase">
                        24h Change
                      </p>
                      <p
                        className={`font-mono ${
                          ((ticker as any).change_pct_24h ?? ticker.changePercent ?? 0) >= 0
                            ? "text-[hsl(var(--profit))]"
                            : "text-[hsl(var(--loss))]"
                        }`}
                      >
                        {fmtPct.format(((ticker as any).change_pct_24h ?? ticker.changePercent ?? 0) / 100)}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Order Book */}
          <Card className="border-card-border bg-card" data-testid="order-book">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Order Book
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="grid grid-cols-2 gap-4">
                {/* Bids */}
                <div>
                  <div className="flex justify-between text-[10px] text-muted-foreground uppercase mb-1.5 px-1">
                    <span>Price</span>
                    <span>Amount</span>
                  </div>
                  <div className="space-y-px">
                    {(orderBook?.bids ?? []).slice(0, 12).map((bid, i) => (
                      <div
                        key={i}
                        className="relative flex justify-between py-0.5 px-1 text-xs font-mono"
                      >
                        <div
                          className="absolute inset-0 bg-[hsl(var(--profit))]/8 rounded-sm"
                          style={{
                            width: `${((bid.quantity ?? bid.amount ?? 0) / maxBidVol) * 100}%`,
                            right: 0,
                            left: "auto",
                          }}
                        />
                        <span className="relative text-[hsl(var(--profit))]">
                          {fmtNum.format(bid.price)}
                        </span>
                        <span className="relative text-muted-foreground">
                          {fmtNum.format((bid.quantity ?? bid.amount ?? 0))}
                        </span>
                      </div>
                    ))}
                    {(!orderBook?.bids || orderBook.bids.length === 0) && (
                      <p className="text-xs text-muted-foreground text-center py-4">
                        No bids
                      </p>
                    )}
                  </div>
                </div>

                {/* Asks */}
                <div>
                  <div className="flex justify-between text-[10px] text-muted-foreground uppercase mb-1.5 px-1">
                    <span>Price</span>
                    <span>Amount</span>
                  </div>
                  <div className="space-y-px">
                    {(orderBook?.asks ?? []).slice(0, 12).map((ask, i) => (
                      <div
                        key={i}
                        className="relative flex justify-between py-0.5 px-1 text-xs font-mono"
                      >
                        <div
                          className="absolute inset-0 bg-[hsl(var(--loss))]/8 rounded-sm"
                          style={{
                            width: `${((ask.quantity ?? ask.amount ?? 0) / maxAskVol) * 100}%`,
                          }}
                        />
                        <span className="relative text-[hsl(var(--loss))]">
                          {fmtNum.format(ask.price)}
                        </span>
                        <span className="relative text-muted-foreground">
                          {fmtNum.format((ask.quantity ?? ask.amount ?? 0))}
                        </span>
                      </div>
                    ))}
                    {(!orderBook?.asks || orderBook.asks.length === 0) && (
                      <p className="text-xs text-muted-foreground text-center py-4">
                        No asks
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Open Orders */}
      <Card className="border-card-border bg-card" data-testid="open-orders">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Open Orders
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {ordersLoading ? (
            <div className="p-4 space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : openOrders.length === 0 ? (
            <p className="text-sm text-muted-foreground p-6 text-center">
              No open orders
            </p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent border-border">
                    <TableHead className="text-xs text-muted-foreground">
                      Symbol
                    </TableHead>
                    <TableHead className="text-xs text-muted-foreground">
                      Exchange
                    </TableHead>
                    <TableHead className="text-xs text-muted-foreground">
                      Side
                    </TableHead>
                    <TableHead className="text-xs text-muted-foreground">
                      Type
                    </TableHead>
                    <TableHead className="text-xs text-muted-foreground text-right">
                      Qty
                    </TableHead>
                    <TableHead className="text-xs text-muted-foreground text-right">
                      Price
                    </TableHead>
                    <TableHead className="text-xs text-muted-foreground">
                      Status
                    </TableHead>
                    <TableHead className="text-xs text-muted-foreground w-16" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {openOrders.map((order) => (
                    <TableRow
                      key={order.id}
                      data-testid={`open-order-${order.id}`}
                      className="border-border hover:bg-muted/30"
                    >
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
                        {order.price ? fmt.format(order.price) : "MKT"}
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                          {order.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Button
                          data-testid={`cancel-order-${order.id}`}
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0 text-muted-foreground hover:text-destructive"
                          onClick={() => cancelOrder.mutate(order.id)}
                          disabled={cancelOrder.isPending}
                        >
                          <X size={14} />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
