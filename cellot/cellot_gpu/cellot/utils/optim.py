import torch


def sync_optimizer_device(optim, device):
    """Adam exp_avg buffers must live on the same device as parameters after resume."""
    if device is None:
        return
    for state in optim.state.values():
        for k, v in state.items():
            if torch.is_tensor(v):
                state[k] = v.to(device)
