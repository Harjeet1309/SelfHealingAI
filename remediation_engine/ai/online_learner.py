"""
Online Learner — Continuous Fine-Tuning on Production Data
===========================================================
Fixes the "frozen weights" limitation.

How it works:
    1. The InferenceEngine feeds clean production sequences into this buffer
       (only sequences where corroboration FAILS — meaning no fault is detected).
    2. When the buffer reaches FINE_TUNE_TRIGGER samples, we run one fine-tuning
       epoch on those samples using the live model (in-place weight update).
    3. After fine-tuning, the updated weights are saved back to the model file
       so the next Docker restart loads the improved model.
    4. The buffer is then cleared and the cycle repeats.

This lets the model continuously adapt to real production traffic patterns
without requiring a full retrain from scratch.
"""

import os
import json
import time
import torch
import torch.nn as nn
import numpy as np
import logging

from collections import deque
from torch.utils.data import DataLoader, TensorDataset

logger = logging.getLogger(__name__)


class OnlineLearner:
    """
    Collects clean production sequences and periodically fine-tunes the
    LSTM model in-place using them.
    """

    def __init__(
        self,
        model: nn.Module,
        model_path: str,
        threshold_path: str,
        device: torch.device,
        fine_tune_trigger: int = 500,      # sequences before fine-tuning
        fine_tune_lr: float = 1e-5,        # very small LR to avoid overwriting old knowledge
        fine_tune_epochs: int = 1,         # light update, not full retrain
        fine_tune_batch: int = 32,
        max_buffer: int = 2000,            # rolling window — discard oldest
        min_samples_for_threshold: int = 100,
        threshold_percentile: float = 99.0,
        save_raw_data: bool = True,
        raw_data_path: str = "/app/logs/live_training_buffer.npy",
    ):
        self.model              = model
        self.model_path         = model_path
        self.threshold_path     = threshold_path
        self.device             = device
        self.fine_tune_trigger  = fine_tune_trigger
        self.fine_tune_lr       = fine_tune_lr
        self.fine_tune_epochs   = fine_tune_epochs
        self.fine_tune_batch    = fine_tune_batch
        self.max_buffer         = max_buffer
        self.min_samples        = min_samples_for_threshold
        self.threshold_pct      = threshold_percentile
        self.save_raw_data      = save_raw_data
        self.raw_data_path      = raw_data_path

        # Rolling buffer of clean (X, y) sequence pairs
        # Each entry: (seq_array shape (seq_len, features), next_step shape (features,))
        self._X_buffer: deque = deque(maxlen=max_buffer)
        self._y_buffer: deque = deque(maxlen=max_buffer)

        self._fine_tune_count   = 0    # how many fine-tune passes completed
        self._last_fine_tune_ts = 0.0

        # MSE scores from clean samples — for live threshold update
        self._mse_scores: deque = deque(maxlen=2000)

    # ──────────────────────────────────────────────────────────────────
    # PUBLIC API (called by InferenceEngine)
    # ──────────────────────────────────────────────────────────────────

    def add_clean_sample(self, X: np.ndarray, y: np.ndarray, mse_score: float):
        """
        Add a clean (non-anomalous) sequence to the buffer.

        Args:
            X: shape (seq_len, num_features) — the input sequence
            y: shape (num_features,)         — the actual next timestep
            mse_score: the LSTM's MSE for this sequence (used for threshold update)
        """
        self._X_buffer.append(X.copy())
        self._y_buffer.append(y.copy())
        self._mse_scores.append(mse_score)

        if self.save_raw_data:
            self._maybe_persist_raw_data()

        # Trigger fine-tuning when buffer is full enough
        if len(self._X_buffer) >= self.fine_tune_trigger:
            self._fine_tune()

    def get_live_threshold(self) -> float | None:
        """
        Compute and return a threshold from live production MSE scores.
        Returns None if not enough samples yet.
        """
        if len(self._mse_scores) < self.min_samples:
            return None
        return float(np.percentile(list(self._mse_scores), self.threshold_pct))

    def persist_threshold(self, dynamic_threshold: float, static_threshold: float):
        """
        Write the best available threshold back to threshold.json.
        Called periodically by InferenceEngine to keep threshold calibrated
        to real production data rather than just synthetic training data.
        """
        live = self.get_live_threshold()
        best = live if live is not None else dynamic_threshold

        try:
            existing = {}
            if os.path.exists(self.threshold_path):
                with open(self.threshold_path) as f:
                    existing = json.load(f)

            existing.update({
                "threshold":         best,
                "live_threshold":    live,
                "dynamic_threshold": dynamic_threshold,
                "static_threshold":  static_threshold,
                "live_samples":      len(self._mse_scores),
                "fine_tune_count":   self._fine_tune_count,
                "last_updated":      time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })

            with open(self.threshold_path, "w") as f:
                json.dump(existing, f, indent=2)

            logger.info(
                f"[OnlineLearner] Threshold persisted → {best:.6f} "
                f"(live={live}, dynamic={dynamic_threshold:.6f}, "
                f"static={static_threshold:.6f})"
            )
        except Exception as e:
            logger.warning(f"[OnlineLearner] Failed to persist threshold: {e}")

    @property
    def buffer_size(self) -> int:
        return len(self._X_buffer)

    @property
    def fine_tune_count(self) -> int:
        return self._fine_tune_count

    # ──────────────────────────────────────────────────────────────────
    # PRIVATE
    # ──────────────────────────────────────────────────────────────────

    def _fine_tune(self):
        """Run one fine-tuning epoch on all buffered clean samples."""
        if len(self._X_buffer) < 32:
            return  # Need at least one batch

        logger.info(
            f"[OnlineLearner] Fine-tuning on {len(self._X_buffer)} clean samples "
            f"(pass #{self._fine_tune_count + 1}) ..."
        )

        X_arr = np.stack(list(self._X_buffer), axis=0)   # (n, seq_len, features)
        y_arr = np.stack(list(self._y_buffer), axis=0)   # (n, features)

        X_t = torch.tensor(X_arr, dtype=torch.float32)
        y_t = torch.tensor(y_arr, dtype=torch.float32)

        dataset = TensorDataset(X_t, y_t)
        loader  = DataLoader(dataset, batch_size=self.fine_tune_batch, shuffle=True)

        # Very small LR — we're refining, not rewriting the model
        optimizer = torch.optim.Adam(
            self.model.parameters(),
            lr=self.fine_tune_lr,
            weight_decay=1e-6,
        )
        criterion = nn.MSELoss()

        self.model.train()
        total_loss = 0.0
        batches = 0

        for _ in range(self.fine_tune_epochs):
            for batch_X, batch_y in loader:
                batch_X = batch_X.to(self.device)
                batch_y = batch_y.to(self.device)
                optimizer.zero_grad()
                pred = self.model(batch_X)
                loss = criterion(pred, batch_y)
                loss.backward()
                nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()
                total_loss += loss.item()
                batches += 1

        self.model.eval()
        avg_loss = total_loss / max(batches, 1)

        # Save updated weights
        try:
            torch.save(self.model.state_dict(), self.model_path)
            logger.info(
                f"[OnlineLearner] Fine-tune complete. "
                f"avg_loss={avg_loss:.6f}. Saved → {self.model_path}"
            )
        except Exception as e:
            logger.warning(f"[OnlineLearner] Could not save updated model: {e}")

        self._fine_tune_count  += 1
        self._last_fine_tune_ts = time.time()

        # Clear the buffer after fine-tuning
        self._X_buffer.clear()
        self._y_buffer.clear()

    def _maybe_persist_raw_data(self):
        """Save raw training X/y arrays every 100 additions for future full retraining."""
        if len(self._X_buffer) % 100 != 0 or len(self._X_buffer) == 0:
            return
        try:
            X_arr = np.stack(list(self._X_buffer), axis=0)
            y_arr = np.stack(list(self._y_buffer), axis=0)
            os.makedirs(os.path.dirname(self.raw_data_path), exist_ok=True)
            np.save(self.raw_data_path.replace(".npy", "_X.npy"), X_arr)
            np.save(self.raw_data_path.replace(".npy", "_y.npy"), y_arr)
        except Exception:
            pass  # Non-critical — don't interrupt inference
