"""Ed25519 signing helpers built on PyNaCl.

The micropayment channel requires each state update to be co-signed by both
participants. wrapping PyNaCl keeps the dependency surface small while giving
us constant-time, well-tested Ed25519 primitives.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from nacl import exceptions as nacl_exceptions
from nacl import signing


@dataclass(frozen=True)
class SigningKey:
    """Wrapper around PyNaCl's SigningKey with type-annotated helpers."""

    _key: signing.SigningKey

    @classmethod
    def generate(cls) -> SigningKey:
        return cls(signing.SigningKey.generate())

    @property
    def verify_key(self) -> VerifyKey:
        return VerifyKey(self._key.verify_key)

    def sign(self, message: bytes) -> "Signature":
        signed = self._key.sign(message)
        return Signature(signed.signature)

    def to_hex(self) -> str:
        return self._key.encode().hex()

    @classmethod
    def from_hex(cls, value: str) -> SigningKey:
        return cls(signing.SigningKey(bytes.fromhex(value)))


@dataclass(frozen=True)
class VerifyKey:
    """Verification key container with serialization helpers."""

    _key: signing.VerifyKey

    def verify(self, message: bytes, signature: "Signature") -> bool:
        try:
            self._key.verify(message, signature.value)
            return True
        except nacl_exceptions.BadSignatureError:
            return False

    def to_hex(self) -> str:
        return self._key.encode().hex()

    @classmethod
    def from_hex(cls, value: str) -> VerifyKey:
        return cls(signing.VerifyKey(bytes.fromhex(value)))


@dataclass(frozen=True)
class Signature:
    """Lightweight wrapper for raw signature bytes."""

    value: bytes

    def to_hex(self) -> str:
        return self.value.hex()

    @classmethod
    def from_hex(cls, value: str) -> "Signature":
        return cls(bytes.fromhex(value))


def generate_keypair() -> Tuple[SigningKey, VerifyKey]:
    """Return a freshly generated Ed25519 signing/verification key pair."""

    sk = SigningKey.generate()
    return sk, sk.verify_key


def sign(message: bytes, signing_key: SigningKey) -> Signature:
    return signing_key.sign(message)


def verify(message: bytes, signature: Signature, verify_key: VerifyKey) -> bool:
    return verify_key.verify(message, signature)

