import torch
import cellot.models
from cellot.data.cell import load_cell_data

# reads the yaml config and check if cuda is available
# return a torch.device
def resolve_device(config):
    name = config.get("device", "cpu")
    if name == "cuda" and not torch.cuda.is_available():
        name = "cpu"
    return torch.device(name)



def load_data(config, **kwargs):
    data_type = config.get("data.type", "cell")
    if data_type in ["cell", "cell-merged", "tupro-cohort"]:
        loadfxn = load_cell_data

    elif data_type == "toy":
        loadfxn = load_toy_data

    else:
        raise ValueError

    return loadfxn(config, **kwargs)


def load_model(config, restore=None, device=None, **kwargs):
    name = config.get("model.name", "cellot")
    if name == "cellot":
        loadfxn = cellot.models.load_cellot_model

    elif name == "scgen":
        loadfxn = cellot.models.load_autoencoder_model

    elif name == "cae":
        loadfxn = cellot.models.load_autoencoder_model

    elif name == "popalign":
        loadfxn = cellot.models.load_popalign_model

    else:
        raise ValueError

    return loadfxn(config, restore=restore, device=device, **kwargs)
    # every other file should import resolve_device from here

# pass the device down to load, and then load_model
def load(config, restore=None, include_model_kwargs=False, **kwargs):
    device = resolve_device(config)

    loader, model_kwargs = load_data(config, include_model_kwargs=True, **kwargs)

    model, opt = load_model(config, restore=restore, device=device, **model_kwargs)

    if include_model_kwargs:
        return model, opt, loader, model_kwargs

    return model, opt, loader
