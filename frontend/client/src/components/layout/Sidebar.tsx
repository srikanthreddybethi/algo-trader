import { useState } from "react";
import { useLocation, Link } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import {
  LayoutDashboard,
  LineChart,
  Globe,
  History,
  FlaskConical,
  ChartPie,
  Brain,
  Bot,
  Cpu,
  Bell,
  AlertTriangle,
  Crosshair,
  ShieldCheck,
  Globe2,
  PoundSterling,
  Settings2,
  ChevronLeft,
  ChevronRight,
  Wifi,
  WifiOff,
} from "lucide-react";
import { useWebSocket } from "@/hooks/useWebSocket";
import { cn } from "@/lib/utils";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

const navItems = [
  { path: "/", label: "Dashboard", icon: LayoutDashboard },
  { path: "/smart-trading", label: "Smart Trading", icon: Crosshair },
  { path: "/trust-score", label: "Trust Score", icon: ShieldCheck },
  { path: "/geo-risk", label: "Geo Risk", icon: Globe2 },
  { path: "/trading", label: "Trading", icon: LineChart },
  { path: "/exchanges", label: "Exchanges", icon: Globe },
  { path: "/history", label: "Trade History", icon: History },
  { path: "/backtest", label: "Backtesting", icon: FlaskConical },
  { path: "/analytics", label: "Analytics", icon: ChartPie },
  { path: "/signals", label: "Signals & AI", icon: Brain },
  { path: "/auto-trader", label: "Auto-Trader", icon: Bot },
  { path: "/optimizer", label: "Optimizer", icon: Cpu },
  { path: "/alerts", label: "Alerts", icon: Bell },
  { path: "/system-alerts", label: "System Alerts", icon: AlertTriangle },
  { path: "/spread-betting", label: "Spread Betting", icon: PoundSterling },
  { path: "/settings", label: "Settings", icon: Settings2 },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const [location] = useLocation();
  const { connected } = useWebSocket();

  // Fetch unread system alert count for badge
  const { data: unreadCounts } = useQuery<Record<string, number>>({
    queryKey: ["/api/system-alerts/unread"],
    queryFn: async () => { const r = await apiRequest("GET", "/api/system-alerts/unread"); return r.json(); },
    refetchInterval: 10000,
  });
  const totalUnread = Object.values(unreadCounts ?? {}).reduce((a, b) => a + b, 0);

  return (
    <aside
      data-testid="sidebar"
      className={cn(
        "flex flex-col h-screen border-r border-border bg-sidebar text-sidebar-foreground transition-all duration-200 ease-in-out shrink-0",
        collapsed ? "w-16" : "w-56"
      )}
    >
      {/* Logo */}
      <div className="flex items-center h-14 px-3 border-b border-border shrink-0">
        <Link href="/" className="flex items-center gap-2 min-w-0">
          <svg
            width="32"
            height="32"
            viewBox="0 0 32 32"
            fill="none"
            aria-label="AlgoTrader logo"
            className="shrink-0"
          >
            <rect
              x="2"
              y="2"
              width="28"
              height="28"
              rx="6"
              fill="hsl(168 80% 42%)"
              fillOpacity="0.12"
              stroke="hsl(168 80% 42%)"
              strokeWidth="1.5"
            />
            <polyline
              points="7,22 12,16 16,19 21,10 25,14"
              stroke="hsl(168 80% 42%)"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="none"
            />
            <circle cx="25" cy="14" r="2" fill="hsl(168 80% 42%)" />
          </svg>
          {!collapsed && (
            <span className="font-semibold text-sm tracking-tight whitespace-nowrap">
              AlgoTrader
            </span>
          )}
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
        {navItems.map((item) => {
          const isActive =
            item.path === "/"
              ? location === "/" || location === ""
              : location.startsWith(item.path);

          const linkContent = (
            <Link
              key={item.path}
              href={item.path}
              data-testid={`nav-${item.label.toLowerCase().replace(/\s/g, "-")}`}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
              )}
            >
              <item.icon
                size={18}
                className={cn("shrink-0", isActive && "text-primary")}
              />
              {!collapsed && <span>{item.label}</span>}
              {!collapsed && item.path === "/system-alerts" && totalUnread > 0 && (
                <span className="ml-auto flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
                  {totalUnread > 99 ? "99+" : totalUnread}
                </span>
              )}
              {isActive && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-primary" />
              )}
            </Link>
          );

          if (collapsed) {
            return (
              <Tooltip key={item.path} delayDuration={0}>
                <TooltipTrigger asChild>
                  <div className="relative">
                    {linkContent}
                    {item.path === "/system-alerts" && totalUnread > 0 && (
                      <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                    )}
                  </div>
                </TooltipTrigger>
                <TooltipContent side="right" className="font-medium">
                  {item.label}{item.path === "/system-alerts" && totalUnread > 0 ? ` (${totalUnread})` : ""}
                </TooltipContent>
              </Tooltip>
            );
          }

          return (
            <div key={item.path} className="relative">
              {linkContent}
            </div>
          );
        })}
      </nav>

      {/* Bottom section */}
      <div className="border-t border-border px-3 py-3 space-y-2 shrink-0">
        {/* Connection status */}
        <div
          data-testid="connection-status"
          className={cn(
            "flex items-center gap-2 text-xs",
            connected ? "text-green-400" : "text-muted-foreground"
          )}
        >
          {connected ? <Wifi size={14} /> : <WifiOff size={14} />}
          {!collapsed && (
            <span>{connected ? "Connected" : "Disconnected"}</span>
          )}
        </div>

        {/* Collapse toggle */}
        <button
          data-testid="sidebar-toggle"
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center justify-center w-full py-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>
    </aside>
  );
}
