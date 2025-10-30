"use client";

import { ReactNode } from "react";

import { NavigationBar } from "./navigation-bar";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <NavigationBar />
      <main className="mx-auto w-full max-w-6xl px-6 py-10">
        <div className="grid gap-10">{children}</div>
      </main>
    </div>
  );
}

