from backend.src.crypto import pedersen, signing


def test_pedersen_commitment_roundtrip():
    params = pedersen.default_parameters()
    commitment, opening = pedersen.commit(params, 123)

    assert pedersen.verify(params, commitment, 123, opening)
    assert not pedersen.verify(params, commitment, 124, opening)


def test_pedersen_opening_proof():
    params = pedersen.default_parameters()
    message = 77
    commitment, opening = pedersen.commit(params, message)
    context = b"test-channel|0|alice"

    proof = pedersen.prove_opening(params, message, opening, commitment, context=context)
    assert pedersen.verify_opening_proof(params, commitment, proof, context=context)

    # Wrong context invalidates the proof
    assert not pedersen.verify_opening_proof(params, commitment, proof, context=b"wrong")


def test_pedersen_homomorphism():
    params = pedersen.default_parameters()

    commitment_a, opening_a = pedersen.commit(params, 40)
    commitment_b, opening_b = pedersen.commit(params, 60)

    combined_commitment = pedersen.add_commitments(params, [commitment_a, commitment_b])
    combined_opening = pedersen.add_openings(params, [opening_a, opening_b])
    combined_message = pedersen.add_messages(params, [40, 60])

    assert pedersen.verify(params, combined_commitment, combined_message, combined_opening)


def test_signing_roundtrip():
    signing_key, verify_key = signing.generate_keypair()
    message = b"channel-state"

    signature = signing.sign(message, signing_key)
    assert signing.verify(message, signature, verify_key)
    assert not signing.verify(b"tampered", signature, verify_key)

    encoded = signature.to_hex()
    assert signing.verify(message, signing.Signature.from_hex(encoded), verify_key)

