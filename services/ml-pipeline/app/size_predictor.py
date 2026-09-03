"""
Week 3 — TensorFlow Size Predictor
Dense neural network: body measurements → clothing size + fit score.

Training data is synthetic but realistically distributed.
Trains in < 60 seconds on M2 Max (Metal GPU).
Auto-trains on first call if no saved model found.
"""

import io
import logging
import os
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

_MODEL_PATH = Path(__file__).parent.parent / "checkpoints" / "size_predictor.keras"

# Size labels
SIZES     = ["XS", "S", "M", "L", "XL", "XXL"]
SIZE_IDX  = {s: i for i, s in enumerate(SIZES)}

# Lazy-loaded model
_model = None


# ─── Synthetic training data ──────────────────────────────────────────────────
def _generate_training_data(n: int = 5000):
    """
    Generate realistic synthetic body measurement data.
    Based on standard garment size charts + Gaussian noise.
    """
    rng = np.random.default_rng(42)

    # Size distributions (chest_cm mean, std)
    size_params = {
        "XS":  (78,  3),
        "S":   (86,  3),
        "M":   (92,  3),
        "L":   (100, 3),
        "XL":  (108, 3),
        "XXL": (118, 4),
    }

    X_list, y_list = [], []

    per_size = n // len(SIZES)
    for size, (chest_mean, chest_std) in size_params.items():
        chest     = rng.normal(chest_mean, chest_std, per_size)
        shoulder  = chest * rng.uniform(0.44, 0.48, per_size)
        waist     = chest * rng.uniform(0.75, 0.88, per_size)
        hip       = chest * rng.uniform(0.95, 1.10, per_size)
        height    = rng.normal(165, 8, per_size)

        features = np.column_stack([shoulder, chest, waist, hip, height])
        labels   = np.full(per_size, SIZE_IDX[size])

        X_list.append(features)
        y_list.append(labels)

    X = np.vstack(X_list).astype(np.float32)
    y = np.concatenate(y_list).astype(np.int32)

    # Shuffle
    idx = rng.permutation(len(X))
    return X[idx], y[idx]


# ─── Model definition ─────────────────────────────────────────────────────────
def _build_model():
    import tensorflow as tf

    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(5,)),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.Dense(64, activation="relu"),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(64, activation="relu"),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dense(len(SIZES), activation="softmax"),
    ])

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


# ─── Train ────────────────────────────────────────────────────────────────────
def train_and_save():
    """Train the size predictor and save to checkpoints/."""
    logger.info("🏋️  Training TF size predictor on synthetic data…")

    X, y = _generate_training_data(n=6000)
    split = int(len(X) * 0.85)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    model = _build_model()

    import tensorflow as tf
    cb = [
        tf.keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(patience=3, factor=0.5),
    ]

    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=60,
        batch_size=64,
        callbacks=cb,
        verbose=0,
    )

    val_acc = max(history.history["val_accuracy"])
    logger.info(f"✅ Training complete — val_accuracy: {val_acc:.3f}")

    _MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(_MODEL_PATH))
    logger.info(f"💾 Model saved → {_MODEL_PATH}")
    return model


# ─── Load ─────────────────────────────────────────────────────────────────────
def _load_model():
    global _model
    if _model is not None:
        return _model

    try:
        import tensorflow as tf

        if _MODEL_PATH.exists():
            logger.info("📂 Loading saved size predictor…")
            _model = tf.keras.models.load_model(str(_MODEL_PATH))
        else:
            logger.info("🆕 No saved model found — training now…")
            _model = train_and_save()

        logger.info("✅ Size predictor ready")
    except Exception as e:
        logger.error(f"❌ TF size predictor failed: {e}")
        _model = None

    return _model


# ─── Public API ───────────────────────────────────────────────────────────────
def predict_size(
    shoulder_cm: float,
    chest_cm: float,
    waist_cm: float,
    hip_cm: float,
    height_cm: float = 165.0,
) -> dict:
    """
    Predict clothing size from body measurements.

    Returns:
        {
            "predicted_size": "M",
            "fit_score": 87,          # 0-100, how well this size fits
            "probabilities": {...},    # per-size confidence
            "fallback": bool,
        }
    """
    model = _load_model()

    features = np.array([[shoulder_cm, chest_cm, waist_cm, hip_cm, height_cm]], dtype=np.float32)

    if model is None:
        return _rule_based_fallback(chest_cm)

    try:
        probs = model.predict(features, verbose=0)[0]
        size_idx  = int(np.argmax(probs))
        predicted = SIZES[size_idx]
        fit_score = int(probs[size_idx] * 100)

        return {
            "predicted_size": predicted,
            "fit_score":       fit_score,
            "probabilities":   {s: round(float(p) * 100, 1) for s, p in zip(SIZES, probs)},
            "fallback":        False,
        }
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        return _rule_based_fallback(chest_cm)


def _rule_based_fallback(chest_cm: float) -> dict:
    chart = [("XS", 82), ("S", 88), ("M", 96), ("L", 104), ("XL", 116), ("XXL", 999)]
    size = "XXL"
    for s, limit in chart:
        if chest_cm < limit:
            size = s
            break
    return {
        "predicted_size": size,
        "fit_score":       75,
        "probabilities":   {s: 0.0 for s in SIZES},
        "fallback":        True,
    }
