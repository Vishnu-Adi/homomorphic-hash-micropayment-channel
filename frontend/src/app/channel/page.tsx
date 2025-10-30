"use client";

import { FormEvent, useState } from "react";

import { ApiError } from "../../lib/api";
import { useChannelState, useOpenChannel } from "../../lib/hooks";

export default function ChannelSetupPage() {
  const { data: currentState, error: stateError, isFetching } = useChannelState();
  const [depositAlice, setDepositAlice] = useState("100");
  const [depositBob, setDepositBob] = useState("25");
  const [customChannelId, setCustomChannelId] = useState("");

  const openMutation = useOpenChannel();

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const depositA = Number.parseInt(depositAlice, 10);
    const depositB = Number.parseInt(depositBob, 10);

    if (Number.isNaN(depositA) || Number.isNaN(depositB) || depositA < 0 || depositB < 0) {
      return;
    }

    openMutation.mutate({
      deposit_alice: depositA,
      deposit_bob: depositB,
      channel_id: customChannelId || undefined,
    });
  };

  const noChannel = stateError instanceof ApiError && stateError.status === 404;

  return (
    <div className="grid gap-8">
      <section className="grid gap-3">
        <h2 className="text-2xl font-semibold text-white">Channel Setup</h2>
        <p className="max-w-3xl text-slate-300">
          Initialize a fresh two-party channel by specifying the initial deposits for Alice and Bob. When the
          channel opens, new commitments and verifying keys are minted, while per-party balances stay private.
        </p>
      </section>

      <section className="grid gap-6 rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
        <form className="grid gap-4" onSubmit={handleSubmit}>
          <div className="grid gap-2">
            <label className="text-sm font-medium text-slate-200" htmlFor="depositAlice">
              Deposit for Alice
            </label>
            <input
              id="depositAlice"
              type="number"
              min={0}
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 focus:border-cyan-500 focus:outline-none"
              value={depositAlice}
              onChange={(event) => setDepositAlice(event.target.value)}
              required
            />
          </div>

          <div className="grid gap-2">
            <label className="text-sm font-medium text-slate-200" htmlFor="depositBob">
              Deposit for Bob
            </label>
            <input
              id="depositBob"
              type="number"
              min={0}
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 focus:border-cyan-500 focus:outline-none"
              value={depositBob}
              onChange={(event) => setDepositBob(event.target.value)}
              required
            />
          </div>

          <div className="grid gap-2">
            <label className="text-sm font-medium text-slate-200" htmlFor="channelId">
              Channel ID (optional)
            </label>
            <input
              id="channelId"
              type="text"
              placeholder="Auto-generated when left blank"
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 focus:border-cyan-500 focus:outline-none"
              value={customChannelId}
              onChange={(event) => setCustomChannelId(event.target.value)}
            />
          </div>

          <button
            type="submit"
            className="mt-2 inline-flex items-center justify-center rounded-full bg-cyan-500 px-5 py-2 text-sm font-semibold text-slate-950 transition-colors hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-slate-700"
            disabled={openMutation.isLoading}
          >
            {openMutation.isLoading ? "Opening channel…" : "Open channel"}
          </button>
        </form>

        {openMutation.isError ? (
          <p className="rounded-lg border border-rose-500/60 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            Failed to open channel: {openMutation.error?.message ?? "Unknown error"}
          </p>
        ) : null}

        {openMutation.isSuccess ? (
          <p className="rounded-lg border border-emerald-500/60 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
            Channel opened successfully. Sequence {openMutation.data.sequence} with ID {openMutation.data.channel_id}.
          </p>
        ) : null}
      </section>

      <section className="grid gap-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
        <h3 className="text-lg font-semibold text-white">Verifying Keys</h3>
        {isFetching && !currentState && !noChannel ? (
          <p className="text-slate-400">Loading keys…</p>
        ) : noChannel ? (
          <p className="text-slate-300">Once a channel is opened, verifying keys for each party will appear here.</p>
        ) : stateError ? (
          <p className="text-rose-300">Unable to fetch verifying keys: {stateError.message}</p>
        ) : currentState ? (
          <div className="grid gap-3 font-mono text-xs text-slate-100">
            {Object.entries(currentState.verify_keys).map(([participant, key]) => (
              <div key={participant} className="rounded-lg bg-slate-950/60 px-3 py-2">
                <p className="text-slate-400">{participant}</p>
                <p className="break-all">{key}</p>
              </div>
            ))}
          </div>
        ) : null}
      </section>
    </div>
  );
}

