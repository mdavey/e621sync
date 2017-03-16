from threading import Thread
from queue import PriorityQueue, Empty


class Job:
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


class Worker(Thread):
    def __init__(self, job_queue: PriorityQueue):
        super().__init__()
        self.job_queue = job_queue
        self.is_running = True

    def run(self):
        while self.is_running:
            try:
                job = self.job_queue.get(True, 1)
                job.run()
                self.job_queue.task_done()
            except Empty:
                pass

    def stop(self):
        self.is_running = False


class ThreadPool:
    def __init__(self, max_workers: int):
        self.job_queue = PriorityQueue()
        self.threads = [Worker(self.job_queue) for _ in range(0, max_workers)]

    def add_job(self, job: Job):
        self.job_queue.put(job)

    def run(self):
        [worker.start() for worker in self.threads]
        self.job_queue.join()
        [worker.stop() for worker in self.threads]
