from threading import Thread
from queue import PriorityQueue, Empty


class PriorityJob:
    def __init__(self, priority: int, fun, *args, **kwargs):
        self.priority = priority
        self.fun = fun
        self.args = args
        self.kwargs = kwargs

    def run(self):
        self.fun(*self.args, **self.kwargs)

    def __str__(self):
        return '{}'.format(self.fun)

    def __lt__(self, other):
        return self.priority < other.priority


class LowPriorityJob(PriorityJob):
    def __init__(self, fun, *args, **kwargs):
        super().__init__(10, fun, *args, **kwargs)


class HighPriorityJob(PriorityJob):
    def __init__(self, fun, *args, **kwargs):
        super().__init__(1, fun, *args, **kwargs)


class Worker(Thread):
    def __init__(self, job_queue: PriorityQueue):
        super().__init__()
        self.job_queue = job_queue
        self.is_running = True

    def run(self):
        while self.is_running:
            try:
                job = self.job_queue.get(True, 1)
            except Empty:
                continue

            try:
                job.run()
            except Exception as e:
                print(e)
            finally:
                self.job_queue.task_done()

    def stop(self):
        self.is_running = False


class ThreadPool:
    def __init__(self, max_workers: int):
        self.job_queue = PriorityQueue()
        self.threads = [Worker(self.job_queue) for _ in range(0, max_workers)]

    def add_job(self, job: PriorityJob):
        self.job_queue.put(job)

    def run(self):
        [worker.start() for worker in self.threads]
        self.job_queue.join()
        [worker.stop() for worker in self.threads]
