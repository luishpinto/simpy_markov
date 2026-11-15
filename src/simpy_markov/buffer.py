"""Buffer di processo."""
import simpy
from .history import History

class Buffer:
    def __init__(self, env, name, capacity, init=0, history_limit=2000, recorder=None):
        self.env, self.name = env, name
        self.capacity = capacity
        self.buff = simpy.Container(env, capacity=capacity, init=init)
        self.stat = History(history_limit,
                            (lambda row: recorder.write('buffers', row)) if recorder else None)
        self.save()

    def save(self):
        self.stat.append(dict(name=self.name, time=self.env.now,
                              level=self.buff.level, capacity=self.capacity))
