import os
import pickle
import numpy as np
from google import genai
from dotenv import load_dotenv

# =========================
# Load .env
# =========================
load_dotenv()
# =========================
# Load trained model once
# =========================
MODEL_PATH = "trained_model.pkl"

with open(MODEL_PATH, "rb") as f:
    _data = pickle.load(f)

_model = _data["model"]
_EMBEDDING_MODEL ="models/gemini-embedding-001"
# =========================
# Gemini client
# =========================
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def _get_embedding(text: str) -> list[float]:
    result = _client.models.embed_content(
        model=_EMBEDDING_MODEL,
        contents=text
    )
    return result.embeddings[0].values


# =========================
# PUBLIC FUNCTION
# =========================
def classify_text(text: str, min_confidence: float = 0.5) -> dict:
    """
    Classify text using trained sklearn model.

    Returns:
        {
          "label": str | None,
          "confidence": float,
          "probabilities": dict
        }
    """
    X = np.array([_get_embedding(text)])

    probs = _model.predict_proba(X)[0]
    label = _model.predict(X)[0]
    confidence = float(max(probs))

    result = {
        "label": label if confidence >= min_confidence else None,
        "confidence": confidence,
        "probabilities": dict(zip(_model.classes_, probs))
    }

    return result

