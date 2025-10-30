"""Micro-benchmarks for the micropayment channel prototype."""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional

from ..crypto import pedersen
from ..protocol.channel import Channel, ParticipantId, proof_context


@dataclass
class TimingSummary:
    average_ms: float
    min_ms: float
    max_ms: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "avg_ms": round(self.average_ms, 6),
            "min_ms": round(self.min_ms, 6),
            "max_ms": round(self.max_ms, 6),
        }


def _to_ms(samples: List[float]) -> TimingSummary:
    return TimingSummary(
        average_ms=statistics.mean(samples) * 1000.0,
        min_ms=min(samples) * 1000.0,
        max_ms=max(samples) * 1000.0,
    )


def _hex_size(hex_str: str) -> int:
    return len(hex_str) // 2


def run_benchmarks(
    iterations: int = 100,
    *,
    params: Optional[pedersen.CommitmentParameters] = None,
    deposit_alice: int = 1_000,
    deposit_bob: int = 1_000,
) -> Dict[str, object]:
    """Run synthetic updates and capture timing + size metrics."""

    if iterations <= 0:
        raise ValueError("iterations must be positive")

    params = params or pedersen.default_parameters()

    channel = Channel.open(deposit_alice, deposit_bob, params=params)

    update_samples: List[float] = []
    sign_samples: List[float] = []
    verify_samples: List[float] = []
    proof_verify_samples: List[float] = []

    participants: List[ParticipantId] = ["alice", "bob"]

    for index in range(iterations):
        payer: ParticipantId = participants[index % 2]
        delta = 1 + (index % 3)  # rotate small deltas

        start_update = time.perf_counter()
        channel.apply_payment(payer, delta)
        update_samples.append(time.perf_counter() - start_update)

        start_sign = time.perf_counter()
        for participant_id in participants:
            channel.sign_state(participant_id)
        sign_samples.append(time.perf_counter() - start_sign)

        start_verify = time.perf_counter()
        channel.verify_signatures()
        verify_samples.append(time.perf_counter() - start_verify)

        start_proof_verify = time.perf_counter()
        for participant_id in participants:
            proof = channel.state.proofs[participant_id]
            commitment = channel.state.commitments[participant_id]
            context = proof_context(channel.channel_id, channel.state.sequence, participant_id)
            if not pedersen.verify_opening_proof(params, commitment, proof, context=context):
                raise ValueError("Proof verification failed during benchmark")
        proof_verify_samples.append(time.perf_counter() - start_proof_verify)

    # Capture size metrics on final state
    commitments_hex = {
        pid: pedersen.serialize_commitment(commitment)
        for pid, commitment in channel.state.commitments.items()
    }
    signatures_hex = {
        pid: signature.to_hex() for pid, signature in channel.state.signatures.items()
    }

    state_payload_bytes = sum(_hex_size(value) for value in commitments_hex.values())
    signature_bytes = sum(_hex_size(value) for value in signatures_hex.values())

    return {
        "iterations": iterations,
        "timings": {
            "update": _to_ms(update_samples).to_dict(),
            "sign": _to_ms(sign_samples).to_dict(),
            "verify": _to_ms(verify_samples).to_dict(),
            "proof_verify": _to_ms(proof_verify_samples).to_dict(),
        },
        "sizes": {
            "commitments_bytes": state_payload_bytes,
            "signatures_bytes": signature_bytes,
        },
        "latest_state": {
            "channel_id": channel.channel_id,
            "sequence": channel.state.sequence,
            "commitments": commitments_hex,
            "signatures": signatures_hex,
            "proofs": {pid: pedersen.serialize_proof(proof) for pid, proof in channel.state.proofs.items()},
        },
    }

