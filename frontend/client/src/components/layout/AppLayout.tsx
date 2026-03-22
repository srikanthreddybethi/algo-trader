import { Sidebar } from "./Sidebar";
import { PerplexityAttribution } from "@/components/PerplexityAttribution";

export function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="min-h-full flex flex-col">
          <div className="flex-1 p-4 lg:p-6">
            {children}
          </div>
          <footer className="px-6 py-3 border-t border-border">
            <PerplexityAttribution />
          </footer>
        </div>
      </main>
    </div>
  );
}
