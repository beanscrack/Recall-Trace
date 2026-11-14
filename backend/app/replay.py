"""Black Box: counterfactual replay of a recorded decision. See brief section 8.

Reads only the stored decisions document; never re-queries memories, never touches the sim.
"""
RUNS_PER_VARIANT = 3


def run_replay(decision_id: str) -> dict:
    # TODO: baseline N runs -> stability (stop if < 2/3); leave-one-out ablations -> flip_rate;
    # culprit = max flip_rate if >= 2/3. Run the decide() calls concurrently (ThreadPoolExecutor).
    # Store in db.replays() and return.
    raise NotImplementedError
