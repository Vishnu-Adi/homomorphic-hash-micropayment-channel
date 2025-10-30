from backend.src.crypto import pedersen
from backend.src.protocol.channel import Channel, proof_context
from backend.src.protocol.ledger import SimulatedLedger


def test_channel_update_flow():
    params = pedersen.default_parameters()
    channel = Channel.open(200, 50, params=params)

    assert channel.state.sequence == 0
    assert channel.state.balances == {"alice": 200, "bob": 50}
    for participant in ("alice", "bob"):
        context = proof_context(channel.channel_id, channel.state.sequence, participant)
        proof = channel.state.proofs[participant]
        commitment = channel.state.commitments[participant]
        assert pedersen.verify_opening_proof(params, commitment, proof, context=context)

    channel.apply_payment("alice", 25)
    assert channel.state.sequence == 1
    assert channel.state.balances == {"alice": 175, "bob": 75}
    for participant in ("alice", "bob"):
        context = proof_context(channel.channel_id, channel.state.sequence, participant)
        proof = channel.state.proofs[participant]
        commitment = channel.state.commitments[participant]
        assert pedersen.verify_opening_proof(params, commitment, proof, context=context)

    channel.sign_state("alice")
    channel.sign_state("bob")
    assert channel.is_fully_signed()
    assert channel.verify_signatures()


def test_ledger_cooperative_close():
    params = pedersen.default_parameters()
    channel = Channel.open(150, 75, params=params)
    channel.apply_payment("bob", 10)

    ledger = SimulatedLedger(params)
    ledger.register_channel(channel)
    ledger.update_state(channel)

    channel.sign_state("alice")
    channel.sign_state("bob")

    payload = channel.closing_payload()
    result = ledger.cooperative_close(payload)

    assert result["verified"] is True
    assert result["settled_balances"] == {"alice": 140, "bob": 85}

