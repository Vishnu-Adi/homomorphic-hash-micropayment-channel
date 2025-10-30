"""Pedersen-style additively homomorphic commitments.

This module exposes a small API tailored for the micropayment channel prototype:

* Fixed safe-prime parameters (RFC 3526 2048-bit group).
* Helper functions for generating random scalars and deriving generators.
* Commitment helpers for creation, verification, aggregation, and serialization.

The implementation keeps the interface deliberately simple so it can be explained
clearly in the course report while remaining mathematically sound.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Dict, Iterable, Optional, Tuple

import secrets


# RFC 3526 2048-bit MODP Group (Group 14)
_P_HEX = (
    "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
    "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
    "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
    "E485B576625E7EC6F44C42E9A63A3620FFFFFFFFFFFFFFFF"
)


@dataclass(frozen=True)
class CommitmentParameters:
    """Public parameters for the commitment scheme."""

    p: int
    q: int
    g: int
    h: int


@dataclass(frozen=True)
class Commitment:
    """A simple wrapper to make type signatures clearer."""

    value: int

    def __int__(self) -> int:  # pragma: no cover - trivial
        return self.value

    def to_hex(self) -> str:
        return format(self.value, "x")


@dataclass(frozen=True)
class CommitmentOpening:
    """Stores the scalar randomness needed to open a commitment."""

    randomness: int


@dataclass(frozen=True)
class CommitmentProof:
    """Non-interactive Schnorr-style proof of knowledge of a commitment opening."""

    t: int
    response_m: int
    response_r: int


_PROOF_DOMAIN_SEPARATOR = b"pedersen/opening-proof/v1"


def _pow(base: int, exponent: int, modulus: int) -> int:
    """Small wrapper for Python's built-in pow with three arguments."""

    return pow(base, exponent, modulus)


def _hash_to_scalar(seed: bytes, q: int) -> int:
    """Derive a non-zero scalar less than q from arbitrary seed bytes."""

    attempt = 0
    while True:
        digest = sha256(seed + attempt.to_bytes(4, "big", signed=False)).digest()
        scalar = int.from_bytes(digest, "big") % q
        if scalar != 0:
            return scalar
        attempt += 1


def default_parameters() -> CommitmentParameters:
    """Return hard-coded commitment parameters.

    The parameters correspond to the 2048-bit safe-prime MODP group from RFC 3526.
    The generator ``g`` is 2, which generates the order-q subgroup. ``h`` is a
    second generator derived deterministically from a domain-separated hash so
    that everyone can reproduce the same value without trusted setup.
    """

    p = int(_P_HEX, 16)
    q = (p - 1) // 2
    g = 2
    h = _pow(g, _hash_to_scalar(b"pedersen-h-generator", q), p)
    return CommitmentParameters(p=p, q=q, g=g, h=h)


def random_scalar(params: CommitmentParameters) -> int:
    """Sample a scalar uniformly from ``[1, q-1]``."""

    while True:
        k = secrets.randbelow(params.q)
        if k != 0:
            return k


def commit(
    params: CommitmentParameters,
    message: int,
    randomness: Optional[int] = None,
) -> Tuple[Commitment, CommitmentOpening]:
    """Create a Pedersen commitment to ``message``.

    Args:
        params: Public parameters (prime modulus and generators).
        message: Integer message to commit; reduced modulo ``q`` internally.
        randomness: Optional externally supplied randomness. When omitted, a new
            scalar is sampled using :func:`random_scalar`.

    Returns:
        A tuple ``(Commitment, CommitmentOpening)`` suitable for storage.
    """

    r = randomness if randomness is not None else random_scalar(params)
    m = message % params.q
    value = (_pow(params.g, m, params.p) * _pow(params.h, r, params.p)) % params.p
    return Commitment(value=value), CommitmentOpening(randomness=r)


def verify(
    params: CommitmentParameters,
    commitment: Commitment,
    message: int,
    opening: CommitmentOpening,
) -> bool:
    """Verify that ``commitment`` opens to ``message`` with ``opening``."""

    lhs = commitment.value % params.p
    m = message % params.q
    rhs = (_pow(params.g, m, params.p) * _pow(params.h, opening.randomness, params.p)) % params.p
    return lhs == rhs


def add_commitments(
    params: CommitmentParameters,
    commitments: Iterable[Commitment],
) -> Commitment:
    """Aggregate commitments homomorphically (addition in the exponent)."""

    acc = 1
    for commitment in commitments:
        acc = (acc * commitment.value) % params.p
    return Commitment(value=acc)


def add_messages(
    params: CommitmentParameters,
    messages: Iterable[int],
) -> int:
    """Helper for summing messages modulo ``q`` consistently."""

    total = 0
    for message in messages:
        total = (total + message) % params.q
    return total


def add_openings(
    params: CommitmentParameters,
    openings: Iterable[CommitmentOpening],
) -> CommitmentOpening:
    """Combine openings when commitments are added together."""

    total = 0
    for opening in openings:
        total = (total + opening.randomness) % params.q
    return CommitmentOpening(randomness=total)


def negate_commitment(params: CommitmentParameters, commitment: Commitment) -> Commitment:
    """Return the inverse commitment, representing negation of the message."""

    inverse = _pow(commitment.value, params.p - 2, params.p)
    return Commitment(value=inverse)


def commitment_difference(
    params: CommitmentParameters,
    left: Commitment,
    right: Commitment,
) -> Commitment:
    """Compute ``left - right`` in the commitment group."""

    return add_commitments(params, [left, negate_commitment(params, right)])


def serialize_commitment(commitment: Commitment) -> str:
    """Serialize commitment to a hex string."""

    return commitment.to_hex()


def deserialize_commitment(hex_value: str) -> Commitment:
    """Restore a commitment from its hexadecimal representation."""

    return Commitment(value=int(hex_value, 16))


def serialize_opening(opening: CommitmentOpening) -> str:
    """Serialize an opening scalar to hex."""

    return format(opening.randomness, "x")


def deserialize_opening(hex_value: str) -> CommitmentOpening:
    """Restore an opening from its hex representation."""

    return CommitmentOpening(randomness=int(hex_value, 16))


def _int_to_bytes(value: int, length: int) -> bytes:
    return value.to_bytes(length, "big")


def _commitment_byte_length(params: CommitmentParameters) -> int:
    return (params.p.bit_length() + 7) // 8


def _compute_challenge(
    params: CommitmentParameters,
    commitment: Commitment,
    t_value: int,
    context: bytes,
) -> int:
    byte_length = _commitment_byte_length(params)
    hasher = sha256()
    hasher.update(_PROOF_DOMAIN_SEPARATOR)
    hasher.update(context)
    hasher.update(_int_to_bytes(commitment.value % params.p, byte_length))
    hasher.update(_int_to_bytes(t_value % params.p, byte_length))
    challenge = int.from_bytes(hasher.digest(), "big") % params.q
    if challenge == 0:
        # Extremely unlikely; fall back to 1 to avoid degenerate proofs.
        return 1
    return challenge


def prove_opening(
    params: CommitmentParameters,
    message: int,
    opening: CommitmentOpening,
    commitment: Commitment,
    *,
    context: bytes,
) -> CommitmentProof:
    """Produce a Schnorr-style proof of knowledge of the commitment opening."""

    w_m = random_scalar(params)
    w_r = random_scalar(params)
    t_value = (_pow(params.g, w_m, params.p) * _pow(params.h, w_r, params.p)) % params.p
    challenge = _compute_challenge(params, commitment, t_value, context)
    m = message % params.q
    response_m = (w_m + challenge * m) % params.q
    response_r = (w_r + challenge * opening.randomness) % params.q
    return CommitmentProof(t=t_value, response_m=response_m, response_r=response_r)


def verify_opening_proof(
    params: CommitmentParameters,
    commitment: Commitment,
    proof: CommitmentProof,
    *,
    context: bytes,
) -> bool:
    """Verify a Schnorr-style proof of knowledge of a commitment opening."""

    challenge = _compute_challenge(params, commitment, proof.t, context)
    left = (_pow(params.g, proof.response_m, params.p) * _pow(params.h, proof.response_r, params.p)) % params.p
    right = (proof.t * _pow(commitment.value % params.p, challenge, params.p)) % params.p
    return left == right


def serialize_proof(proof: CommitmentProof) -> Dict[str, str]:
    return {
        "t": format(proof.t, "x"),
        "response_m": format(proof.response_m, "x"),
        "response_r": format(proof.response_r, "x"),
    }


def deserialize_proof(data: Dict[str, str]) -> CommitmentProof:
    return CommitmentProof(
        t=int(data["t"], 16),
        response_m=int(data["response_m"], 16),
        response_r=int(data["response_r"], 16),
    )

