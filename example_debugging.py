from speciesot import Experiment
from speciesot.speciesot_core import R2Evaluation
# Check how to select enviornemtn in py files


experiment_spec_path = "/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/example_debugging.yaml"
experiment = Experiment(experiment_spec_path)

experiment.setup()
experiment.train()
experiment.predict()
#experiment.evaluations.append(R2Evaluation())
experiment.evaluate()



