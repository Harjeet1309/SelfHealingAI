"""
LSTM + Multi-Head Self-Attention Forecasting Model — V3
=========================================================
Architecture upgrade over plain LSTM (V1/V2):

  LSTM captures temporal sequence patterns (what changed over time).
  Self-Attention then re-weights those hidden states so the model
  learns which of the 30 timesteps are most anomalous or informative.
  This combination is state-of-the-art for time-series anomaly detection.

Architecture:
    Input  (batch, seq=30, features=3)
      │
      ▼
    LSTM  (hidden=128, layers=2, dropout=0.25)
      │    → outputs all 30 hidden states, not just last
      ▼
    Multi-Head Self-Attention  (heads=4, dropout=0.1)
      │    → lets model focus on most anomalous timesteps
      ▼
    Attention-weighted mean pooling  (across time dimension)
      │
      ▼
    LayerNorm + Dropout(0.2)
      │
      ▼
    FC head: Linear(128 → 64) → GELU → Linear(64 → input_size)
      │
      ▼
    Output (batch, input_size)  → predicted next-step metrics
"""

import torch
import torch.nn as nn
import math


class LSTMForecastModel(nn.Module):
    def __init__(
        self,
        input_size: int,
        hidden_size: int = 128,
        num_layers: int = 2,
        dropout: float = 0.25,
        num_attention_heads: int = 4,
        attention_dropout: float = 0.1,
        bidirectional: bool = False,
    ):
        super().__init__()

        self.hidden_size   = hidden_size
        self.bidirectional = bidirectional
        self.num_directions = 2 if bidirectional else 1
        lstm_out_dim = hidden_size * self.num_directions

        # ── LSTM Encoder ──────────────────────────────────────────
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
            bidirectional=bidirectional,
        )

        # ── Self-Attention over all LSTM hidden states ────────────
        # MultiheadAttention expects (seq, batch, dim) — we permute in forward()
        self.attention = nn.MultiheadAttention(
            embed_dim=lstm_out_dim,
            num_heads=num_attention_heads,
            dropout=attention_dropout,
            batch_first=True,          # use (batch, seq, dim) convention
        )
        self.attn_norm = nn.LayerNorm(lstm_out_dim)

        # ── Output head ───────────────────────────────────────────
        self.post_norm = nn.LayerNorm(lstm_out_dim)
        self.dropout   = nn.Dropout(p=0.2)

        self.fc1 = nn.Linear(lstm_out_dim, 64)
        self.act  = nn.GELU()                    # GELU outperforms ReLU on sequences
        self.fc2  = nn.Linear(64, input_size)

        self._init_weights()

    def _init_weights(self):
        """Xavier uniform init for linear layers; orthogonal for LSTM."""
        for name, param in self.lstm.named_parameters():
            if "weight_ih" in name:
                nn.init.xavier_uniform_(param)
            elif "weight_hh" in name:
                nn.init.orthogonal_(param)
            elif "bias" in name:
                nn.init.zeros_(param)
        for layer in [self.fc1, self.fc2]:
            nn.init.xavier_uniform_(layer.weight)
            nn.init.zeros_(layer.bias)

    def forward(self, x):
        """
        Args:
            x : Tensor (batch, seq_len, input_size)
        Returns:
            pred : Tensor (batch, input_size)  — predicted next timestep
        """
        # 1. LSTM — get all hidden states (not just last)
        lstm_out, _ = self.lstm(x)          # (batch, seq_len, lstm_out_dim)

        # 2. Self-attention — query = key = value = lstm output (self-attention)
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)  # (batch, seq, dim)
        attn_out = self.attn_norm(lstm_out + attn_out)              # residual connection

        # 3. Mean pool across time dimension (richer than just taking last step)
        pooled = attn_out.mean(dim=1)       # (batch, lstm_out_dim)

        # 4. FC head
        out = self.post_norm(pooled)
        out = self.dropout(out)
        out = self.act(self.fc1(out))
        out = self.fc2(out)

        return out