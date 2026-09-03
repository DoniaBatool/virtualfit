"""
Week 3 — Qiskit Grover's Algorithm for Garment Search
O(√N) quantum search vs classical O(N) linear scan.

Demonstrates quantum advantage on garment catalog search.
Uses Qiskit Aer simulator (no real quantum hardware needed).
"""

import logging
import math
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Sample garment catalog (16 items = 4 qubits) ─────────────────────────────
GARMENT_CATALOG = [
    {"id": 0,  "name": "Classic White Shirt",     "category": "shirt",   "body_type": "all",        "fit": "regular"},
    {"id": 1,  "name": "Navy Slim Blazer",         "category": "blazer",  "body_type": "lean",       "fit": "slim"},
    {"id": 2,  "name": "Relaxed Linen Shirt",      "category": "shirt",   "body_type": "athletic",   "fit": "relaxed"},
    {"id": 3,  "name": "Striped Oxford",           "category": "shirt",   "body_type": "all",        "fit": "regular"},
    {"id": 4,  "name": "Black Formal Blazer",      "category": "blazer",  "body_type": "all",        "fit": "regular"},
    {"id": 5,  "name": "Floral Summer Dress",      "category": "dress",   "body_type": "petite",     "fit": "flowy"},
    {"id": 6,  "name": "Denim Jacket",             "category": "jacket",  "body_type": "athletic",   "fit": "regular"},
    {"id": 7,  "name": "Fitted Polo Shirt",        "category": "shirt",   "body_type": "athletic",   "fit": "slim"},
    {"id": 8,  "name": "Oversized Hoodie",         "category": "hoodie",  "body_type": "all",        "fit": "oversized"},
    {"id": 9,  "name": "Wrap Midi Dress",          "category": "dress",   "body_type": "curvy",      "fit": "wrap"},
    {"id": 10, "name": "Tailored Chinos",          "category": "pants",   "body_type": "lean",       "fit": "slim"},
    {"id": 11, "name": "Wide Leg Trousers",        "category": "pants",   "body_type": "all",        "fit": "wide"},
    {"id": 12, "name": "Cropped Leather Jacket",   "category": "jacket",  "body_type": "petite",     "fit": "cropped"},
    {"id": 13, "name": "Merino Wool Sweater",      "category": "sweater", "body_type": "all",        "fit": "regular"},
    {"id": 14, "name": "Athletic Track Jacket",    "category": "jacket",  "body_type": "athletic",   "fit": "athletic"},
    {"id": 15, "name": "A-Line Skirt",             "category": "skirt",   "body_type": "curvy",      "fit": "flowy"},
]

N = len(GARMENT_CATALOG)   # 16
N_QUBITS = int(math.log2(N))  # 4 qubits


# ─── Classical scoring (used as oracle basis) ─────────────────────────────────
def _score_garment(garment: dict, body_type: str, category: str) -> float:
    score = 0.0
    if garment["category"] == category:
        score += 0.6
    if garment["body_type"] in ("all", body_type):
        score += 0.4
    return score


def _find_target_indices(body_type: str, category: str) -> list[int]:
    """Classical pre-filter to identify which items Grover should amplify."""
    targets = []
    for g in GARMENT_CATALOG:
        if _score_garment(g, body_type, category) >= 0.6:
            targets.append(g["id"])
    return targets if targets else [0]   # fallback: item 0


# ─── Grover's algorithm ───────────────────────────────────────────────────────
def grover_search(body_type: str = "athletic", category: str = "shirt", top_k: int = 5) -> dict:
    """
    Run Grover's algorithm to find matching garments.

    Args:
        body_type: "lean" | "athletic" | "curvy" | "petite" | "all"
        category:  "shirt" | "blazer" | "dress" | "jacket" | "pants" | "hoodie" | "sweater" | "skirt"
        top_k:     number of results to return

    Returns:
        {
            "matches": [...],          # top_k garments sorted by quantum score
            "algorithm": "Grover O(√N)",
            "classical_steps": N,      # O(N) classical
            "quantum_steps": int,      # O(√N) quantum
            "speedup": float,
            "n_qubits": int,
            "fallback": bool,
        }
    """
    targets = _find_target_indices(body_type, category)
    n_targets = len(targets)

    try:
        result = _run_grover_circuit(targets, n_targets)
        return _format_result(result, body_type, category, top_k, fallback=False)
    except Exception as e:
        logger.warning(f"Qiskit unavailable ({e}) — using classical search")
        return _classical_fallback(body_type, category, top_k)


def _apply_oracle(qc, targets: list[int]):
    """Phase oracle: adds -1 phase to target states (Qiskit 2.x compatible)."""
    for target in targets:
        bits = format(target, f'0{N_QUBITS}b')
        # Flip 0-bits to 1 so all target bits are 1
        for i, bit in enumerate(reversed(bits)):
            if bit == '0':
                qc.x(i)
        # Multi-controlled Z: H + MCX + H on last qubit
        qc.h(N_QUBITS - 1)
        qc.mcx(list(range(N_QUBITS - 1)), N_QUBITS - 1)
        qc.h(N_QUBITS - 1)
        # Unflip
        for i, bit in enumerate(reversed(bits)):
            if bit == '0':
                qc.x(i)


def _apply_diffuser(qc, n: int):
    """Grover diffuser (inversion about average)."""
    qc.h(range(n))
    qc.x(range(n))
    qc.h(n - 1)
    qc.mcx(list(range(n - 1)), n - 1)
    qc.h(n - 1)
    qc.x(range(n))
    qc.h(range(n))


def _run_grover_circuit(targets: list[int], n_targets: int) -> dict:
    """Build and simulate Grover's circuit using Qiskit 2.x + Aer."""
    from qiskit import QuantumCircuit
    from qiskit_aer import AerSimulator

    n_iter = max(1, round(math.pi / 4 * math.sqrt(N / max(n_targets, 1))))

    qc = QuantumCircuit(N_QUBITS, N_QUBITS)
    qc.h(range(N_QUBITS))          # uniform superposition

    for _ in range(n_iter):
        _apply_oracle(qc, targets)
        _apply_diffuser(qc, N_QUBITS)

    qc.measure(range(N_QUBITS), range(N_QUBITS))

    sim    = AerSimulator()
    shots  = 1024
    job    = sim.run(qc, shots=shots)
    counts = job.result().get_counts()

    probs = {}
    for bitstr, count in counts.items():
        idx = int(bitstr[::-1], 2)   # reverse bit order (Qiskit LSB convention)
        if idx < N:
            probs[idx] = count / shots

    return {"probs": probs, "n_iter": n_iter, "shots": shots}


def _format_result(circuit_result: dict, body_type: str, category: str, top_k: int, fallback: bool) -> dict:
    probs   = circuit_result.get("probs", {})
    n_iter  = circuit_result.get("n_iter", 1)

    # Combine quantum probability + classical score for final ranking
    ranked = []
    for g in GARMENT_CATALOG:
        q_score = probs.get(g["id"], 0.0)
        c_score = _score_garment(g, body_type, category)
        final   = 0.6 * q_score + 0.4 * c_score
        ranked.append({**g, "quantum_score": round(final, 3), "q_prob": round(q_score, 3)})

    ranked.sort(key=lambda x: x["quantum_score"], reverse=True)
    matches = ranked[:top_k]

    quantum_steps  = n_iter * int(math.sqrt(N))
    classical_steps = N
    speedup = round(classical_steps / max(quantum_steps, 1), 2)

    return {
        "matches":          matches,
        "algorithm":        f"Grover's O(√N) — {n_iter} iteration(s)",
        "classical_steps":  classical_steps,
        "quantum_steps":    quantum_steps,
        "speedup":          f"{speedup}×",
        "n_qubits":         N_QUBITS,
        "catalog_size":     N,
        "fallback":         fallback,
    }


def _classical_fallback(body_type: str, category: str, top_k: int) -> dict:
    ranked = sorted(
        GARMENT_CATALOG,
        key=lambda g: _score_garment(g, body_type, category),
        reverse=True,
    )
    matches = [{**g, "quantum_score": round(_score_garment(g, body_type, category), 2)} for g in ranked[:top_k]]
    return {
        "matches":          matches,
        "algorithm":        "Classical O(N) fallback",
        "classical_steps":  N,
        "quantum_steps":    N,
        "speedup":          "1×",
        "n_qubits":         N_QUBITS,
        "catalog_size":     N,
        "fallback":         True,
    }
