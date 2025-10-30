"use client";

import { ApiError } from "../../lib/api";
import { useChannelHistory, useChannelState } from "../../lib/hooks";

export default function HistoryPage() {
  const { data: state, error: stateError, isLoading: stateLoading } = useChannelState();
  const historyQuery = useChannelHistory(Boolean(state));

  const noChannel = stateError instanceof ApiError && stateError.status === 404;

  return (
    <div className="grid gap-8">
      <section className="grid gap-3">
        <h2 className="text-2xl font-semibold text-white">Signed State History</h2>
        <p className="max-w-3xl text-slate-300">
          Every channel update produces a new commitment pair and sequence number. Both parties sign the state hash
          to acknowledge the update. This view exposes the transcript without revealing the concealed balances.
        </p>
      </section>

      <section className="grid gap-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
        {stateLoading ? (
          <p className="text-slate-400">Loading channel information…</p>
        ) : noChannel ? (
          <p className="text-slate-300">Open a channel to start collecting state history.</p>
        ) : stateError ? (
          <p className="text-rose-300">Failed to fetch channel: {stateError.message}</p>
        ) : historyQuery.isLoading ? (
          <p className="text-slate-400">Fetching historical states…</p>
        ) : historyQuery.isError ? (
          <p className="text-rose-300">Failed to load history: {historyQuery.error.message}</p>
        ) : historyQuery.data && historyQuery.data.history.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full border-separate border-spacing-y-3 text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-slate-400">
                <tr>
                  <th className="px-4 py-2">Sequence</th>
                  <th className="px-4 py-2">Commitment (Alice)</th>
                  <th className="px-4 py-2">Commitment (Bob)</th>
                  <th className="px-4 py-2">Proofs</th>
                  <th className="px-4 py-2">Signatures</th>
                </tr>
              </thead>
              <tbody>
                {historyQuery.data.history.map((entry) => (
                  <tr key={entry.sequence} className="rounded-xl bg-slate-950/60 text-slate-200">
                    <td className="px-4 py-3 font-mono text-xs text-slate-100">{entry.sequence}</td>
                    <td className="px-4 py-3 font-mono text-xs">
                      <span className="block max-w-xs break-all">{entry.commitments.alice}</span>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs">
                      <span className="block max-w-xs break-all">{entry.commitments.bob}</span>
                    </td>
                    <td className="px-4 py-3 font-mono text-[11px]">
                      <ProofCell label="Alice" proof={entry.proofs.alice} />
                      <ProofCell label="Bob" proof={entry.proofs.bob} />
                    </td>
                    <td className="px-4 py-3 font-mono text-[11px]">
                      <SignatureCell label="Alice" value={entry.signatures.alice} />
                      <SignatureCell label="Bob" value={entry.signatures.bob} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-slate-300">No updates recorded yet. Execute a payment to populate the history.</p>
        )}
      </section>
    </div>
  );
}

type SignatureCellProps = {
  label: string;
  value?: string;
};

function SignatureCell({ label, value }: SignatureCellProps) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-slate-400">{label}</span>
      <span className="break-all text-slate-200">{value ?? "Pending"}</span>
    </div>
  );
}

type ProofCellProps = {
  label: string;
  proof?: { t: string; response_m: string; response_r: string };
};

function ProofCell({ label, proof }: ProofCellProps) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-slate-400">{label}</span>
      {proof ? (
        <div className="space-y-1 text-slate-200">
          <p className="break-all">t: {proof.t}</p>
          <p className="break-all">s_m: {proof.response_m}</p>
          <p className="break-all">s_r: {proof.response_r}</p>
        </div>
      ) : (
        <span className="text-slate-500">No proof</span>
      )}
    </div>
  );
}

