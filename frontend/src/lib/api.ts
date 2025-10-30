const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type ParticipantId = "alice" | "bob";

export type CommitmentProof = {
  t: string;
  response_m: string;
  response_r: string;
};

export type ChannelState = {
  channel_id: string;
  sequence: number;
  commitments: Record<ParticipantId, string>;
  proofs: Record<ParticipantId, CommitmentProof>;
  signatures: Partial<Record<ParticipantId, string>>;
  verify_keys: Record<ParticipantId, string>;
};

export type ChannelHistoryEntry = {
  sequence: number;
  commitments: Record<ParticipantId, string>;
  proofs: Record<ParticipantId, CommitmentProof>;
  signatures: Partial<Record<ParticipantId, string>>;
};

export type ChannelHistoryResponse = {
  channel_id: string;
  history: ChannelHistoryEntry[];
};

export type SettlementResponse = {
  channel_id: string;
  sequence: number;
  settled_balances: Record<ParticipantId, number>;
  verified: boolean;
};

export type OpenChannelPayload = {
  deposit_alice: number;
  deposit_bob: number;
  channel_id?: string;
};

export type UpdateChannelPayload = {
  delta: number;
  payer: ParticipantId;
  channel_id?: string;
};

export type CosignPayload = {
  channel_id?: string;
  participant?: ParticipantId;
};

export type CloseChannelPayload = {
  channel_id?: string;
};

export type BenchmarkResponse = {
  iterations: number;
  timings: Record<"update" | "sign" | "verify" | "proof_verify", { avg_ms: number; min_ms: number; max_ms: number }>;
  sizes: {
    commitments_bytes: number;
    signatures_bytes: number;
  };
  latest_state: {
    channel_id: string;
    sequence: number;
    commitments: Record<ParticipantId, string>;
    proofs: Record<ParticipantId, CommitmentProof>;
    signatures: Partial<Record<ParticipantId, string>>;
  };
};

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    const errorMessage = typeof detail?.detail === "string" ? detail.detail : response.statusText;
    throw new ApiError(errorMessage || "Unexpected API error", response.status);
  }

  if (response.status === 204) {
    return undefined as unknown as T;
  }

  return (await response.json()) as T;
}

function buildQuery(params: Record<string, string | number | undefined>) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined) return;
    search.append(key, String(value));
  });
  const query = search.toString();
  return query ? `?${query}` : "";
}

export const apiClient = {
  health: () => request<{ status: string }>("/health"),
  openChannel: (payload: OpenChannelPayload) =>
    request<ChannelState>("/channel/open", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateChannel: (payload: UpdateChannelPayload) =>
    request<ChannelState>("/channel/update", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  cosignChannel: (payload: CosignPayload) =>
    request<ChannelState>("/channel/cosign", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  closeChannel: (payload: CloseChannelPayload) =>
    request<SettlementResponse>("/channel/close", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getChannelState: (channelId?: string) =>
    request<ChannelState>(`/channel/state${buildQuery({ channel_id: channelId })}`),
  getChannelHistory: (channelId?: string) =>
    request<ChannelHistoryResponse>(`/channel/history${buildQuery({ channel_id: channelId })}`),
  runBenchmark: (iterations = 100, channelId?: string) =>
    request<BenchmarkResponse>(
      `/eval/bench${buildQuery({ N: iterations, channel_id: channelId })}`,
    ),
};

