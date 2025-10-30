# Design of a Privacy-Preserving Micropayment Channel Using Homomorphic Hash Functions

> Formatting note: export this Markdown to DOCX using the provided Word template (`report/reference.docx`) to ensure Times New Roman 12 pt and bold headings as required.

---

## Title Page

- **Title**: Design of a Privacy-Preserving Micropayment Channel Using Homomorphic Hash Functions
- **Student Name and Reg. No.**: __________________________
- **Course Name and Code, Slot**: __________________________
- **Faculty Name**: __________________________

---

## 1. Abstract

Micropayment channels enable two parties to exchange a high volume of small payments off-chain while settling on-chain once, reducing fees and latency. However, popular designs leak per-update amounts in the off-chain messages, revealing spending behavior and business relationships. This project presents a two‑party micropayment channel prototype that preserves per‑update privacy using additively homomorphic Pedersen commitments and co‑signed state transitions. Each party’s balance is committed as \(C = g^m h^r\) in a prime‑order group, so commitment multiplication corresponds to hidden value addition; updates never disclose the transfer \(\Delta\). We strengthen integrity with Ed25519 co‑signatures and add a Fiat–Shamir Schnorr proof of knowledge for each commitment opening to provide verifiable confidential balances at cooperative close.

The system consists of a Python FastAPI backend implementing the cryptographic and protocol logic and a Next.js frontend that demonstrates opening a channel, executing private updates, inspecting the signed history, and running benchmarks. Experiments on 10/100/1000 update sequences show update latency around 10–11 ms per update (in Python), signature verification around 0.22 ms, and proof verification around 4.7–4.8 ms per state. Commitment payloads are constant (192 bytes for two commitments), and signature payloads are 128 bytes per state. The prototype demonstrates that private updates are practical and educationally accessible while clearly separating privacy (off‑chain) and disclosure (final settlement only).

---

## 2. Introduction

### 2.1 Background and Theoretical Context

Micropayment channels allow parties to transact off-chain by repeatedly updating a shared state representing balances, then publishing a single settlement transaction on-chain. This amortizes fees and reduces latency. In many classic designs, the off-chain state contains plaintext balances or payment amounts, leaking sensitive information to observers or intermediaries. Additively homomorphic commitments (e.g., Pedersen commitments) provide a simple, standard mechanism to hide these values while supporting algebraic operations.

Pedersen commitments are information‑theoretically hiding and computationally binding under the discrete logarithm assumption. Given generators \(g, h\) in a prime order group \(\mathbb{G}\) of order \(q\), committing to message \(m\) with randomness \(r\) yields \(C = g^m h^r\). The commitment is additively homomorphic: \(C(m_1,r_1)\cdot C(m_2,r_2) = C(m_1+m_2, r_1+r_2)\). We exploit this to update balances privately. To ensure integrity, each state is co‑signed by both participants using Ed25519. To raise the cryptographic bar, we add a non‑interactive Schnorr proof (Fiat–Shamir) of knowledge of the opening \((m, r)\) for each commitment, enabling the simulated ledger to verify disclosures at settlement.

### 2.2 Importance and Motivation

Privacy for off‑chain updates protects user behavior (e.g., subscription usage, content tipping, IoT metering). Even when final settlement reveals end balances, hiding intermediate \(\Delta\) prevents traffic analysis and contractual inference. Pedersen commitments offer a lightweight, well‑understood primitive that is easy to prototype and explain in a cryptology course while being close to practical designs.

### 2.3 Applicability

- Pay‑per‑use web APIs, content platforms, and streaming media
- IoT sensor metering and energy micro‑settlements
- Educational sandbox for confidential state updates and ZK proof composition

### 2.4 Notation and Symbols

- \(\mathbb{G}\): subgroup of order \(q\) of \(\mathbb{Z}_p^*\) (safe prime \(p\)); operation is multiplication mod \(p\).
- \(g, h \in \mathbb{G}\): public generators with unknown discrete log relation.
- \(m \in \mathbb{Z}_q\): integer encoding of a balance; \(r \in \mathbb{Z}_q\): blinding randomness.
- \(C = \mathsf{Com}(m; r) = g^m h^r \bmod p\): Pedersen commitment.
- Transcript hash: \(H(\cdot)\) modeled as a random oracle for Fiat–Shamir.
- State \(S_i = (i, C_A^i, C_B^i)\); digest \(\mathsf{dig}_i = H(S_i)\).
- Proof of knowledge: \(\pi = (t, s_m, s_r)\) with verifier check \(g^{s_m} h^{s_r} \stackrel{?}{=} t C^c\).

### 2.5 Security Properties of Pedersen Commitments (Sketch)

- (Perfect Hiding) For fixed \(m\), the distribution of \(C = g^m h^r\) is uniform over coset \(g^m \cdot \langle h \rangle\). Since \(r\) is uniform in \(\mathbb{Z}_q\), \(C\) leaks no information about \(m\).
- (Computational Binding) Suppose two distinct openings \((m, r) \neq (m', r')\) map to the same \(C\). Then \(g^{m-m'} = h^{r'-r}\). If an adversary finds such a pair, it recovers \(\log_g(h)\), solving DLOG in \(\mathbb{G}\). Under the discrete log assumption, binding holds.
- (Additive Homomorphism) \(\mathsf{Com}(m_1; r_1) \cdot \mathsf{Com}(m_2; r_2) = \mathsf{Com}(m_1+m_2; r_1+r_2)\). This enables private balance updates by multiplying commitments rather than disclosing \(\Delta\).

### 2.6 Generator Derivation and Trapdoor Independence

To avoid trusted setup for \(h\), we derive \(h = g^\alpha\) with \(\alpha = H(\text{"pedersen-h-generator"}) \bmod q\). While a trapdoor exists mathematically (\(\alpha\)), nobody knows it because it is produced by hashing public strings; thus no participant can equivocate between openings without breaking collision resistance/DLOG. The report also includes explicit domain separation so the same \(h\) is not reused across unrelated protocols.

### 2.7 Related Work

Lightning-style payment channels prioritize performance and enforce security with penalty transactions and HTLCs, but intermediate amounts are typically visible to peers. Confidential transactions (CT) hide amounts using Pedersen commitments and range proofs; we borrow the commitment mechanism and adapt it to a two‑party channel setting with knowledge proofs at cooperative close. Bulletproofs reduce range proof sizes logarithmically; adding them is identified as future work.

---

## 3. Methodology

### 3.1 Problem Statement

Design a two‑party micropayment channel where the per‑update transfer \(\Delta\) and intermediate balances remain hidden during channel lifetime. Ensure that the final settlement is verifiable by revealing openings and proofs to a ledger, while integrity is enforced via monotonically increasing sequence numbers and co‑signatures.

### 3.2 Project Architecture

- Backend (FastAPI, Python): cryptographic primitives (Pedersen commitments; Schnorr knowledge proofs), Ed25519 signing, channel state machine (open, update, co‑sign, close), simulated ledger verification, and benchmarking.
- Frontend (Next.js 14): pages for Channel Setup, Payments, History, Benchmarks. The UI never displays \(\Delta\) or plaintext balances; it only shows commitments, proof tuples, signatures, and sequence numbers.
- Data flow: the frontend calls REST endpoints; the backend manages state and returns signed snapshots and proofs. At cooperative close, the ledger verifies signatures, commitment openings, and knowledge proofs.

### 3.3 Cryptographic Primitives

Let \(p\) be a 2048‑bit safe prime and \(q = (p-1)/2\). Let \(g\) be a generator of the order‑\(q\) subgroup and \(h = g^\alpha\) for unknown \(\alpha\) derived deterministically by hashing. For balance \(m\) and randomness \(r\), the commitment is:

\[ C = g^m h^r \pmod p. \]

At settlement, an opening \((m, r)\) verifies if \(C = g^m h^r \bmod p\).

We include a Schnorr proof of knowledge of \((m, r)\) for each commitment. The prover samples \(w_m, w_r \xleftarrow{} \mathbb{Z}_q\) and computes \(t = g^{w_m} h^{w_r}\). The Fiat–Shamir challenge is

\[ c = H(\text{domain} \parallel \text{context} \parallel C \parallel t) \bmod q. \]

Responses are \(s_m = w_m + c m \bmod q\) and \(s_r = w_r + c r \bmod q\). The verifier checks

\[ g^{s_m} h^{s_r} \stackrel{?}{=} t \cdot C^{c} \bmod p. \]

The context includes channel id, sequence, and participant id to bind proofs to a specific state.

### 3.4 Protocol Sketch

State \(S_i = (i, C_A^i, C_B^i)\) where \(i\) is the sequence index. An update where payer A pays \(\Delta\) to B transitions to \(S_{i+1}\) with balances \(m_A' = m_A - \Delta\), \(m_B' = m_B + \Delta\). Fresh randomness is used to compute \(C_A^{i+1}, C_B^{i+1}\). Both parties sign \(H(S_{i+1})\) with Ed25519. At cooperative close, the ledger verifies signatures and the openings \((m_A', r_A'), (m_B', r_B')\) along with the Schnorr proofs.

### 3.5 Modules (Algorithms and Interfaces)

- Commitment operations: commit, verify, add, serialize/deserialize.
- Knowledge proof: prover and verifier with Fiat–Shamir (domain separation and context binding).
- Signing: Ed25519 keygen, sign, verify.
- Channel state machine: `open`, `apply_payment`, `sign_state`, `closing_payload`.
- Simulated ledger: checks last signed state equals submitted commitments, verifies both signatures, openings, and knowledge proofs.

### 3.6 Algorithms (Pseudocode)

Commitment proof of knowledge (Fiat–Shamir):

```text
ProveOpening(params, C, m, r, context):
  w_m, w_r ←$ Z_q
  t ← g^{w_m} · h^{w_r} mod p
  c ← H(domain || context || C || t) mod q
  s_m ← (w_m + c·m) mod q
  s_r ← (w_r + c·r) mod q
  return (t, s_m, s_r)

VerifyOpening(params, C, (t, s_m, s_r), context):
  c ← H(domain || context || C || t) mod q
  return g^{s_m} · h^{s_r} ≟ t · C^c mod p
```

Channel update and signing:

```text
ApplyPayment(Channel, payer, Δ):
  assert Δ > 0 and balances[payer] ≥ Δ
  payee ← other(payer)
  balances[payer] ← balances[payer] – Δ
  balances[payee] ← balances[payee] + Δ
  i ← i + 1
  for pid in {alice, bob}:
    (C_pid, r_pid) ← Commit(params, balances[pid])
    π_pid ← ProveOpening(params, C_pid, balances[pid], r_pid, context=(chid,i,pid))
  signatures ← ∅  // must be re‑collected
```

Cooperative close (ledger):

```text
CoopClose(payload):
  check commitments equal last recorded state
  check Ed25519 signatures over H(S_i)
  for pid in {alice, bob}:
    verify opening (m_pid, r_pid) against C_pid
    verify π_pid over context=(chid,i,pid)
  return verified = true and settled_balances = {m_A, m_B}
```

### 3.7 Correctness Invariants

1. (Conservation) \(m_A^i + m_B^i = m_A^0 + m_B^0\) for all \(i\). Proof: each update applies \(+\Delta\) to one party and \(-\Delta\) to the other.
2. (Commitment Consistency) For each \(i\) and participant \(X\), \(C_X^i = \mathsf{Com}(m_X^i; r_X^i)\).
3. (Signature Freshness) State digests are strictly ordered by \(i\); signatures for \(i\) cannot be replayed as \(i' > i\) because \(H\) binds \(i\) into the digest.

### 3.8 Security Definitions (Informal)

- Completeness: honest parties always construct proofs that the verifier accepts.
- Knowledge soundness: from any prover that convinces the verifier with non‑negligible probability, there exists an extractor that outputs an opening \((m,r)\) to \(C\) (under ROM and DLOG assumptions).
- Hiding: the view of any PPT adversary observing \(C\) is independent of \(m\).
- Binding: no PPT adversary can produce \((m,r) \neq (m',r')\) with \(\mathsf{Com}(m;r) = \mathsf{Com}(m';r')\) except with negligible probability.

### 3.9 Proof Sketches

- (Completeness) Direct from arithmetic: plugging \(s_m, s_r\) into the verifier equation yields identity by exponent laws.
- (Knowledge Soundness) The Schnorr protocol is a standard proof of knowledge; using the Forking Lemma in ROM, two accepting transcripts with challenges \(c \neq c'\) reveal \((m,r)\).
- (Binding) If two different openings exist, \(g^{m-m'} = h^{r'-r}\). Taking discrete logs recovers \(\log_g(h)\), breaking DLOG.

### 3.10 Complexity Analysis

Per update (two commitments):

- Commitments: 2 exponentiations in \(g\) and 2 in \(h\) (dominant cost).
- Proofs: one \(t\) (2 exponentiations), one verification per participant (3 exponentiations counting \(C^c\)).
- Signatures: 2 Ed25519 sign + 2 verify (cheap vs. big‑int exponents).

Let \(E\) denote a modular exponentiation at 2048 bits; empirical timings align with ~10–11 ms/update and ~4.7–4.8 ms/proof‑verify on the test machine.

### 3.11 Parameterization and Encoding

- Group: RFC‑3526 2048‑bit safe prime (educational; EC groups recommended in production).
- Message encoding: balances reduced mod \(q\); inputs validated to be non‑negative Python ints.
- Domain separation: `pedersen/opening-proof/v1` and `(channel_id, sequence, participant)` bound into \(c\).
- Logging: Δ never logged; the UI renders only digests, commitments, proofs, and signatures.

### 3.12 Security Games (Informal Definitions)

1. (Hiding) Adversary \(\mathcal{A}\) submits \(m_0, m_1\). Challenger samples \(b\in\{0,1\}\), \(r\leftarrow \mathbb{Z}_q\), returns \(C = g^{m_b} h^r\). \(\mathcal{A}\) outputs \(b'\). Advantage is \(|\Pr[b'=b]-1/2|\). Pedersen is perfectly hiding, so advantage is 0.

2. (Binding) \(\mathcal{A}\) outputs \(C, (m,r), (m',r')\) with \((m,r)\neq(m',r')\) and both openings valid. Advantage is \(\Pr[\mathsf{Verify}(C,m,r)=\mathsf{Verify}(C,m',r')=1]\). Under DLOG in \(\mathbb{G}\), advantage is negligible.

3. (Knowledge of Opening) \(\mathcal{A}\) interacts with the non‑interactive prover algorithm to produce \((C, \pi)\) accepted by the verifier. In ROM, a polynomial‑time extractor obtains \((m,r)\) such that \(C=\mathsf{Com}(m;r)\) except with negligible probability.

### 3.13 Optional Range Proofs (Design Outline)

To prevent negative balances or overflow without revealing \(m\), one can prove \(m \in [0, 2^k)\) using:

- Borromean ring signatures (CT-style) with \(k\) commitments to bits and per‑bit proofs; size \(O(k)\).
- Bulletproofs with inner‑product arguments; size \(O(\log k)\). Let \(V = g^m h^r\). The prover demonstrates that \(m\) is a non‑negative \(k\)-bit integer via a committed vector \(\mathbf{a}_L, \mathbf{a}_R\) satisfying \(\mathbf{a}_L \circ \mathbf{a}_R = \mathbf{0}\) and \(\langle \mathbf{a}_L, \mathbf{2}^n \rangle = m\). The verifier checks a commitment equation and an inner‑product relation with logarithmic‑size proofs.

Integrating Bulletproofs would raise settlement verification cost and message size, but provides strong guarantees that protocol logic alone cannot violate balance bounds.

---

## 4. Implementation

### 4.1 Tools / Languages

- Python 3.11, FastAPI, Uvicorn
- PyNaCl (Ed25519), standard big‑int modular arithmetic for commitments
- Next.js 14 (TypeScript), React Query, Tailwind CSS

### 4.2 Environment Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.src.api.main:app --reload --port 8000

cd frontend
export NEXT_PUBLIC_API_BASE=http://localhost:8000
npm install && npm run dev
```

### 4.3 Code Snippets (Key Excerpts)

Commitment and proof verification (excerpts):

```text
238:289:backend/src/crypto/pedersen.py
def _compute_challenge(...):
    ...
def prove_opening(...)-> CommitmentProof:
    w_m = random_scalar(params)
    w_r = random_scalar(params)
    t_value = (g**w_m * h**w_r) % p
    c = H(domain || context || C || t) mod q
    s_m = (w_m + c*m) mod q; s_r = (w_r + c*r) mod q
def verify_opening_proof(...)-> bool:
    return g**s_m * h**s_r == t * C**c (mod p)
```

Channel proof generation on each update (excerpt):

```text
142:155:backend/src/protocol/channel.py
def _set_balances(...):
    for pid, balance in balances.items():
        commitment, opening = pedersen.commit(self.params, balance)
        context = proof_context(self.channel_id, self.state.sequence, pid)
        proof = pedersen.prove_opening(self.params, balance, opening, commitment, context=context)
        assert pedersen.verify_opening_proof(self.params, commitment, proof, context=context)
    self.state.proofs = new_proofs
```

### 4.4 API Overview

- `POST /channel/open { deposit_alice, deposit_bob } → { channel_id, sequence, commitments, proofs, signatures, verify_keys }`
- `POST /channel/update { payer, delta } → { …state… }`
- `POST /channel/cosign { participant? } → { …state… }`
- `POST /channel/close { } → { settled_balances, verified }`
- `GET /channel/state`, `GET /channel/history`, `GET /eval/bench?N=<int>`

### 4.5 Screenshots (UI)

Place the screenshots provided in the chat into the `figures/` folder and reference them here:

- `figures/channel_setup.png` – Channel deposits and verifying keys.
- `figures/payments.png` – Private updates and co‑sign/close panel.
- `figures/history.png` – Signed state history with proofs.
- `figures/benchmarks.png` – Timings table and latest state snapshot.

Embed with:

```markdown
![Channel Setup](../figures/channel_setup.png)
```

---

## 5. Results and Discussion

### 5.1 Test Cases and Correctness

- Crypto unit tests verify commitment round‑trip, homomorphism, signing, and proof soundness (wrong context fails verification).
- Protocol tests cover open → update → co‑sign, proof validity across updates, and cooperative close verification on the ledger.

### 5.2 Performance Measurements

Hardware/Runtime: macOS (Python 3.12, FastAPI dev server). Measurements are end‑to‑end in the Python backend. We ran benchmarks for N ∈ {10, 100, 1000} updates; each iteration applies an update, co‑signs, verifies signatures, and verifies proofs (for analysis; in a real system, proof verification is mainly required at close).

Observed timings (milliseconds):

| N | Update avg | Update min | Update max | Sign avg | Verify avg | Proof_verify avg |
|---|---:|---:|---:|---:|---:|---:|
| 10 | 11.255 | 10.826 | 12.069 | 0.113 | 0.224 | 4.768 |
| 100 | 10.834 | 10.459 | 12.529 | 0.105 | 0.223 | 4.689 |
| 1000 | 11.183 | 10.392 | 24.240 | 0.109 | 0.233 | 4.842 |

Payload sizes for the final state: commitments 192 bytes (two hex-encoded commitments), signatures 128 bytes (two Ed25519 signatures). Proofs are shown per participant as `(t, s_m, s_r)` hex values; their size depends on modulus length (here, 2048‑bit group elements and scalars).

#### Interpretation

- Update latency is ~10–11 ms in Python; most cost is modular exponentiation for commitment refresh. In optimized C/EC implementations, this would drop significantly.
- Signature verification is fast (<0.25 ms per state). Proof verification averages ~4.7–4.8 ms; in real deployments this cost appears primarily at close; we verify on each iteration to stress the crypto path.
- Constant commitment and signature sizes simplify reasoning about bandwidth; proofs add overhead but only at settlement.

#### Statistical Methodology (how to reproduce)

For a sequence of observed latencies \(x_1,\dots,x_n\), compute the sample mean \(\bar{x} = \tfrac{1}{n}\sum_i x_i\) and unbiased standard deviation \(s = \sqrt{\tfrac{1}{n-1}\sum_i (x_i-\bar{x})^2}\). A (1-\(\alpha\)) confidence interval for the mean under mild assumptions is

\[ \bar{x} \pm t_{n-1,1-\alpha/2} \cdot \frac{s}{\sqrt{n}}, \]

where \(t_{n-1,1-\alpha/2}\) is the \(t\)-distribution quantile. Our benchmark tool currently records averages/min/max; to compute confidence intervals, export per‑iteration timings and apply the above formula.

### 5.3 Comparison with Non‑Private Baseline

| Property | Plain channel (balances in clear) | Private channel (this work) |
|---|---|---|
| Per‑update privacy | None | Hides \(\Delta\) and intermediate balances (commitments only) |
| Integrity | Co‑signatures | Co‑signatures + context‑bound proofs |
| Update cost | lowest | + commitment refresh cost |
| Verification cost | signatures only (~0.22 ms) | + proof verify (~4.7–4.8 ms per state, mostly at close) |
| Message size (state) | small | + commitments + proofs |

The private design pays modest computational overhead for strong privacy properties and verifiable settlement.

### 5.4 Threat Model and Security Discussion

- Honest‑but‑curious parties learn nothing about \(\Delta\) from messages: only commitments (hiding) and co‑signatures are exchanged. Sequence numbers prevent replay. Proofs provide knowledge of openings at close.
- Binding holds under the discrete logarithm assumption: it is computationally infeasible to open a commitment to two different values.
- Limitations: range proofs are not implemented, so negative or out‑of‑range balances are prevented by protocol logic rather than ZK. Dispute handling for non‑cooperative closes is not implemented (simulated ledger only). Side‑channels and timing are not mitigated in Python code.

### 5.5 Threat Coverage Matrix

| Threat | Mitigation | Notes |
|---|---|---|
| Replay of stale state | Sequence numbers + signatures over digest | Digest binds \(i\), commitments |
| Amount leakage | Pedersen commitments (perfect hiding) | Only openings at cooperative close |
| Forged openings | Schnorr knowledge proofs + verification | ROM and DLOG assumptions |
| Signature forgery | Ed25519 unforgeability | Standard assumptions |
| Malicious generator trapdoor | Derive \(h\) by hashing; unknown \(\alpha\) | Domain separation |
| Non‑cooperative close | Out of scope (simulator only) | Future work |
| Side channels / timing | Out of scope (Python) | Use constant‑time EC libs in practice |

---

## 6. Conclusion and Future Work

We implemented an end‑to‑end micropayment channel with private off‑chain updates using Pedersen commitments, Ed25519 co‑signatures, and Schnorr knowledge proofs. A full web demo and benchmark suite demonstrate practicality and provide quantitative insights. Results indicate that proof verification dominates cryptographic cost (~4.7–4.8 ms per state in Python) while updates remain around 10–11 ms, which is reasonable for instructional and prototype settings.

Future work:

1. Range proofs (e.g., Bulletproofs) to ensure balances lie in valid ranges without disclosure.
2. Non‑cooperative close with challenge periods and penalty logic in the ledger simulator.
3. Elliptic‑curve commitments (e.g., secp256k1 or Ristretto) with constant‑time implementations.
4. Signature aggregation (Schnorr/BLS) and hashing transcript formalization.
5. Formal proofs and mechanized tests for protocol invariants.

---

## 7. References

1. T. P. Pedersen, “Non-Interactive and Information-Theoretic Secure Verifiable Secret Sharing,” in Advances in Cryptology — CRYPTO’91, LNCS 576, 1992, pp. 129–140.
2. C.-P. Schnorr, “Efficient Signature Generation by Smart Cards,” Journal of Cryptology, vol. 4, 1991, pp. 161–174.
3. J. Poon and T. Dryja, “The Bitcoin Lightning Network: Scalable Off-Chain Instant Payments,” 2016 (BOLT specifications and design notes).
4. D. Boneh and V. Shoup, “A Graduate Course in Applied Cryptography,” 2020. (Commitments and discrete log background.)
5. B. Bünz, J. Bootle, D. Boneh, et al., “Bulletproofs: Short Proofs for Confidential Transactions and More,” IEEE S&P, 2018.
6. FastAPI Documentation, https://fastapi.tiangolo.com
7. PyNaCl (libsodium bindings) Documentation, https://pynacl.readthedocs.io


---

## Appendix A — Mathematical Details

### A.1 Proof that Pedersen is Perfectly Hiding

For any fixed \(m\) and any \(C \in \mathbb{G}\), there exists exactly one \(r\) such that \(C = g^m h^r\), because \(h\) generates \(\mathbb{G}\). As \(r \leftarrow \mathbb{Z}_q\) is uniform, the distribution of \(C\) is uniform over \(\mathbb{G}\) up to a coset, independent of \(m\). Hence, for any two messages \(m_0, m_1\), the distributions of \(C\) are identical.

### A.2 Proof (Sketch) of Computational Binding

Assume an adversary outputs \((m,r) \neq (m',r')\) with \(g^m h^r = g^{m'} h^{r'}\). Then \(g^{m-m'} = h^{r'-r} = g^{\alpha(r'-r)}\). Therefore \(\alpha = (m-m')(r'-r)^{-1} \bmod q\), recovering \(\log_g(h)\) and breaking DLOG. Hence, binding holds under the discrete logarithm assumption.

### A.3 Schnorr Knowledge Proof Extractor (ROM)

Given two accepting transcripts \((t, c, s_m, s_r)\) and \((t, c', s'_m, s'_r)\) with \(c \neq c'\), subtract responses to obtain \((s_m-s'_m) = (c-c') m\) and \((s_r-s'_r) = (c-c') r\) in \(\mathbb{Z}_q\); dividing by \(c-c'\) reveals \((m, r)\). The Forking Lemma ensures the extractor obtains two transcripts in ROM.

### A.4 Re-randomization and Aggregation

Given \(C = \mathsf{Com}(m; r)\) and fresh \(\rho\), we can derive \(C' = C \cdot h^{\rho} = \mathsf{Com}(m; r+\rho)\), preserving the message. Similarly, products of commitments aggregate messages and randomness additively.

### A.5 Balance Encoding and Overflow Handling

Balances are stored in Python integers then reduced mod \(q\) in the commitment layer. Protocol logic enforces non‑negativity and conservation; in production, range proofs would guarantee bounds without relying on application logic.

---

## Appendix B — Full REST API and Types (Schema Summary)

```
POST /channel/open
  { deposit_alice: int, deposit_bob: int, channel_id?: string }
  -> { channel_id, sequence, commitments: {alice,bob}, proofs: {alice,bob}, signatures, verify_keys }

POST /channel/update
  { payer: "alice"|"bob", delta: int }
  -> { channel_id, sequence, commitments, proofs, signatures, verify_keys }

POST /channel/cosign
  { participant?: "alice"|"bob" }
  -> latest state (as above)

POST /channel/close
  {}
  -> { channel_id, sequence, settled_balances: {alice,bob}, verified: true }

GET /channel/state -> latest state
GET /channel/history -> { channel_id, history: [ ... snapshots ... ] }
GET /eval/bench?N=100 -> timings + sizes + latest state snapshot
```

---

## Appendix C — Reproducibility Checklist

1. Create a Python virtual environment and install backend requirements.
2. Start the backend (`uvicorn backend.src.api.main:app --reload --port 8000`).
3. Start the frontend (`npm run dev`) with `NEXT_PUBLIC_API_BASE` set.
4. Open a channel (e.g., 100/25), perform multiple updates, co‑sign, and close.
5. Run benchmarks with N ∈ {10, 100, 1000}; export JSON outputs for plots.
6. Capture screenshots for Channel Setup, Payments, History, and Benchmarks.
7. Export this report to DOCX using the Word template and submit along with figures.

---

## Appendix D — Notation Table

| Symbol | Meaning |
|---|---|
| \(p\) | Safe prime modulus; \(q=(p-1)/2\) |
| \(\mathbb{G}\) | Order‑\(q\) subgroup of \(\mathbb{Z}_p^*\) |
| \(g, h\) | Public generators with unknown relation |
| \(m\) | Balance value (reduced mod \(q\)) |
| \(r\) | Randomness/blinding scalar |
| \(C\) | Commitment \(g^m h^r \bmod p\) |
| \(t\) | Schnorr commitment \(g^{w_m}h^{w_r}\) |
| \(c\) | Fiat–Shamir challenge hash in \(\mathbb{Z}_q\) |
| \(s_m, s_r\) | Schnorr responses |
| \(S_i\) | Channel state at sequence \(i\) |
| \(\mathsf{dig}_i\) | Hash digest of \(S_i\) used for co‑signing |
| \(\Delta\) | Transfer amount per update |


