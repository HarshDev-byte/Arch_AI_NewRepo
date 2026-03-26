"""Style mixing engine – blends multiple style influences."""

def fuse_styles(styles: list[str], weights: list[float]) -> dict:
    assert len(styles) == len(weights), "Styles and weights must match"
    return {"fused_style": styles[weights.index(max(weights))], "influences": dict(zip(styles, weights))}
