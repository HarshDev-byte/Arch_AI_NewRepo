"""Random seed system for reproducible design generation."""
import hashlib, time

def generate_seed(project_id: str) -> int:
    raw = f"{project_id}-{time.time()}"
    return int(hashlib.sha256(raw.encode()).hexdigest(), 16) % (2**32)
