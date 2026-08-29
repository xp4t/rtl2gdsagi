from .run_model import DictListModel


class StrategyModel(DictListModel):
    def __init__(self, parent=None):
        super().__init__([
            {"name": "sweep_a", "strategyFocus": "Balanced (baseline)", "wns": "+0.092", "tns": "-1.324", "area": "12.38M", "power": "125.7", "congestion": "0.72", "runtime": "00:48:12", "violations": "0", "completed": "May 22 06:00"},
            {"name": "sweep_b", "strategyFocus": "Timing-first", "wns": "+0.287", "tns": "-0.423", "area": "12.86M", "power": "142.1", "congestion": "0.81", "runtime": "01:02:35", "violations": "0", "completed": "May 22 06:14"},
            {"name": "sweep_c", "strategyFocus": "Density-guarded", "wns": "-0.013", "tns": "-2.987", "area": "11.74M", "power": "131.3", "congestion": "0.46", "runtime": "00:52:07", "violations": "2", "completed": "May 22 06:05"},
            {"name": "sweep_d", "strategyFocus": "Power-first", "wns": "-0.118", "tns": "-3.772", "area": "12.01M", "power": "102.4", "congestion": "0.65", "runtime": "00:44:21", "violations": "0", "completed": "May 22 06:56"},
        ], parent)
