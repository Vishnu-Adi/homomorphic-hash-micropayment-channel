"""FastAPI entrypoint for the micropayment channel prototype."""

from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..crypto import pedersen
from ..eval import benchmark
from ..protocol import channel as channel_module
from ..protocol import ledger

ParticipantId = channel_module.ParticipantId


class OpenChannelRequest(BaseModel):
    deposit_alice: int = Field(ge=0)
    deposit_bob: int = Field(ge=0)
    channel_id: Optional[str] = Field(default=None, description="Optional custom channel identifier")


class UpdateChannelRequest(BaseModel):
    delta: int = Field(gt=0)
    payer: ParticipantId
    channel_id: Optional[str] = None


class CosignRequest(BaseModel):
    channel_id: Optional[str] = None
    participant: Optional[ParticipantId] = Field(default=None, description="Sign as a single participant; default signs both")


class CloseChannelRequest(BaseModel):
    channel_id: Optional[str] = None


class ChannelStateResponse(BaseModel):
    channel_id: str
    sequence: int
    commitments: Dict[ParticipantId, str]
    proofs: Dict[ParticipantId, Dict[str, str]]
    signatures: Dict[ParticipantId, str]
    verify_keys: Dict[ParticipantId, str]


class ChannelHistoryResponse(BaseModel):
    channel_id: str
    history: List[Dict[str, object]]


class SettlementResponse(BaseModel):
    channel_id: str
    sequence: int
    settled_balances: Dict[ParticipantId, int]
    verified: bool


class ChannelManager:
    def __init__(self) -> None:
        self.params = pedersen.default_parameters()
        self.channels: Dict[str, channel_module.Channel] = {}
        self.active_channel_id: Optional[str] = None
        self._ledger = ledger.SimulatedLedger(self.params)

    def _resolve_channel(self, channel_id: Optional[str]) -> channel_module.Channel:
        target_id = channel_id or self.active_channel_id
        if target_id is None:
            raise HTTPException(status_code=404, detail="No channel has been opened")
        try:
            return self.channels[target_id]
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Channel {target_id} not found") from exc

    def open_channel(self, request: OpenChannelRequest) -> channel_module.Channel:
        channel = channel_module.Channel.open(
            deposit_alice=request.deposit_alice,
            deposit_bob=request.deposit_bob,
            params=self.params,
            channel_id=request.channel_id,
        )
        self.channels[channel.channel_id] = channel
        self.active_channel_id = channel.channel_id
        self._ledger.register_channel(channel)
        return channel

    def apply_update(self, request: UpdateChannelRequest) -> channel_module.Channel:
        channel = self._resolve_channel(request.channel_id)
        channel.apply_payment(request.payer, request.delta)
        self._ledger.update_state(channel)
        return channel

    def cosign(self, request: CosignRequest) -> channel_module.Channel:
        channel = self._resolve_channel(request.channel_id)
        if request.participant is not None:
            channel.sign_state(request.participant)
        else:
            for participant_id in channel.participants.keys():
                channel.sign_state(participant_id)
        return channel

    def close(self, request: CloseChannelRequest) -> SettlementResponse:
        channel = self._resolve_channel(request.channel_id)
        if not channel.is_fully_signed():
            raise HTTPException(status_code=400, detail="Channel must be co-signed before settlement")

        payload = channel.closing_payload()
        try:
            result = self._ledger.cooperative_close(payload)
        except ledger.LedgerError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return SettlementResponse(**result)

    def benchmark(self, iterations: int, channel_id: Optional[str]) -> Dict[str, object]:
        if channel_id is not None:
            self._resolve_channel(channel_id)
        elif not self.active_channel_id:
            raise HTTPException(status_code=404, detail="No channel has been opened")

        return benchmark.run_benchmarks(iterations, params=self.params)

    def state_response(self, channel: channel_module.Channel) -> ChannelStateResponse:
        commitments = {
            pid: pedersen.serialize_commitment(commit) for pid, commit in channel.state.commitments.items()
        }
        proofs = {pid: pedersen.serialize_proof(proof) for pid, proof in channel.state.proofs.items()}
        signatures = {pid: sig.to_hex() for pid, sig in channel.state.signatures.items()}
        verify_keys = {pid: participant.verify_key.to_hex() for pid, participant in channel.participants.items()}
        return ChannelStateResponse(
            channel_id=channel.channel_id,
            sequence=channel.state.sequence,
            commitments=commitments,
            proofs=proofs,
            signatures=signatures,
            verify_keys=verify_keys,
        )

    def history_response(self, channel: channel_module.Channel) -> ChannelHistoryResponse:
        return ChannelHistoryResponse(channel_id=channel.channel_id, history=channel.history_snapshots())


app = FastAPI(title="Homomorphic Micropayment Channel", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = ChannelManager()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/channel/open", response_model=ChannelStateResponse)
def open_channel(request: OpenChannelRequest) -> ChannelStateResponse:
    channel = manager.open_channel(request)
    return manager.state_response(channel)


@app.post("/channel/update", response_model=ChannelStateResponse)
def update_channel(request: UpdateChannelRequest) -> ChannelStateResponse:
    channel = manager.apply_update(request)
    return manager.state_response(channel)


@app.post("/channel/cosign", response_model=ChannelStateResponse)
def cosign_channel(request: CosignRequest) -> ChannelStateResponse:
    channel = manager.cosign(request)
    return manager.state_response(channel)


@app.post("/channel/close", response_model=SettlementResponse)
def close_channel(request: CloseChannelRequest) -> SettlementResponse:
    return manager.close(request)


@app.get("/channel/state", response_model=ChannelStateResponse)
def get_state(channel_id: Optional[str] = None) -> ChannelStateResponse:
    channel = manager._resolve_channel(channel_id)
    return manager.state_response(channel)


@app.get("/channel/history", response_model=ChannelHistoryResponse)
def get_history(channel_id: Optional[str] = None) -> ChannelHistoryResponse:
    channel = manager._resolve_channel(channel_id)
    return manager.history_response(channel)


@app.get("/eval/bench")
def run_benchmark(N: int = 100, channel_id: Optional[str] = None) -> Dict[str, object]:  # noqa: N803
    return manager.benchmark(N, channel_id)

