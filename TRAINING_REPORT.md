=======================================================
  STEP 1 — Generating Synthetic Dataset
=======================================================
[DATAGEN] Segment breakdown:
  Segment 01: 435 timesteps  shape=(435, 5)
  Segment 02: 709 timesteps  shape=(709, 5)
  Segment 03: 578 timesteps  shape=(578, 5)
  Segment 04: 621 timesteps  shape=(621, 5)
  Segment 05: 556 timesteps  shape=(556, 5)
  Segment 06: 727 timesteps  shape=(727, 5)
  Segment 07: 648 timesteps  shape=(648, 5)
  Segment 08: 438 timesteps  shape=(438, 5)
  Segment 09: 415 timesteps  shape=(415, 5)
  Segment 10: 514 timesteps  shape=(514, 5)
  Segment 11: 600 timesteps  shape=(600, 5)
  Segment 12: 400 timesteps  shape=(400, 5)
  Segment 13: 350 timesteps  shape=(350, 5)
  Segment 14: 350 timesteps  shape=(350, 5)
  Segment 15: 300 timesteps  shape=(300, 5)
  Segment 16: 500 timesteps  shape=(500, 5)
  Segment 17: 450 timesteps  shape=(450, 5)
  Segment 18: 500 timesteps  shape=(500, 5)
  Segment 19: 400 timesteps  shape=(400, 5)
  Segment 20: 500 timesteps  shape=(500, 5)
  Segment 21: 450 timesteps  shape=(450, 5)
  Segment 22: 400 timesteps  shape=(400, 5)
  Segment 23: 500 timesteps  shape=(500, 5)
  Segment 24: 450 timesteps  shape=(450, 5)
  Segment 25: 400 timesteps  shape=(400, 5)
  Segment 26: 500 timesteps  shape=(500, 5)
  Segment 27: 450 timesteps  shape=(450, 5)
  Segment 28: 400 timesteps  shape=(400, 5)
  Segment 29: 400 timesteps  shape=(400, 5)
  Segment 30: 500 timesteps  shape=(500, 5)
  Segment 31: 400 timesteps  shape=(400, 5)
  Segment 32: 500 timesteps  shape=(500, 5)
  Segment 33: 400 timesteps  shape=(400, 5)
  Segment 34: 500 timesteps  shape=(500, 5)
  Segment 35: 400 timesteps  shape=(400, 5)
  Segment 36: 500 timesteps  shape=(500, 5)

[DATAGEN] Total: 17,141 timesteps x 5 features
  request_rate         min=0.053  max=9.157  mean=1.311
  error_rate           min=0.000  max=1.000  mean=0.108
  p95_latency          min=0.072  max=10.001  mean=0.910
  memory_mb            min=20.000  max=792.739  mean=118.051
  active_conns         min=0.000  max=153.393  mean=14.520

=======================================================
  STEP 2 — Normalizing Features
=======================================================
  Scaler fitted on 17141 timesteps.
  Feature means  : [1.31071066e+00 1.08070150e-01 9.09796479e-01 1.18050566e+02
 1.45199022e+01]
  Feature scales : [  1.00833826   0.21681894   1.79287856 103.83790887  16.05740801]

=======================================================
  STEP 3 — Building Sequences
=======================================================
  X shape: (17111, 30, 5)   (samples, seq_len, features)
  y shape: (17111, 5)   (samples, features)
  Train samples : 13689
  Val   samples : 3422

=======================================================
  STEP 4 — Model Initialisation
=======================================================
  Device       : cpu
  Parameters   : 276,357
  Architecture :
LSTMForecastModel(
  (lstm): LSTM(5, 128, num_layers=2, batch_first=True, dropout=0.25)
  (attention): MultiheadAttention(
    (out_proj): NonDynamicallyQuantizableLinear(in_features=128, out_features=128, bias=True)    
  )
  (attn_norm): LayerNorm((128,), eps=1e-05, elementwise_affine=True)
=======================================================
  [✓] Epoch    1/120 | Train: 0.518963 | Val: 0.258085 | LR: 5.00e-04 | Patience: 0/15     
  [✓] Epoch    2/120 | Train: 0.242580 | Val: 0.178936 | LR: 5.00e-04 | Patience: 0/15     
  [✓] Epoch    3/120 | Train: 0.163652 | Val: 0.115627 | LR: 5.00e-04 | Patience: 0/15     
  [✓] Epoch    4/120 | Train: 0.128640 | Val: 0.093019 | LR: 5.00e-04 | Patience: 0/15     
  [✓] Epoch    5/120 | Train: 0.111224 | Val: 0.072653 | LR: 5.00e-04 | Patience: 0/15     
  [✓] Epoch    6/120 | Train: 0.097615 | Val: 0.057714 | LR: 5.00e-04 | Patience: 0/15     
  [✓] Epoch    7/120 | Train: 0.091778 | Val: 0.055454 | LR: 5.00e-04 | Patience: 0/15     
  [✓] Epoch    8/120 | Train: 0.087822 | Val: 0.050824 | LR: 5.00e-04 | Patience: 0/15     
  [✓] Epoch    9/120 | Train: 0.078681 | Val: 0.049753 | LR: 5.00e-04 | Patience: 0/15
  [ ] Epoch   10/120 | Train: 0.073987 | Val: 0.056278 | LR: 5.00e-04 | Patience: 1/15
  [ ] Epoch   11/120 | Train: 0.070713 | Val: 0.054387 | LR: 5.00e-04 | Patience: 2/15
  [✓] Epoch   12/120 | Train: 0.065058 | Val: 0.035591 | LR: 5.00e-04 | Patience: 0/15
  [✓] Epoch   13/120 | Train: 0.063253 | Val: 0.032604 | LR: 5.00e-04 | Patience: 0/15
  [ ] Epoch   14/120 | Train: 0.057636 | Val: 0.047462 | LR: 5.00e-04 | Patience: 1/15
  [ ] Epoch   15/120 | Train: 0.057270 | Val: 0.039296 | LR: 5.00e-04 | Patience: 2/15
  [ ] Epoch   16/120 | Train: 0.052549 | Val: 0.038654 | LR: 5.00e-04 | Patience: 3/15
  [✓] Epoch   17/120 | Train: 0.047845 | Val: 0.026161 | LR: 5.00e-04 | Patience: 0/15
  [✓] Epoch   18/120 | Train: 0.044065 | Val: 0.022482 | LR: 5.00e-04 | Patience: 0/15
  [ ] Epoch   19/120 | Train: 0.040587 | Val: 0.027541 | LR: 5.00e-04 | Patience: 1/15
  [ ] Epoch   20/120 | Train: 0.039887 | Val: 0.024342 | LR: 5.00e-04 | Patience: 2/15
  [ ] Epoch   21/120 | Train: 0.036612 | Val: 0.025086 | LR: 5.00e-04 | Patience: 3/15
  [ ] Epoch   22/120 | Train: 0.035207 | Val: 0.023046 | LR: 5.00e-04 | Patience: 4/15
  [ ] Epoch   23/120 | Train: 0.036870 | Val: 0.023972 | LR: 5.00e-04 | Patience: 5/15
  [✓] Epoch   24/120 | Train: 0.033385 | Val: 0.018631 | LR: 5.00e-04 | Patience: 0/15
  [ ] Epoch   25/120 | Train: 0.034414 | Val: 0.024295 | LR: 5.00e-04 | Patience: 1/15
  [ ] Epoch   26/120 | Train: 0.032115 | Val: 0.023616 | LR: 5.00e-04 | Patience: 2/15
  [ ] Epoch   27/120 | Train: 0.030175 | Val: 0.024294 | LR: 5.00e-04 | Patience: 3/15
  [ ] Epoch   28/120 | Train: 0.030157 | Val: 0.021654 | LR: 5.00e-04 | Patience: 4/15
  [ ] Epoch   29/120 | Train: 0.028835 | Val: 0.040066 | LR: 5.00e-04 | Patience: 5/15
  [ ] Epoch   30/120 | Train: 0.029980 | Val: 0.027744 | LR: 5.00e-04 | Patience: 6/15
  [ ] Epoch   31/120 | Train: 0.027795 | Val: 0.022447 | LR: 5.00e-04 | Patience: 7/15
  [ ] Epoch   32/120 | Train: 0.025437 | Val: 0.018773 | LR: 2.50e-04 | Patience: 8/15
  [✓] Epoch   33/120 | Train: 0.021203 | Val: 0.014483 | LR: 2.50e-04 | Patience: 0/15
  [ ] Epoch   34/120 | Train: 0.020939 | Val: 0.016250 | LR: 2.50e-04 | Patience: 1/15
  [✓] Epoch   35/120 | Train: 0.020886 | Val: 0.014307 | LR: 2.50e-04 | Patience: 0/15
  [ ] Epoch   36/120 | Train: 0.020838 | Val: 0.014918 | LR: 2.50e-04 | Patience: 1/15
  [ ] Epoch   37/120 | Train: 0.020027 | Val: 0.016502 | LR: 2.50e-04 | Patience: 2/15
  [✓] Epoch   38/120 | Train: 0.019957 | Val: 0.014035 | LR: 2.50e-04 | Patience: 0/15
  [ ] Epoch   39/120 | Train: 0.019330 | Val: 0.019398 | LR: 2.50e-04 | Patience: 1/15
  [ ] Epoch   40/120 | Train: 0.020096 | Val: 0.015992 | LR: 2.50e-04 | Patience: 2/15
  [✓] Epoch   41/120 | Train: 0.019482 | Val: 0.013861 | LR: 2.50e-04 | Patience: 0/15
  [ ] Epoch   42/120 | Train: 0.020199 | Val: 0.015483 | LR: 2.50e-04 | Patience: 1/15
  [ ] Epoch   43/120 | Train: 0.018816 | Val: 0.018539 | LR: 2.50e-04 | Patience: 2/15
  [ ] Epoch   44/120 | Train: 0.019933 | Val: 0.015185 | LR: 2.50e-04 | Patience: 3/15
  [✓] Epoch   45/120 | Train: 0.018285 | Val: 0.012449 | LR: 2.50e-04 | Patience: 0/15
  [ ] Epoch   46/120 | Train: 0.018225 | Val: 0.016015 | LR: 2.50e-04 | Patience: 1/15
  [ ] Epoch   47/120 | Train: 0.018013 | Val: 0.015249 | LR: 2.50e-04 | Patience: 2/15
  [✓] Epoch   48/120 | Train: 0.018645 | Val: 0.012321 | LR: 2.50e-04 | Patience: 0/15
  [ ] Epoch   49/120 | Train: 0.017752 | Val: 0.015056 | LR: 2.50e-04 | Patience: 1/15
  [ ] Epoch   50/120 | Train: 0.018489 | Val: 0.016599 | LR: 2.50e-04 | Patience: 2/15
  [ ] Epoch   51/120 | Train: 0.017288 | Val: 0.013209 | LR: 2.50e-04 | Patience: 3/15
  [ ] Epoch   52/120 | Train: 0.017245 | Val: 0.017212 | LR: 2.50e-04 | Patience: 4/15
  [ ] Epoch   53/120 | Train: 0.017194 | Val: 0.017095 | LR: 2.50e-04 | Patience: 5/15
  [ ] Epoch   54/120 | Train: 0.017545 | Val: 0.015598 | LR: 2.50e-04 | Patience: 6/15
  [ ] Epoch   55/120 | Train: 0.017642 | Val: 0.014047 | LR: 2.50e-04 | Patience: 7/15
  [ ] Epoch   56/120 | Train: 0.017164 | Val: 0.017784 | LR: 1.25e-04 | Patience: 8/15
  [ ] Epoch   57/120 | Train: 0.015258 | Val: 0.013842 | LR: 1.25e-04 | Patience: 9/15
  [ ] Epoch   58/120 | Train: 0.015809 | Val: 0.012495 | LR: 1.25e-04 | Patience: 10/15
  [ ] Epoch   59/120 | Train: 0.015231 | Val: 0.013620 | LR: 1.25e-04 | Patience: 11/15
  [ ] Epoch   60/120 | Train: 0.014694 | Val: 0.015128 | LR: 1.25e-04 | Patience: 12/15
  [ ] Epoch   61/120 | Train: 0.015404 | Val: 0.013379 | LR: 1.25e-04 | Patience: 13/15
  [ ] Epoch   62/120 | Train: 0.014733 | Val: 0.013447 | LR: 1.25e-04 | Patience: 14/15
  [ ] Epoch   63/120 | Train: 0.014684 | Val: 0.017186 | LR: 1.25e-04 | Patience: 15/15

  Early stopping triggered at epoch 63.
  Best epoch was 48 with val_loss=0.012321

=======================================================
  STEP 6 — Computing Anomaly Threshold
=======================================================
  Val MSE stats:
    Mean    : 0.959088
    Std     : 2.460579
    P95     : 4.978338
    P99     : 14.987963   ← used as threshold
  Threshold set to: 14.987963

=======================================================
  STEP 7 — Saving Artifacts
=======================================================
  Model     → C:\Users\gudde\Desktop\SelfHealingAI\remediation_engine\ai\..\..\models\lstm_model.pt
  Scaler    → C:\Users\gudde\Desktop\SelfHealingAI\remediation_engine\ai\..\..\models\scaler.pkl
  Threshold → C:\Users\gudde\Desktop\SelfHealingAI\remediation_engine\ai\..\..\models\threshold.json
  History   → C:\Users\gudde\Desktop\SelfHealingAI\remediation_engine\ai\..\..\models\training_history.json

=======================================================
  TRAINING COMPLETE
=======================================================
  Best epoch       : 48
  Best val loss    : 0.012321
  Anomaly threshold: 14.987963
  Total samples    : 17,111
  Training samples : 13,689
  Validation samp  : 3,422
