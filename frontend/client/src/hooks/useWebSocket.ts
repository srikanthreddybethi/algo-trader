import { useState, useEffect, useRef, useCallback } from "react";

export interface PriceTicker {
  symbol: string;
  exchange: string;
  last: number;
  bid: number;
  ask: number;
  high: number;
  low: number;
  volume: number;
  change: number;
  changePercent: number;
  timestamp: string;
}

interface WebSocketMessage {
  type: string;
  data: PriceTicker[];
}

const WS_BASE = "__PORT_8000__".startsWith("__") ? "" : "__PORT_8000__";

export function useWebSocket() {
  const [prices, setPrices] = useState<Record<string, PriceTicker>>({});
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = WS_BASE
        ? `${WS_BASE.replace(/^http/, "ws")}/ws/prices`
        : `${protocol}//${window.location.host}/ws/prices`;

      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        if (mountedRef.current) {
          setConnected(true);
        }
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          if (message.type === "price_update" && Array.isArray(message.data)) {
            setPrices((prev) => {
              const next = { ...prev };
              for (const ticker of message.data) {
                const key = `${ticker.exchange}:${ticker.symbol}`;
                next[key] = ticker;
              }
              return next;
            });
          }
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        if (mountedRef.current) {
          setConnected(false);
          reconnectTimerRef.current = setTimeout(() => {
            if (mountedRef.current) connect();
          }, 3000);
        }
      };

      ws.onerror = () => {
        ws.close();
      };

      wsRef.current = ws;
    } catch {
      // connection failed, retry
      reconnectTimerRef.current = setTimeout(() => {
        if (mountedRef.current) connect();
      }, 3000);
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const priceList = Object.values(prices);

  const getPrice = useCallback(
    (exchange: string, symbol: string): PriceTicker | undefined => {
      return prices[`${exchange}:${symbol}`];
    },
    [prices]
  );

  return { prices: priceList, priceMap: prices, connected, getPrice };
}
