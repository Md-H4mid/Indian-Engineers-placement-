from typing import Any, Dict, List, Tuple


def build_parameterized_filter(
    tiers: List[str],
    branches: List[str],
    cgpa_range: Tuple[float, float],
    min_dsa: int,
    placed_only: bool = True,
) -> Tuple[str, Dict[str, Any]]:
    """Construct a sanitized SQL WHERE clause and named parameters."""
    conditions: List[str] = []
    params: Dict[str, Any] = {}

    if tiers:
        tier_keys = [f"tier_{i}" for i in range(len(tiers))]
        placeholders = ", ".join(f":{key}" for key in tier_keys)
        conditions.append(f"college_tier IN ({placeholders})")
        for key, val in zip(tier_keys, tiers):
            params[key] = val

    if branches:
        branch_keys = [f"branch_{i}" for i in range(len(branches))]
        placeholders = ", ".join(f":{key}" for key in branch_keys)
        conditions.append(f"branch IN ({placeholders})")
        for key, val in zip(branch_keys, branches):
            params[key] = val


    conditions.append("CGPA BETWEEN :cgpa_min AND :cgpa_max")
    params["cgpa_min"] = float(cgpa_range[0])
    params["cgpa_max"] = float(cgpa_range[1])

    conditions.append("DSA_Problems_Solved >= :min_dsa")
    params["min_dsa"] = int(min_dsa)

    if placed_only:
        conditions.append("placement_status = Status")
        params["Status"] = "Placed"

    Where_clause =f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return Where_clause, params