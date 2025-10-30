"""Channel state machine for privacy-preserving micropayments."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Dict, List, Literal, Optional
from uuid import uuid4

from ..crypto import pedersen, signing


ParticipantId = Literal["alice", "bob"]


class ChannelError(Exception):
    """Base exception for channel-related issues."""


class InsufficientBalanceError(ChannelError):
    pass


class InvalidParticipantError(ChannelError):
    pass


class InvalidAmountError(ChannelError):
    pass


def compute_state_digest(
    channel_id: str,
    sequence: int,
    commitments: Dict[ParticipantId, pedersen.Commitment],
) -> bytes:
    pieces = [channel_id, str(sequence)]
    for participant_id in sorted(commitments.keys()):
        pieces.append(pedersen.serialize_commitment(commitments[participant_id]))
    return sha256("|".join(pieces).encode("utf-8")).digest()


def proof_context(channel_id: str, sequence: int, participant_id: ParticipantId) -> bytes:
    return f"{channel_id}|{sequence}|{participant_id}|opening-proof".encode("utf-8")


@dataclass(frozen=True)
class ChannelParticipant:
    participant_id: ParticipantId
    signing_key: signing.SigningKey

    @property
    def verify_key(self) -> signing.VerifyKey:
        return self.signing_key.verify_key


@dataclass
class ChannelState:
    sequence: int
    balances: Dict[ParticipantId, int]
    commitments: Dict[ParticipantId, pedersen.Commitment]
    openings: Dict[ParticipantId, pedersen.CommitmentOpening]
    proofs: Dict[ParticipantId, pedersen.CommitmentProof]
    signatures: Dict[ParticipantId, signing.Signature] = field(default_factory=dict)

    def clone(self) -> "ChannelState":
        return ChannelState(
            sequence=self.sequence,
            balances=dict(self.balances),
            commitments={pid: pedersen.Commitment(value=commit.value) for pid, commit in self.commitments.items()},
            openings={pid: pedersen.CommitmentOpening(randomness=opening.randomness) for pid, opening in self.openings.items()},
            proofs={pid: pedersen.CommitmentProof(t=proof.t, response_m=proof.response_m, response_r=proof.response_r) for pid, proof in self.proofs.items()},
            signatures={pid: signing.Signature(bytes(sig.value)) for pid, sig in self.signatures.items()},
        )


@dataclass
class Channel:
    channel_id: str
    params: pedersen.CommitmentParameters
    participants: Dict[ParticipantId, ChannelParticipant]
    state: ChannelState
    history: List[ChannelState] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.history:
            self.history.append(self.state.clone())

    @staticmethod
    def _other(participant_id: ParticipantId) -> ParticipantId:
        if participant_id == "alice":
            return "bob"
        if participant_id == "bob":
            return "alice"
        raise InvalidParticipantError(participant_id)

    @classmethod
    def open(
        cls,
        deposit_alice: int,
        deposit_bob: int,
        *,
        params: Optional[pedersen.CommitmentParameters] = None,
        channel_id: Optional[str] = None,
        signing_keys: Optional[Dict[ParticipantId, signing.SigningKey]] = None,
    ) -> "Channel":
        if deposit_alice < 0 or deposit_bob < 0:
            raise InvalidAmountError("Deposits must be non-negative integers")

        params = params or pedersen.default_parameters()
        channel_id = channel_id or str(uuid4())

        if signing_keys is None:
            signing_keys = {
                "alice": signing.SigningKey.generate(),
                "bob": signing.SigningKey.generate(),
            }

        participants = {
            pid: ChannelParticipant(participant_id=pid, signing_key=sk)
            for pid, sk in signing_keys.items()
        }

        balances = {"alice": deposit_alice, "bob": deposit_bob}
        commitments: Dict[ParticipantId, pedersen.Commitment] = {}
        openings: Dict[ParticipantId, pedersen.CommitmentOpening] = {}
        proofs: Dict[ParticipantId, pedersen.CommitmentProof] = {}

        for pid, balance in balances.items():
            commitment, opening = pedersen.commit(params, balance)
            commitments[pid] = commitment
            openings[pid] = opening
            context = proof_context(channel_id, 0, pid)
            proof = pedersen.prove_opening(params, balance, opening, commitment, context=context)
            if not pedersen.verify_opening_proof(params, commitment, proof, context=context):
                raise ChannelError(f"Initial proof generation failed for participant {pid}")
            proofs[pid] = proof

        state = ChannelState(sequence=0, balances=balances, commitments=commitments, openings=openings, proofs=proofs)
        return cls(channel_id=channel_id, params=params, participants=participants, state=state)

    def _set_balances(self, balances: Dict[ParticipantId, int]) -> None:
        self.state.balances.update(balances)
        new_proofs: Dict[ParticipantId, pedersen.CommitmentProof] = {}
        for pid, balance in balances.items():
            commitment, opening = pedersen.commit(self.params, balance)
            self.state.commitments[pid] = commitment
            self.state.openings[pid] = opening
            context = proof_context(self.channel_id, self.state.sequence, pid)
            proof = pedersen.prove_opening(self.params, balance, opening, commitment, context=context)
            if not pedersen.verify_opening_proof(self.params, commitment, proof, context=context):
                raise ChannelError(f"Failed to verify commitment proof for participant {pid}")
            new_proofs[pid] = proof
        self.state.proofs = new_proofs
        self.state.signatures.clear()

    def apply_payment(self, payer: ParticipantId, amount: int) -> ChannelState:
        if payer not in self.participants:
            raise InvalidParticipantError(payer)
        if amount <= 0:
            raise InvalidAmountError("Transfer amount must be positive")
        if amount > self.state.balances[payer]:
            raise InsufficientBalanceError(
                f"{payer} balance {self.state.balances[payer]} insufficient for transfer {amount}"
            )

        payee = self._other(payer)
        balances = self.state.balances.copy()
        balances[payer] -= amount
        balances[payee] += amount

        self.state.sequence += 1
        self._set_balances(balances)
        self.history.append(self.state.clone())
        return self.state

    def state_digest(self) -> bytes:
        return compute_state_digest(self.channel_id, self.state.sequence, self.state.commitments)

    def sign_state(self, participant_id: ParticipantId) -> signing.Signature:
        if participant_id not in self.participants:
            raise InvalidParticipantError(participant_id)
        signature = self.participants[participant_id].signing_key.sign(self.state_digest())
        self.state.signatures[participant_id] = signature
        return signature

    def is_fully_signed(self) -> bool:
        return all(pid in self.state.signatures for pid in self.participants)

    def verify_signatures(self) -> bool:
        digest = self.state_digest()
        for pid, participant in self.participants.items():
            signature = self.state.signatures.get(pid)
            if signature is None:
                return False
            if not participant.verify_key.verify(digest, signature):
                return False
        return True

    def snapshot(self) -> Dict[str, object]:
        return {
            "channel_id": self.channel_id,
            "sequence": self.state.sequence,
            "commitments": {
                pid: pedersen.serialize_commitment(commit) for pid, commit in self.state.commitments.items()
            },
            "proofs": {pid: pedersen.serialize_proof(proof) for pid, proof in self.state.proofs.items()},
            "signatures": {pid: sig.to_hex() for pid, sig in self.state.signatures.items()},
        }

    def history_snapshots(self) -> List[Dict[str, object]]:
        return [
            {
                "sequence": record.sequence,
                "commitments": {
                    pid: pedersen.serialize_commitment(commit) for pid, commit in record.commitments.items()
                },
                "proofs": {pid: pedersen.serialize_proof(proof) for pid, proof in record.proofs.items()},
                "signatures": {pid: sig.to_hex() for pid, sig in record.signatures.items()},
            }
            for record in self.history
        ]

    def closing_payload(self) -> Dict[str, object]:
        return {
            "channel_id": self.channel_id,
            "sequence": self.state.sequence,
            "balances": dict(self.state.balances),
            "commitments": {
                pid: pedersen.serialize_commitment(commit) for pid, commit in self.state.commitments.items()
            },
            "openings": {
                pid: pedersen.serialize_opening(opening) for pid, opening in self.state.openings.items()
            },
            "proofs": {pid: pedersen.serialize_proof(proof) for pid, proof in self.state.proofs.items()},
            "signatures": {pid: sig.to_hex() for pid, sig in self.state.signatures.items()},
        }

