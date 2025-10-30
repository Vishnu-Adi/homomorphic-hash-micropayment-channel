"use client";

import { FormEvent, useState } from "react";

import { useMutation } from "@tanstack/react-query";

import { ApiError, BenchmarkResponse, apiClient } from "../../lib/api";
import { useChannelState } from "../../lib/hooks";

export default function BenchmarksPage() {
  const { data: state, error: stateError } = useChannelState();
  const [iterations, setIterations] = useState("100");

  const benchmarkMutation = useMutation<BenchmarkResponse, ApiError, number>({
    mutationFn: (count) => apiClient.runBenchmark(count),
  });

  const noChannel = stateError instanceof ApiError && stateError.status === 404;

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const count = Number.parseInt(iterations, 10);
    if (Number.isNaN(count) || count <= 0) {
      return;
    }
    benchmarkMutation.mutate(count);
  };

  return (
    <div className="grid gap-8">
      <section className="grid gap-3">
        <h2 className="text-2xl font-semibold text-white">Benchmark Simulator</h2>
        <p className="max-w-3xl text-slate-300">
          Run lightweight benchmarks to capture per-update latency, proof verification cost, and message sizes. Use
          the resulting statistics in the evaluation section of your report.
        </p>
      </section>

      <section className="grid gap-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
        <form className="flex flex-col gap-4 md:flex-row md:items-end" onSubmit={handleSubmit}>
          <div className="grid gap-2">
            <label className="text-sm font-medium text-slate-200" htmlFor="iterations">
              Number of updates (N)
            </label>
            <input
              id="iterations"
              type="number"
              min={10}
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 focus:border-cyan-500 focus:outline-none"
              value={iterations}
              onChange={(event) => setIterations(event.target.value)}
            />
          </div>
          <button
            type="submit"
            className="inline-flex items-center justify-center rounded-full bg-cyan-500 px-5 py-2 text-sm font-semibold text-slate-950 transition-colors hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-slate-700"
            disabled={benchmarkMutation.isLoading || noChannel}
          >
            {benchmarkMutation.isLoading ? "Running…" : "Run benchmark"}
          </button>
        </form>

        {noChannel ? (
          <p className="text-slate-400">Open a channel before benchmarking to ensure parameters are initialised.</p>
        ) : null}

        {benchmarkMutation.isError ? (
          <p className="rounded-lg border border-rose-500/60 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            Benchmark failed: {benchmarkMutation.error.message}
          </p>
        ) : null}

        {benchmarkMutation.isSuccess ? (
          <div className="grid gap-4">
            <div className="rounded-lg border border-indigo-500/60 bg-indigo-500/10 px-4 py-3 text-sm text-indigo-100">
              <p className="font-semibold">Benchmark summary</p>
              <p className="text-xs text-indigo-200">
                {benchmarkMutation.data.iterations} synthetic updates alternating between Alice and Bob.
              </p>
            </div>
            <div className="grid gap-4 rounded-lg border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-200">
              <h4 className="font-semibold text-white">Timings (milliseconds)</h4>
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-xs">
                  <thead className="text-slate-400">
                    <tr>
                      <th className="px-4 py-2">Phase</th>
                      <th className="px-4 py-2">Average</th>
                      <th className="px-4 py-2">Min</th>
                      <th className="px-4 py-2">Max</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(benchmarkMutation.data.timings).map(([phase, summary]) => (
                      <tr key={phase} className="border-t border-slate-800">
                        <td className="px-4 py-2 capitalize">{phase}</td>
                        <td className="px-4 py-2">{summary.avg_ms.toFixed(3)}</td>
                        <td className="px-4 py-2">{summary.min_ms.toFixed(3)}</td>
                        <td className="px-4 py-2">{summary.max_ms.toFixed(3)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="text-xs text-slate-300">
                <p>Data sizes captured for the final state:</p>
                <p>• Commitments payload: {benchmarkMutation.data.sizes.commitments_bytes} bytes</p>
                <p>• Signatures payload: {benchmarkMutation.data.sizes.signatures_bytes} bytes</p>
              </div>
            </div>

            <div className="grid gap-2 rounded-lg border border-slate-800 bg-slate-950/60 p-4 text-xs font-mono text-slate-200">
              <p className="font-sans text-sm font-semibold text-white">Latest state snapshot</p>
              <p className="font-sans text-slate-400">
                Channel {benchmarkMutation.data.latest_state.channel_id} · sequence {benchmarkMutation.data.latest_state.sequence}
              </p>
              {Object.entries(benchmarkMutation.data.latest_state.commitments).map(([participant, commitment]) => {
                const proof =
                  benchmarkMutation.data.latest_state.proofs[participant as keyof typeof benchmarkMutation.data.latest_state.proofs];
                return (
                  <div key={participant} className="rounded-lg bg-slate-900 px-3 py-2">
                    <p className="font-sans text-xs text-slate-400">{participant}</p>
                    <p className="break-all">commitment: {commitment}</p>
                    {proof ? (
                      <div className="mt-2 space-y-1 text-[11px] text-slate-300">
                        <p className="break-all">t: {proof.t}</p>
                        <p className="break-all">s_m: {proof.response_m}</p>
                        <p className="break-all">s_r: {proof.response_r}</p>
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}
      </section>

      {state ? (
        <section className="grid gap-3 rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
          <h3 className="text-lg font-semibold text-white">Current channel context</h3>
          <p className="text-sm text-slate-300">
            Benchmarks will use the active channel (<span className="font-mono text-slate-100">{state.channel_id}</span>)
            , sequence {state.sequence}. Commitments are recycled after each run to avoid leaking Δ in timing logs.
          </p>
        </section>
      ) : null}
    </div>
  );
}

