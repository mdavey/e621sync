from .downloadposts import DownloadPosts
from .threadpool import HighPriorityJob


class DownloadPool(DownloadPosts):
    def get_listing(self, page_num: int = None):
        pool_vars = {'id': str(self.rule.get_pool_id())}

        if page_num is not None:
            pool_vars['page'] = str(page_num)

        return self.get_json('https://e621.net/pool/show.json', pool_vars)

    def process_rule(self, page_num: int = 1):
        items = self.get_listing(page_num)
        self.items_found += len(items)

        for index, item in enumerate(items['posts']):

            self.queue_download(item['file_url'], '{:04d}_{:d}_{}.{}'.format(index + ((page_num-1)*24), item['id'],
                                                                             item['md5'], item['file_ext']))

        # found new items on this page, so try the next
        if len(items['posts']) > 0:
            self.thread_pool.add_job(HighPriorityJob(self.process_rule, page_num + 1))
        else:
            self.print_rule_summary()