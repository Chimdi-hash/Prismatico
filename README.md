# Prismatico

![GenLayer](https://img.shields.io/badge/Network-GenLayer_Studio-blue?style=flat-square)
![Language](https://img.shields.io/badge/Language-Python-yellow?style=flat-square)
![Status](https://img.shields.io/badge/Status-Live-success?style=flat-square)

**Prismatico** is a stateful semantic authorization boundary designed for GenLayer. It allows a creator to establish strict, natural-language conditions under which a designated delegate is authorized to execute actions. When that delegate requests an action, GenLayer determines whether the action falls safely within the semantic boundary. A successful `APPROVED` decision consumes one unit of allowance and produces an immutable evaluation record.

---

## 📖 Table of Contents
1. [Why Prismatico](#-why-prismatico)
2. [How It Works](#-how-it-works)
3. [Example Usage](#-example-usage)
4. [Boundary Lifecycle](#-boundary-lifecycle)
5. [Semantic Consensus](#-semantic-consensus)
6. [Contract Interface](#-contract-interface)
7. [State Model & Replay Protection](#-state-model--replay-protection)
8. [Live Deployment](#-live-deployment)

---

## 🧠 Why Prismatico

Traditional smart contract permissions can answer *who* may call a function (e.g., `onlyOwner`), but they are less suited for nuanced, human-language limits on *what* an actor may do. Prismatico bridges this gap by acting as a smart semantic firewall. It combines deterministic actor authorization with GenLayer's semantic judgment, making the granted authority explicitly bounded, observable, and strictly consumable.

## ⚙️ How It Works

```text
Creator
    |
    | establish_boundary(...)
    v
Designated Delegate
    |
    | propose_execution(...)
    v
Bounded Semantic Snapshot
    |
    v
GenLayer Semantic Consensus
    |
    +--> APPROVED     -> consume one allowance unit, persist evaluation
    +--> REJECTED     -> persist evaluation, consume no allowance
    +--> AMBIGUOUS    -> persist evaluation, consume no allowance
```

The creator owns the boundary. The stored `delegate` is the only address permitted to request execution intents, and the boundary conditions cannot be edited after creation. A new authority grant requires establishing a completely new boundary.

## 📝 Example Usage

**Boundary Conditions:**
```text
The delegate may approve expenses related to cloud infrastructure scaling,
but may not authorize new hardware purchases or alter salary payments.
```

**Proposed Intent 1:** `Increase AWS instance count from 4 to 8 to handle spike.`
*Result:* `APPROVED`; `uses_remaining` decreases by one.

**Proposed Intent 2:** `Approve $5,000 for new employee laptops.`
*Result:* `REJECTED`; `uses_remaining` is unchanged.

## ⏳ Boundary Lifecycle

Boundaries have four derived states, evaluated in this exact order:

1. `TERMINATED` — The creator has prematurely cancelled the boundary.
2. `DEPLETED` — The `uses_remaining` allowance is exactly zero.
3. `EXPIRED` — The current transaction timestamp is at or after the boundary's `expiration_ts`.
4. `ACTIVE` — None of the terminal conditions applies.

Only an un-terminated boundary may be terminated by the creator, including one that is already expired or depleted. Historical evaluation records remain permanently readable after any lifecycle changes.

## 🤖 Semantic Consensus

GenLayer evaluates a single question: whether the proposed execution intent clearly and unambiguously falls within the full authority granted by the registered boundary conditions. The conditions must be satisfied as a whole; a direct conflict with any restriction is `REJECTED`. Any missing, ambiguous, contradictory, or externally dependent information is marked `AMBIGUOUS`, which serves as a fail-safe and never as an implicit approval.

The leader node evaluates a bounded captured snapshot, and the validator nodes independently evaluate the same snapshot. Prismatico requires strict equivalence checking. The semantic prompt carefully frames the boundary and submitted fields as untrusted data, ensuring the contract does not browse external facts or store model reasoning, preventing state bloat and injection vulnerabilities.

## 🛠 Contract Interface

The contract is built using `py-genlayer` and follows the Optimistic Democracy consensus model. The public ABI contains standard write and view methods.

### Writes

- `establish_boundary(title, conditions, delegate, allowance, expiration_ts) -> str`
- `propose_execution(boundary_id, request_nonce, execution_context, execution_intent) -> str`
- `terminate_boundary(boundary_id)`

`establish_boundary` binds the creator, delegate, text constraints, use limit, and expiry. `propose_execution` requires the exact stored delegate and a unique request nonce. Only an `APPROVED` result decrements the boundary allowance; other semantic outcomes do not consume authority. `terminate_boundary` is strictly creator-only.

### Views

- `get_boundary(boundary_id) -> dict`
- `get_evaluation(eval_id) -> dict`
- `get_boundary_state(boundary_id) -> str`

## 🔒 State Model & Replay Protection

Prismatico stores boundary records and evaluation records as serialized JSON strings in two `TreeMap` structures. To prevent double-processing and replay attacks, `propose_execution` demands a unique `request_nonce` tied to the specific boundary and delegate.

Evaluation IDs are entirely deterministic. The same boundary, delegate, and `request_nonce` cannot be finalized twice, even if the earlier result was `REJECTED` or `AMBIGUOUS`. The contract prevents unauthorized mutations and relies strictly on canonical JSON structures for state storage.

---

## 🚀 Live Deployment

This contract is successfully deployed and running on the **GenLayer Studio** network:

- **Contract Address:** `0xe92BDB51eC3679A9Bbff690AA2284accC9Dff47c`
- **Studio Explorer:** [View on GenLayer Explorer](https://explorer-studio.genlayer.com/address/0xe92BDB51eC3679A9Bbff690AA2284accC9Dff47c)
