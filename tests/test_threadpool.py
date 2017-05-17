from e621sync.threadpool import ThreadPool, LowPriorityJob, HighPriorityJob


class TestThreadPool:
    def test_ordering(self):
        # this of course looks wrong...  Lower value entries are picked first in a queue.PriorityQueue
        l = LowPriorityJob(print)
        h = HighPriorityJob(print)
        assert l > h

    def test_enter_exit(self):
        with ThreadPool(2) as thread_pool:
            thread_pool.add_job(LowPriorityJob(print))
            pass
