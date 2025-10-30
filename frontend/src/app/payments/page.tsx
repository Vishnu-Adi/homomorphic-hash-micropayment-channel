"use client";

import { FormEvent, useMemo, useState } from "react";

import { ApiError } from "../../lib/api";
import {
  useChannelState,
  useCloseChannel,
  useCosignChannel,
  useUpdateChannel,
} from "../../lib/hooks";

const participants = [
  { id: "alice" as const, label: "Alice pays Bob" },
  { id: "bob" as const, label: "Bob pays Alice" },
];

export default function PaymentsPage() {
  const { data: state, error, isFetching } = useChannelState();
  const updateMutation = useUpdateChannel();
  const cosignMutation = useCosignChannel();
  const closeMutation = useCloseChannel();

  const [payer, setPayer] = useState<typeof participants[number]["id"]>("alice");
  const [amount, setAmount] = useState("5");

  const handlePayment = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const delta = Number.parseInt(amount, 10);
    if (Number.isNaN(delta) || delta <= 0) {
      return;
    }
    updateMutation.mutate({ delta, payer });
  };

  const hasChannel = !!state;
  const noChannel = error instanceof ApiError && error.status === 404;
  const signaturesCollected = useMemo(() => {
    if (!state) return 0;
    return Object.keys(state.signatures ?? {}).length;
  }, [state]);

  return (
    <div className="grid gap-8">
      <section className="grid gap-3">
        <h2 className="text-2xl font-semibold text-white">Micropayment Updates</h2>
        <p className="max-w-3xl text-slate-300">
          Each update applies an amount Δ from the payer to the counterparty while refreshing the underlying
          commitments with fresh randomness. Neither Δ nor the intermediate balances leave the backend.
        </p>
      </section>

      <section className="grid gap-6 rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
        <form className="grid gap-4" onSubmit={handlePayment}>
          <fieldset className="grid gap-3">
            <legend className="text-sm font-medium text-slate-200">Select payer</legend>
            <div className="flex flex-wrap gap-3">
              {participants.map((participantOption) => {
                const isActive = payer === participantOption.id;
                return (
                  <button
                    key={participantOption.id}
                    type="button"
                    onClick={() => setPayer(participantOption.id)}
                    className={`rounded-full border px-4 py-2 text-sm transition-colors ${
                      isActive
                        ? "border-cyan-400 bg-cyan-500/20 text-cyan-200"
                        : "border-slate-700 bg-slate-950 text-slate-300 hover:border-cyan-400"
                    }`}
                  >
                    {participantOption.label}
                  </button>
                );
              })}
            </div>
          </fieldset>

          <div className="grid gap-2">
            <label className="text-sm font-medium text-slate-200" htmlFor="amount">
              Transfer amount Δ
            </label>
            <input
              id="amount"
              type="number"
              min={1}
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 focus:border-cyan-500 focus:outline-none"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              required
            />
          </div>

          <button
            type="submit"
            className="mt-2 inline-flex items-center justify-center rounded-full bg-cyan-500 px-5 py-2 text-sm font-semibold text-slate-950 transition-colors hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-slate-700"
            disabled={!hasChannel || updateMutation.isLoading}
          >
            {updateMutation.isLoading ? "Applying update…" : "Apply update"}
          </button>
        </form>

        {updateMutation.isError ? (
          <p className="rounded-lg border border-rose-500/60 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            Update failed: {updateMutation.error?.message}
          </p>
        ) : null}

        {updateMutation.isSuccess ? (
          <p className="rounded-lg border border-emerald-500/60 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
            Update applied. Sequence advanced to {updateMutation.data.sequence}. Collect co-signatures to finalise.
          </p>
        ) : null}
      </section>

      <section className="grid gap-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
        <h3 className="text-lg font-semibold text-white">Co-sign & Close</h3>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="grid gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <p className="text-sm font-medium text-slate-200">Signature status</p>
            {noChannel ? (
              <p className="text-slate-400">Open a channel before collecting signatures.</p>
            ) : error ? (
              <p className="text-rose-300">{error.message}</p>
            ) : state ? (
              <>
                <p className="text-xs text-slate-400">
                  {signaturesCollected} / {Object.keys(state.verify_keys).length} signatures collected
                </p>
                <div className="grid gap-2 text-xs font-mono text-slate-200">
                  {Object.entries(state.verify_keys).map(([participant, key]) => {
                    const signatureHex = state.signatures?.[participant as keyof typeof state.signatures];
                    return (
                      <div key={participant} className="rounded-lg bg-slate-900 px-3 py-2">
                        <p className="text-slate-400">{participant}</p>
                        <p className="break-all">
                          {signatureHex ? signatureHex : "Signature pending"}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </>
            ) : null}
            <button
              type="button"
              onClick={() => cosignMutation.mutate({})}
              className="inline-flex items-center justify-center rounded-full bg-indigo-500 px-4 py-2 text-sm font-semibold text-slate-900 transition-colors hover:bg-indigo-400 disabled:cursor-not-allowed disabled:bg-slate-700"
              disabled={!hasChannel || cosignMutation.isLoading}
            >
              {cosignMutation.isLoading ? "Collecting signatures…" : "Co-sign state"}
            </button>
            {cosignMutation.isError ? (
              <p className="text-sm text-rose-200">Failed to sign: {cosignMutation.error?.message}</p>
            ) : null}
          </div>

          <div className="grid gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <p className="text-sm font-medium text-slate-200">Cooperative close</p>
            <p className="text-sm text-slate-300">
              Once both signatures are present, reveal the final openings to the simulated ledger. The ledger verifies
              each commitment and returns final balances.
            </p>
            <button
              type="button"
              onClick={() => closeMutation.mutate()}
              className="inline-flex items-center justify-center rounded-full bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-900 transition-colors hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-slate-700"
              disabled={!hasChannel || closeMutation.isLoading}
            >
              {closeMutation.isLoading ? "Settling channel…" : "Close channel"}
            </button>
            {closeMutation.isError ? (
              <p className="text-sm text-rose-200">Close failed: {closeMutation.error?.message}</p>
            ) : null}
            {closeMutation.isSuccess ? (
              <div className="rounded-lg border border-emerald-500/60 bg-emerald-500/10 px-3 py-2 text-xs">
                <p className="font-semibold text-emerald-200">Settlement verified</p>
                <p className="text-emerald-100">Alice: {closeMutation.data.settled_balances.alice}</p>
                <p className="text-emerald-100">Bob: {closeMutation.data.settled_balances.bob}</p>
              </div>
            ) : null}
          </div>
        </div>
      </section>

      <section className="grid gap-3 rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
        <h3 className="text-lg font-semibold text-white">Raw commitments</h3>
        {isFetching && !state ? (
          <p className="text-slate-400">Loading commitments…</p>
        ) : noChannel ? (
          <p className="text-slate-400">Open a channel to generate commitments.</p>
        ) : error ? (
          <p className="text-rose-300">{error.message}</p>
        ) : state ? (
          <div className="grid gap-3 font-mono text-xs text-slate-200">
            {Object.entries(state.commitments).map(([participant, commitment]) => {
              const proof = state.proofs[participant as keyof typeof state.proofs];
              return (
                <div key={participant} className="rounded-lg bg-slate-950/60 px-3 py-2">
                  <p className="text-slate-400">{participant}</p>
                  <p className="break-all">commitment: {commitment}</p>
                  {proof ? (
                    <div className="mt-2 grid gap-1 text-[11px] text-slate-300">
                      <p className="break-all">t: {proof.t}</p>
                      <p className="break-all">s_m: {proof.response_m}</p>
                      <p className="break-all">s_r: {proof.response_r}</p>
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        ) : null}
      </section>
    </div>
  );
}

