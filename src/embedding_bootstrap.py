# src/embedding_bootstrap.py
import os
import sys
from pathlib import Path
from typing import Set, Dict
import numpy as np

from src.scoring import load_skill_vectors, save_skill_vectors, _get_model, _normalize_skill

def bootstrap_embeddings(
    skills: Set[str],
    cache_path: Path,
    allow_download: bool = True,
    is_hf_spaces: bool = False
) -> Dict[str, np.ndarray]:
    """
    Bootstrap the skill embedding cache. Handles offline modes, local models, and lazy loading.
    For HF Spaces, restricts encoding to JD and sample skills (~200) to keep memory footprint low and prevent timeouts.
    """
    cache_path = Path(cache_path)
    
    # 1. Load existing cache
    vectors = load_skill_vectors(cache_path)
    
    # 2. Normalize and check which skills are missing
    normalized_skills = {_normalize_skill(s) for s in skills if s.strip()}
    missing = normalized_skills - set(vectors.keys())
    
    if not missing:
        return vectors
        
    # For HuggingFace Spaces: avoid loading huge counts of missing skills at start
    if is_hf_spaces:
        # Restrict missing skills to JD requirements and some sample skills, capping at 200
        missing = set(sorted(list(missing))[:200])
        
    if not missing:
        return vectors

    # 3. Check for local model vs download permission
    local_model_path = Path("data/embeddings/model")
    has_local_model = local_model_path.exists() and (local_model_path / "config.json").exists()
    
    # Check if network is blocked
    is_offline = os.environ.get("HF_HUB_OFFLINE") == "1"
    
    if is_offline and not has_local_model:
        # If we cannot download and don't have local model, we fail with RuntimeError
        raise RuntimeError(
            f"Missing {len(missing)} skill vectors in {cache_path} (offline mode). "
            f"Please run: python scripts/precompute_embeddings.py first."
        )

    if not allow_download and not has_local_model:
        raise RuntimeError(
            f"Network download not allowed, and local model snapshot not found at {local_model_path}. "
            f"Please precompute embeddings offline."
        )
        
    # 4. Load model and encode missing
    try:
        model = _get_model("all-MiniLM-L6-v2")
        encoded = model.encode(
            sorted(missing),
            normalize_embeddings=True,
            show_progress_bar=False
        )
        for name, vec in zip(sorted(missing), encoded):
            vectors[name] = np.asarray(vec, dtype=np.float32)
            
        save_skill_vectors(cache_path, vectors)
    except Exception as e:
        raise RuntimeError(f"Error bootstrapping skill embeddings: {e}")
        
    return vectors
