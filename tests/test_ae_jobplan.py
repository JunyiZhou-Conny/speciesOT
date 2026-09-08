import inspect
import os

from speciesot.ae import AutoEncoderModel, JobPlan


def test_gpu_train_returns_jobplan_without_sbatch():
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = os.path.join(repo, "specs", "m1_modern.yaml")
    model = AutoEncoderModel(spec)
    plan = model.train(device="gpu")
    assert isinstance(plan, JobPlan)
    assert plan.submitted is False
    assert "sbatch/train/" in plan.text
    assert "hvg_pearson_residuals_m1_v08_ood" in plan.text
    assert plan.experiment_tag == "hvg_pearson_residuals_m1_v08_ood"
    assert plan.interpreter == "CellOT_gpu"
    src = inspect.getsource(AutoEncoderModel.train)
    assert "subprocess" not in src
    assert "Popen" not in src
    assert "os.system" not in src
    assert not any(token.isdigit() and len(token) >= 6 for token in plan.text.split() if token.isdigit())


def test_cpu_jobplan_names_cellot():
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = os.path.join(repo, "specs", "m1_modern.yaml")
    plan = AutoEncoderModel(spec).train(device="cpu")
    assert plan.interpreter == "CellOT"
    assert plan.submitted is False


if __name__ == "__main__":
    test_gpu_train_returns_jobplan_without_sbatch()
    test_cpu_jobplan_names_cellot()
    print("test_ae_jobplan ok")
