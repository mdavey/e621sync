import sys
import argparse
import os.path
from typing import List

import requests

from e621sync.configuration import Configuration, ConfigurationException
from e621sync.threadpool import ThreadPool, Job
from e621sync.rule import Rule


USER_AGENT = 'e621sync/0.40 (e621 username zero)'
HTTP_DEFAULT_TIMEOUT = 30


def download_item(thread_pool: ThreadPool, rule: Rule, url: str, filename: str):
    r = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=HTTP_DEFAULT_TIMEOUT)

    if not os.path.exists(rule.download_directory):
        os.makedirs(rule.download_directory)

    with open(filename, 'wb') as f:
        bytes_written = f.write(r.content)

    print('[{:d}]  Rule<{}>  Downloaded {:s}  ({:.0f} KB)'.format(thread_pool.job_queue.qsize(), rule.name, filename,
                                                                  bytes_written / 1024))


def get_list(rule: Rule, before_id: int = None):
    """Get the raw data for post/index.json"""
    post_vars = {'tags': ' '.join(rule.tags), 'limit': rule.list_limit}

    # If None, just get the latest
    if before_id is not None:
        post_vars['before_id'] = before_id

    r = requests.get('https://e621.net/post/index.json', post_vars, headers={'User-Agent': USER_AGENT},
                     timeout=HTTP_DEFAULT_TIMEOUT)
    json = r.json()

    if 'success' in json and json['success'] is False:
        raise Exception('Error getting list: {}'.format(json['reason']))

    return json


def process_rule(thread_pool: ThreadPool, rule: Rule, before_id: int = None):
    counter = 0
    items = get_list(rule, before_id)
    for item in items:

        # keep track of were we are up to
        if before_id is None or item['id'] < before_id:
            before_id = item['id']

        # client side tag check
        if rule.has_blacklisted_tag(item['tags'].split(' ')):
            continue

        filename = '{}{:d}_{}.{}'.format(rule.download_directory, item['id'], item['md5'], item['file_ext'])

        if not os.path.exists(filename):
            counter += 1
            thread_pool.add_job(Job(10, download_item, thread_pool, rule, item['file_url'], filename))

    if len(items) > 0:
        thread_pool.add_job(Job(0, process_rule, thread_pool, rule, before_id))

    if counter > 0:
        print('[{:d}]  Rule<{}>  Found {:d} new items to download'.format(thread_pool.job_queue.qsize(), rule.name,
                                                                           counter))


def sync(rules: List[Rule], max_workers: int):
    print('Starting e621sync with {:d} threads'.format(max_workers))
    thread_pool = ThreadPool(max_workers=max_workers)
    for rule in rules:
        thread_pool.add_job(Job(0, process_rule, thread_pool, rule))
    thread_pool.run()
    print('Done')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='Specify a configuration file to load (default: config.toml)',
                        default='config.toml')
    args = parser.parse_args()

    try:
        config = Configuration().load(args.config)
    except FileNotFoundError:
        print('Unable to find config file: {}'.format(args.config))
        sys.exit(1)
    except ConfigurationException as e:
        print('Unable to load config file: {}'.format(args.config))
        print(e)
        sys.exit(1)

    sync(config.rules, config.max_workers)
