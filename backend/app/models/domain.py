from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.neighbors import KNeighborsClassifier


@dataclass
class Artifacts:
    cases: pd.DataFrame
    embeddings: np.ndarray
    knn: KNeighborsClassifier
    pca: PCA
    model_name: str
    best_k: int
    trained_at: str
    schema_version: str
    required_columns: list[str]
