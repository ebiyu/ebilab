# sample of ctx.sleep
from ebilab.experiment import ExperimentProtocol, ExperimentContext
from ebilab.experiment.options import FloatField


class RandomWalkExperiment(ExperimentProtocol):
    columns = []
    name = "ctx-sleep"
    options = {
        "time": FloatField(default=10),
    }

    def steps(self, ctx: ExperimentContext) -> None:
        # you have to use ctx.sleep instead of time.sleep in order to make STOP button to work
        ctx.sleep(ctx.options["time"])
