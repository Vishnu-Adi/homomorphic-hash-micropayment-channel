"""Simulated ledger for cooperative channel settlement."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, TYPE_CHECKING

from ..crypto import pedersen, signing
from .channel import ParticipantId, compute_state_digest, proof_context


if TYPE_CHECKING:  # pragma: no cover - for type hints only
    from .channel import Channel


class LedgerError(Exception):
    pass


class UnknownChannelError(LedgerError):
    pass


class InvalidSettlementError(LedgerError):
    pass


@dataclass
class LedgerRecord:
    channel_id: str
    sequence: int
    commitments: Dict[ParticipantId, pedersen.Commitment]
    verify_keys: Dict[ParticipantId, signing.VerifyKey]
    closed: bool = False

    def clone_commitments(self) -> Dict[ParticipantId, pedersen.Commitment]:
        return {pid: pedersen.Commitment(value=commit.value) for pid, commit in self.commitments.items()}


class SimulatedLedger:
    """A lightweight ledger that validates cooperative close payloads."""

    def __init__(self, params: Optional[pedersen.CommitmentParameters] = None) -> None:
        self.params = params or pedersen.default_parameters()
        self._records: Dict[str, LedgerRecord] = {}

    def register_channel(self, channel: "Channel") -> None:
        self._records[channel.channel_id] = LedgerRecord(
            channel_id=channel.channel_id,
            sequence=channel.state.sequence,
            commitments={pid: pedersen.Commitment(value=commit.value) for pid, commit in channel.state.commitments.items()},
            verify_keys={pid: participant.verify_key for pid, participant in channel.participants.items()},
        )

    def update_state(self, channel: "Channel") -> None:
        record = self._require_record(channel.channel_id)
        if channel.state.sequence < record.sequence:
            raise InvalidSettlementError("Channel sequence regressed; refusing to update")
        record.sequence = channel.state.sequence
        record.commitments = {
            pid: pedersen.Commitment(value=commit.value) for pid, commit in channel.state.commitments.items()
        }

    def cooperative_close(self, payload: Dict[str, object]) -> Dict[str, object]:
        channel_id = payload.get("channel_id")
        if not isinstance(channel_id, str):
            raise InvalidSettlementError("Missing channel_id in close payload")

        record = self._require_record(channel_id)
        if record.closed:
            raise InvalidSettlementError("Channel already settled")

        sequence = payload.get("sequence")
        if not isinstance(sequence, int) or sequence != record.sequence:
            raise InvalidSettlementError("Sequence mismatch during settlement")

        commitments_hex = payload.get("commitments")
        openings_hex = payload.get("openings")
        balances = payload.get("balances")
        signatures_hex = payload.get("signatures")
        proofs_hex = payload.get("proofs")

        if not isinstance(commitments_hex, dict) or not isinstance(openings_hex, dict) or not isinstance(balances, dict):
            raise InvalidSettlementError("Malformed close payload")
        if not isinstance(signatures_hex, dict):
            raise InvalidSettlementError("Missing signatures in close payload")
        if not isinstance(proofs_hex, dict):
            raise InvalidSettlementError("Missing proofs in close payload")

        # Check commitments match the last known state.
        for pid, commitment in record.commitments.items():
            serialized = pedersen.serialize_commitment(commitment)
            if commitments_hex.get(pid) != serialized:
                raise InvalidSettlementError(f"Commitment mismatch for participant {pid}")

        digest = compute_state_digest(channel_id, record.sequence, record.commitments)

        # Verify signatures and openings.
        for pid, verify_key in record.verify_keys.items():
            signature_hex = signatures_hex.get(pid)
            if signature_hex is None:
                raise InvalidSettlementError(f"Missing signature for participant {pid}")
            signature = signing.Signature.from_hex(signature_hex)
            if not verify_key.verify(digest, signature):
                raise InvalidSettlementError(f"Invalid signature for participant {pid}")

            opening_hex = openings_hex.get(pid)
            balance = balances.get(pid)
            if opening_hex is None or not isinstance(balance, int):
                raise InvalidSettlementError(f"Missing opening or balance for participant {pid}")
            opening = pedersen.deserialize_opening(opening_hex)
            commitment = record.commitments[pid]
            if not pedersen.verify(self.params, commitment, balance, opening):
                raise InvalidSettlementError(f"Opening does not match commitment for participant {pid}")

            proof_blob = proofs_hex.get(pid)
            if not isinstance(proof_blob, dict):
                raise InvalidSettlementError(f"Missing proof for participant {pid}")
            proof = pedersen.deserialize_proof(proof_blob)
            context = proof_context(channel_id, record.sequence, pid)
            if not pedersen.verify_opening_proof(self.params, commitment, proof, context=context):
                raise InvalidSettlementError(f"Invalid commitment proof for participant {pid}")

        record.closed = True
        return {
            "channel_id": channel_id,
            "sequence": record.sequence,
            "settled_balances": balances,
            "verified": True,
        }

    def _require_record(self, channel_id: str) -> LedgerRecord:
        if channel_id not in self._records:
            raise UnknownChannelError(channel_id)
        return self._records[channel_id]

