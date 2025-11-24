def times_intersect(start1: float, end1: float, start2: float, end2: float) -> bool:
    """Returns True if the two time intervals intersect."""
    return max(start1, start2) <= min(end1, end2)
