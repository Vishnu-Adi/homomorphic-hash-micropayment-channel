"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Overview" },
  { href: "/channel", label: "Channel Setup" },
  { href: "/payments", label: "Payments" },
  { href: "/history", label: "History" },
  { href: "/benchmarks", label: "Benchmarks" },
];

export function NavigationBar() {
  const pathname = usePathname();

  return (
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-4">
        <div>
          <p className="text-xs uppercase tracking-wider text-slate-400">Micropayment Channel</p>
          <h1 className="text-lg font-semibold text-slate-100">Privacy-Preserving Demo</h1>
        </div>
        <nav className="flex gap-4 text-sm">
          {links.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded-full px-4 py-2 transition-colors ${
                  isActive
                    ? "bg-cyan-500/20 text-cyan-300"
                    : "text-slate-300 hover:bg-slate-800 hover:text-white"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}

