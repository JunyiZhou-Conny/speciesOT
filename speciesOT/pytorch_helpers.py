import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from collections import OrderedDict
from typing import Dict, Any, List

# ----- Hyperparameters -----
EPOCHS = 100
BATCH_SIZE = 64          # keep >=2 for BatchNorm
LR = 1e-3
WEIGHT_DECAY = 1e-4
SEED = 42

def set_seed(seed: int = 42):
    import random
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

def build_model() -> nn.Sequential:
    # Exactly the requested architecture/names
    model = nn.Sequential(OrderedDict([
        ('dense0',     nn.Linear(50, 50, bias=True)),
        ('batchnorm0', nn.BatchNorm1d(50, eps=1e-5, momentum=0.1, affine=True, track_running_stats=True)),
        ('act0',       nn.ReLU()),
        ('dense1',     nn.Linear(50, 50, bias=True)),
        ('batchnorm1', nn.BatchNorm1d(50, eps=1e-5, momentum=0.1, affine=True, track_running_stats=True)),
        ('act1',       nn.ReLU()),
        ('dense_out',  nn.Linear(50, 50, bias=True)),
    ]))
    return model

def prepare_tensors(X: np.ndarray, Y: np.ndarray, device: torch.device):
    # Ensure 2D [N, 50]
    X = np.asarray(X, dtype=np.float32)
    Y = np.asarray(Y, dtype=np.float32)
    if X.ndim == 1: X = X.reshape(1, -1)
    if Y.ndim == 1: Y = Y.reshape(1, -1)
    assert X.shape[1] == 50 and Y.shape[1] == 50, f"Expected X and Y with 50 columns, got {X.shape}, {Y.shape}"

    Xt = torch.from_numpy(X).to(device)
    Yt = torch.from_numpy(Y).to(device)
    return Xt, Yt

def fit_mlp(X: np.ndarray, Y: np.ndarray, epochs=EPOCHS, batch_size=BATCH_SIZE, lr=LR,
            weight_decay=WEIGHT_DECAY) -> Dict[str, List[float]]:
    set_seed(SEED)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    model = build_model().to(device).float()
    criterion = nn.MSELoss()  # 50-d regression target
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    Xt, Yt = prepare_tensors(X, Y, device)
    ds = TensorDataset(Xt, Yt)
    # drop_last=True keeps BatchNorm stable if the last batch would be size 1
    dl = DataLoader(ds, batch_size=batch_size, shuffle=True, drop_last=True)

    history = {'train_loss': []}
    model.train()
    for epoch in range(1, epochs + 1):
        running = 0.0
        count = 0
        for xb, yb in dl:
            optimizer.zero_grad(set_to_none=True)
            preds = model(xb)                 # [B, 50]
            loss = criterion(preds, yb)       # MSE over 50 dims
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            running += loss.item() * xb.size(0)
            count  += xb.size(0)

        epoch_loss = running / max(count, 1)
        history['train_loss'].append(epoch_loss)
        if epoch % 100 == 0 or epoch == 1:
            print(f"Epoch {epoch:03d} | loss {epoch_loss:.6f}")

    # Switch to eval for inference
    model.eval()
    return {'model': model, 'history': history}

