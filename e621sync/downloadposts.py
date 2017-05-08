import os
from typing import Dict

import requests

from .threadpool import ThreadPool, LowPriorityJob, HighPriorityJob
from .rule import Rule
from .globalsettings import USER_AGENT, HTTP_DEFAULT_TIMEOUT


class DownloadPosts:
    def __init__(self, thread_pool: ThreadPool, rule: Rule):
        self.thread_pool = thread_pool
        self.rule = rule
        self.items_found = 0
        self.items_queued = 0
        thread_pool.add_job(HighPriorityJob(self.process_rule))

    @staticmethod
    def get_json(url: str, request_vars: Dict[str, str]):
        r = requests.get(url, request_vars, headers={'User-Agent': USER_AGENT}, timeout=HTTP_DEFAULT_TIMEOUT)
        json = r.json()

        if 'success' in json and json['success'] is False:
            raise Exception('Error getting list: {}'.format(json['reason']))

        return json

    def download_item(self, url: str, filename: str):
        r = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=HTTP_DEFAULT_TIMEOUT)

        if not os.path.exists(self.rule.download_directory):
            os.makedirs(self.rule.download_directory)

        with open(filename, 'wb') as f:
            bytes_written = f.write(r.content)

        print('[{:d}]  <{}>  Downloaded {:s}  ({:.0f} KB)'.format(self.thread_pool.job_queue.qsize(), self.rule.name,
                                                                  filename, bytes_written / 1024))

    def get_listing(self, before_id: int = None):
        post_vars = {'tags': ' '.join(self.rule.tags), 'limit': self.rule.list_limit}

        # If None, just get the latest
        if before_id is not None:
            post_vars['before_id'] = str(before_id)

        return self.get_json('https://e621.net/post/index.json', post_vars)

    def queue_download(self, url: str, filename: str):
        """Join the rule directory with the base filename, and if it hasn't already been downloaded, queue it up"""
        full_filename = os.path.join(self.rule.download_directory, filename)
        if not os.path.exists(full_filename):
            self.thread_pool.add_job(LowPriorityJob(self.download_item, url, full_filename))
            self.items_queued += 1

    def process_rule(self, before_id: int = None):
        items = self.get_listing(before_id)
        self.items_found += len(items)

        for item in items:
            # keep track of were we are up to
            if before_id is None or item['id'] < before_id:
                before_id = item['id']

            # client side tag check
            if self.rule.has_blacklisted_tag(item['tags'].split(' ')):
                continue

            self.queue_download(item['file_url'], '{:d}_{}.{}'.format(item['id'], item['md5'], item['file_ext']))

        # if we found items to download with the last before_id value, try the next listing
        if len(items) > 0:
            self.thread_pool.add_job(HighPriorityJob(self.process_rule, before_id))
        else:
            self.print_rule_summary()

    def print_rule_summary(self):
        print('[{:d}]  <{}>  Found {:d} items, {:d} queued for download'.format(
            self.thread_pool.job_queue.qsize(), self.rule.name, self.items_found, self.items_queued))
