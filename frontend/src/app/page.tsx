"use client";

import Link from "next/link";

import { ApiError } from "../lib/api";
import { useChannelState } from "../lib/hooks";

export default function Home() {
  const { data, isLoading, error } = useChannelState();

  const noChannel = error instanceof ApiError && error.status === 404;

  return (
    <div className="grid gap-10">
      <section className="grid gap-4">
        <h2 className="text-3xl font-semibold text-white">Project Overview</h2>
        <p className="max-w-3xl text-slate-300">
          This interface drives the privacy-preserving micropayment channel prototype. Open a
          channel, execute confidential payments, review jointly signed states, and inspect
          performance metrics—all without ever revealing per-payment amounts.
        </p>
        <div className="flex flex-wrap gap-3 text-sm text-cyan-300">
          <span className="rounded-full bg-cyan-900/40 px-3 py-1">Additively homomorphic commitments</span>
          <span className="rounded-full bg-cyan-900/40 px-3 py-1">Ed25519 co-signatures</span>
          <span className="rounded-full bg-cyan-900/40 px-3 py-1">Simulated cooperative settlement</span>
        </div>
      </section>

      <section className="grid gap-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
        <h3 className="text-xl font-semibold text-white">Current Channel State</h3>
        {isLoading ? (
          <p className="text-slate-400">Loading state...</p>
        ) : noChannel ? (
          <p className="text-slate-300">
            No channel is active yet. Head to <Link href="/channel" className="text-cyan-300 underline">Channel
            Setup</Link> to deposit funds and generate commitments.
          </p>
        ) : error ? (
          <p className="text-rose-300">Failed to load channel state: {error.message}</p>
        ) : data ? (
          <div className="grid gap-4 text-sm text-slate-300">
            <div className="flex flex-wrap gap-6">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Channel ID</p>
                <p className="font-mono text-slate-100">{data.channel_id}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Sequence</p>
                <p className="font-semibold text-slate-100">{data.sequence}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Signatures Collected</p>
                <p className="font-semibold text-slate-100">
                  {Object.keys(data.signatures ?? {}).length} / {Object.keys(data.verify_keys).length}
                </p>
              </div>
            </div>
            <div className="grid gap-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">Commitments</p>
              <div className="grid gap-2 font-mono text-xs text-slate-200">
                {Object.entries(data.commitments).map(([participant, commitment]) => (
                  <div key={participant} className="rounded-lg bg-slate-950/60 px-3 py-2">
                    <p className="text-slate-400">{participant}</p>
                    <p className="break-all">{commitment}</p>
                  </div>
                ))}
              </div>
            </div>
            <div className="grid gap-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">Proof of Knowledge (t, s_m, s_r)</p>
              <div className="grid gap-2 font-mono text-[11px] text-slate-200">
                {Object.entries(data.proofs).map(([participant, proof]) => (
                  <div key={participant} className="rounded-lg bg-slate-950/60 px-3 py-2">
                    <p className="text-slate-400">{participant}</p>
                    <p className="break-all">t: {proof.t}</p>
                    <p className="break-all">s_m: {proof.response_m}</p>
                    <p className="break-all">s_r: {proof.response_r}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : null}
      </section>

      <section className="grid gap-4">
        <h3 className="text-xl font-semibold text-white">Workflow</h3>
        <div className="grid gap-6 md:grid-cols-3">
          <WorkflowCard
            title="1. Initialize"
            description="Choose deposits for Alice and Bob. Fresh commitments and verifying keys are published to the ledger."
            href="/channel"
          />
          <WorkflowCard
            title="2. Update Privately"
            description="Apply micropayments without exposing individual deltas. Commitments update and both parties co-sign the new state."
            href="/payments"
          />
          <WorkflowCard
            title="3. Audit & Close"
            description="Inspect the signed history, run lightweight benchmarks, then reveal openings for cooperative settlement."
            href="/history"
          />
        </div>
      </section>
    </div>
  );
}

type WorkflowCardProps = {
  title: string;
  description: string;
  href: string;
};

function WorkflowCard({ title, description, href }: WorkflowCardProps) {
  return (
    <Link
      href={href}
      className="group grid gap-3 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 transition-colors hover:border-cyan-500/40 hover:bg-slate-900"
    >
      <p className="text-sm font-semibold text-cyan-300">{title}</p>
      <p className="text-sm text-slate-300">{description}</p>
      <span className="text-sm font-medium text-cyan-400">Open page →</span>
    </Link>
  );
}
