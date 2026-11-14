"""
Simple LSTM Autoencoder for Anomaly Detection
==============================================
Trained on real system data to detect behavioral anomalies.

Architecture:
    Input  (batch, seq=30, features=5)
      │
      ▼
    LSTM Encoder  (hidden=32, layers=1)
      │    → compresses sequence into hidden state
      ▼
    LSTM Decoder  (hidden=32, layers=1)
      │    → reconstructs sequence from hidden state
      ▼
    Linear Output Layer  (32 → 5)
      │
      ▼
    Output (batch, seq=30, features=5)  → reconstructed sequence

Anomaly Detection:
    MSE between input and reconstruction
    High MSE = anomaly (pattern doesn't match learned normal behavior)
"""

import torch
import torch.nn as nn


class LSTMForecastModel(nn.Module):
    """Simple LSTM autoencoder optimized for small datasets"""
    def __init__(
        self,
        input_size: int,
        hidden_size: int = 32,
        num_layers: int = 1,
        dropout: float = 0.0,
        num_attention_heads: int = 4,  # Ignored, kept for compatibility
        attention_dropout: float = 0.1,  # Ignored, kept for compatibility
        bidirectional: bool = False,  # Ignored, kept for compatibility
    ):
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        
        # Encoder: input -> hidden
        self.encoder = nn.LSTM(input_size, hidden_size, batch_first=True)
        
        # Decoder: hidden -> hidden
        self.decoder = nn.LSTM(hidden_size, hidden_size, batch_first=True)
        
        # Output projection: hidden -> input
        self.output_layer = nn.Linear(hidden_size, input_size)
        
    def forward(self, x):
        """
        Args:
            x : Tensor (batch, seq_len, input_size)
        Returns:
            output : Tensor (batch, seq_len, input_size) — reconstructed sequence
        """
        # Encode
        _, (hidden, cell) = self.encoder(x)
        
        # Prepare decoder input (repeat last hidden state)
        batch_size = x.size(0)
        seq_len = x.size(1)
        decoder_input = hidden[-1].unsqueeze(1).repeat(1, seq_len, 1)
        
        # Decode
        decoder_output, _ = self.decoder(decoder_input, (hidden, cell))
        
        # Project to output
        output = self.output_layer(decoder_output)
        
        return output