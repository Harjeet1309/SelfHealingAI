import numpy as np


class SequenceBuilder:
    def __init__(self, sequence_length: int = 30):
        self.sequence_length = sequence_length

    def build_sequences(self, data: np.ndarray):
        """
        data shape: (timesteps, features)
        Returns:
            X shape: (samples, sequence_length, features)
            y shape: (samples, features)
        """
        X, y = [], []

        for i in range(len(data) - self.sequence_length):
            X.append(data[i:i + self.sequence_length])
            y.append(data[i + self.sequence_length])

        return np.array(X), np.array(y)