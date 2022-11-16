# sample of capturing local variable
import time

from ebilab.experiment.core import Experiment

class SampleExperiment(Experiment):
    columns = ["var1", "var2"]
    filename = "sample-exp"

    def steps(self):
        var2 = 2
        self.send_row({"var1": 1}, capture=["var2"])
        time.sleep(1)


if __name__ == "__main__":
    experiment = SampleExperiment()
    experiment.start()
