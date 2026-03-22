import { Switch, Route, Router } from "wouter";
import { useHashLocation } from "wouter/use-hash-location";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppLayout } from "@/components/layout/AppLayout";
import Dashboard from "@/pages/Dashboard";
import Trading from "@/pages/Trading";
import Exchanges from "@/pages/Exchanges";
import TradeHistory from "@/pages/TradeHistory";
import Backtesting from "@/pages/Backtesting";
import Analytics from "@/pages/Analytics";
import Alerts from "@/pages/Alerts";
import Settings from "@/pages/Settings";
import Signals from "@/pages/Signals";
import AutoTraderPage from "@/pages/AutoTrader";
import OptimizerPage from "@/pages/Optimizer";
import SystemAlerts from "@/pages/SystemAlerts";
import SpreadBetting from "@/pages/SpreadBetting";
import SmartTrading from "@/pages/SmartTrading";
import NotFound from "@/pages/not-found";

function AppRouter() {
  return (
    <AppLayout>
      <Switch>
        <Route path="/" component={Dashboard} />
        <Route path="/smart-trading" component={SmartTrading} />
        <Route path="/trading" component={Trading} />
        <Route path="/exchanges" component={Exchanges} />
        <Route path="/history" component={TradeHistory} />
        <Route path="/backtest" component={Backtesting} />
        <Route path="/analytics" component={Analytics} />
        <Route path="/alerts" component={Alerts} />
        <Route path="/signals" component={Signals} />
        <Route path="/auto-trader" component={AutoTraderPage} />
        <Route path="/optimizer" component={OptimizerPage} />
        <Route path="/system-alerts" component={SystemAlerts} />
        <Route path="/spread-betting" component={SpreadBetting} />
        <Route path="/settings" component={Settings} />
        <Route component={NotFound} />
      </Switch>
    </AppLayout>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Router hook={useHashLocation}>
          <AppRouter />
        </Router>
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
