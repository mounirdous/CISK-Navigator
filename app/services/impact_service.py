"""
Impact Compounding Service

Computes "true importance" for entities in the CISK hierarchy.
Five calculation methods available:

1. Simple Product — multiply weights through chain, normalize by max possible
2. Geometric Mean — sqrt(parent x child) at each step, stays in natural scale
3. Toyota QFD — fuzzy lookup table (strongest contrast)
4. Toyota Weighted (downstream) — exponential reinforcement on child ratings
5. Toyota Weighted (full) — exponential reinforcement on all ratings
"""

import math


# Toyota QFD fuzzy compounding table (Tableau 2)
# Maps (parent_level, child_level) -> result_level
# 0=not set, 1=*, 2=**, 3=***
_QFD_TABLE = {
    (3, 3): 3, (3, 2): 3, (3, 1): 2, (3, 0): 0,
    (2, 3): 3, (2, 2): 2, (2, 1): 1, (2, 0): 0,
    (1, 3): 2, (1, 2): 1, (1, 1): 0, (1, 0): 0,
    (0, 3): 0, (0, 2): 0, (0, 1): 0, (0, 0): 0,
}

# Toyota exponential reinforcement scale
# Higher levels get disproportionately more weight
_REINFORCE = {1: 1, 2: 2, 3: 4}


def _level_to_weight(level, weights):
    """Convert impact level (1/2/3) to numeric weight."""
    if not level:
        return 0
    return weights.get(level, 0)


def _weight_to_level(weight, weights):
    """Convert numeric weight back to level (1/2/3) using nearest match."""
    if weight <= 0:
        return None
    # Build sorted (weight, level) pairs
    items = sorted([(w, lvl) for lvl, w in weights.items()])
    if not items:
        return None
    # Find nearest
    best_lvl = items[0][1]
    best_dist = abs(weight - items[0][0])
    for w, lvl in items[1:]:
        dist = abs(weight - w)
        if dist < best_dist:
            best_dist = dist
            best_lvl = lvl
    return best_lvl


def compute_simple_product(chain_levels, weights):
    """
    Simple Product method.
    Score = product of all weights in chain.
    Normalized against max_weight^depth -> mapped to L1/L2/L3.
    """
    if not chain_levels or not all(chain_levels):
        return None
    max_w = max(weights.values()) if weights else 1
    score = 1
    for lvl in chain_levels:
        w = weights.get(lvl, 0)
        if w <= 0:
            return None
        score *= w
    depth = len(chain_levels)
    max_possible = max_w ** depth
    if max_possible <= 0:
        return None
    pct = score / max_possible
    if pct <= 0.33:
        return 1
    elif pct <= 0.66:
        return 2
    else:
        return 3


def compute_geometric_mean(chain_levels, weights):
    """
    Geometric Mean method (simplified CISK compounding).
    At each step: compounded = sqrt(parent_weight x child_weight)
    Result naturally stays in the weight scale.
    Final value mapped back to nearest level.
    """
    if not chain_levels or not all(chain_levels):
        return None
    current_w = weights.get(chain_levels[0], 0)
    if current_w <= 0:
        return None
    for lvl in chain_levels[1:]:
        child_w = weights.get(lvl, 0)
        if child_w <= 0:
            return None
        current_w = math.sqrt(current_w * child_w)
    return _weight_to_level(current_w, weights)


def compute_toyota_qfd(chain_levels, custom_matrix=None):
    """
    Toyota QFD method (fuzzy lookup table).
    Strongest contrast — a weak link in the chain pulls the result down hard.
    No numeric weights needed — uses the lookup table directly.
    Accepts optional custom_matrix dict with keys like '3_2' -> result level.
    """
    if not chain_levels or not all(chain_levels):
        return None
    table = _QFD_TABLE
    if custom_matrix:
        table = {}
        for key, val in custom_matrix.items():
            parts = key.split("_")
            if len(parts) == 2:
                table[(int(parts[0]), int(parts[1]))] = int(val)
    current = chain_levels[0]
    for child_lvl in chain_levels[1:]:
        current = table.get((current, child_lvl), 0)
        if current == 0:
            return None
    return current if current > 0 else None


def _get_reinforce(custom_reinforce=None):
    """Get reinforcement weights — custom or default."""
    if custom_reinforce:
        return {int(k): v for k, v in custom_reinforce.items()}
    return dict(_REINFORCE)


def compute_toyota_weighted_ds(chain_levels, weights, custom_reinforce=None):
    """
    Toyota Weighted (downstream only).
    Uses exponential reinforcement on the child (deepest entity) rating.
    Default: Level 1 -> 1, Level 2 -> 2, Level 3 -> 4 (configurable).
    Parent weights stay as configured.
    Product is normalized against max possible -> mapped to L1/L2/L3.
    """
    if not chain_levels or not all(chain_levels):
        return None
    reinforce = _get_reinforce(custom_reinforce)
    max_r = max(reinforce.values()) if reinforce else 4
    score = 1
    max_score = 1
    for i, lvl in enumerate(chain_levels):
        w = weights.get(lvl, 0)
        if w <= 0:
            return None
        max_w = max(weights.values())
        if i == len(chain_levels) - 1:
            # Last entity: apply exponential reinforcement
            score *= reinforce.get(lvl, 1)
            max_score *= max_r
        else:
            # Parent: use configured weight as-is
            score *= w
            max_score *= max_w
    if max_score <= 0:
        return None
    pct = score / max_score
    if pct <= 0.33:
        return 1
    elif pct <= 0.66:
        return 2
    else:
        return 3


def compute_toyota_weighted_full(chain_levels, weights, custom_reinforce=None):
    """
    Toyota Weighted (upstream + downstream).
    Uses exponential reinforcement on ALL levels in the chain.
    Default: Level 1 -> 1, Level 2 -> 2, Level 3 -> 4 (configurable).
    Both parent and child ratings get amplified.
    Product is normalized against max possible -> mapped to L1/L2/L3.
    """
    if not chain_levels or not all(chain_levels):
        return None
    reinforce = _get_reinforce(custom_reinforce)
    max_r = max(reinforce.values()) if reinforce else 4
    score = 1
    for lvl in chain_levels:
        if lvl <= 0:
            return None
        score *= reinforce.get(lvl, 1)
    depth = len(chain_levels)
    max_score = max_r ** depth
    if max_score <= 0:
        return None
    pct = score / max_score
    if pct <= 0.33:
        return 1
    elif pct <= 0.66:
        return 2
    else:
        return 3


# Method registry
METHODS = {
    "simple_product": {
        "name": "Simple Product",
        "description": "Multiply weights through chain, normalize by maximum possible",
        "compute": compute_simple_product,
        "needs_weights": True,
    },
    "geometric_mean": {
        "name": "Geometric Mean",
        "description": "sqrt(parent x child) at each step — balanced compounding",
        "compute": compute_geometric_mean,
        "needs_weights": True,
    },
    "toyota_qfd": {
        "name": "Toyota QFD",
        "description": "Fuzzy lookup table — strongest contrast, recommended for decision-making",
        "compute": compute_toyota_qfd,
        "needs_weights": False,
    },
    "toyota_weighted_ds": {
        "name": "Toyota Weighted (downstream)",
        "description": "Exponential reinforcement on child ratings — high ratings amplified",
        "compute": compute_toyota_weighted_ds,
        "needs_weights": True,
    },
    "toyota_weighted_full": {
        "name": "Toyota Weighted (full)",
        "description": "Exponential reinforcement on all ratings — maximum amplification",
        "compute": compute_toyota_weighted_full,
        "needs_weights": True,
    },
}


def compute_true_importance(chain_levels, method, weights=None, custom_matrix=None, custom_reinforce=None):
    """
    Compute the true importance level for an entity given its chain of impact levels.

    Args:
        chain_levels: list of impact levels from root to entity, e.g. [2, 3, 1]
        method: 'simple_product', 'geometric_mean', 'toyota_qfd', 'toyota_weighted_ds', or 'toyota_weighted_full'
        weights: dict {1: w1, 2: w2, 3: w3} — required for weight-based methods
        custom_matrix: dict {'3_2': 3, ...} — optional custom QFD matrix
        custom_reinforce: dict {'1': 1, '2': 2, '3': 4} — optional custom reinforcement weights

    Returns:
        int (1, 2, or 3) or None if chain is incomplete
    """
    if method == "toyota_qfd":
        return compute_toyota_qfd(chain_levels, custom_matrix)
    elif method in ("toyota_weighted_ds", "toyota_weighted_full"):
        info = METHODS[method]
        return info["compute"](chain_levels, weights or {}, custom_reinforce)
    else:
        info = METHODS.get(method, METHODS["simple_product"])
        if info["needs_weights"]:
            return info["compute"](chain_levels, weights or {})
        return info["compute"](chain_levels)
