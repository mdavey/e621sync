import sys
import argparse
import os
from typing import List, Dict

import requests

from e621sync.configuration import Configuration, ConfigurationException
from e621sync.threadpool import ThreadPool, LowPriorityJob, HighPriorityJob
from e621sync.rule import Rule


USER_AGENT = 'e621sync/0.43 (e621 username zero https://github.com/mdavey/e621sync)'
HTTP_DEFAULT_TIMEOUT = 30


def download_item(thread_pool: ThreadPool, rule: Rule, url: str, filename: str):
    r = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=HTTP_DEFAULT_TIMEOUT)

    if not os.path.exists(rule.download_directory):
        os.makedirs(rule.download_directory)

    with open(filename, 'wb') as f:
        bytes_written = f.write(r.content)

    print('[{:d}]  Rule<{}>  Downloaded {:s}  ({:.0f} KB)'.format(thread_pool.job_queue.qsize(), rule.name, filename,
                                                                  bytes_written / 1024))


def get_json(url: str, request_vars: Dict[str, str]):
    r = requests.get(url, request_vars, headers={'User-Agent': USER_AGENT}, timeout=HTTP_DEFAULT_TIMEOUT)
    json = r.json()

    if 'success' in json and json['success'] is False:
        raise Exception('Error getting list: {}'.format(json['reason']))

    return json


def get_post_listing(rule: Rule, before_id: int = None):
    post_vars = {'tags': ' '.join(rule.tags), 'limit': rule.list_limit}

    # If None, just get the latest
    if before_id is not None:
        post_vars['before_id'] = str(before_id)

    return get_json('https://e621.net/post/index.json', post_vars)


def get_pool_listing(pool_id: int, page_num: int = None):
    """
    Need to handle pools separately as they have implicit sorting that cannot
    be handled with just searching for 'pool:1234' (at least I cannot figure it out) 
    """
    pool_vars = {'id': str(pool_id)}

    if page_num is not None:
        pool_vars['page'] = str(page_num)

    return get_json('https://e621.net/pool/show.json', pool_vars)


def process_rule_pool(thread_pool: ThreadPool, rule: Rule, page_num: int = None):
    counter = 0

    items = get_pool_listing(rule.get_pool_id(), page_num)

    for index, item in enumerate(items['posts']):
        filename = '{}{:04d}_{:d}_{}.{}'.format(rule.download_directory, index + ((page_num-1)*24), item['id'],
                                                item['md5'], item['file_ext'])

        if not os.path.exists(filename):
            counter += 1
            thread_pool.add_job(LowPriorityJob(download_item, thread_pool, rule, item['file_url'], filename))

    if len(items['posts']) > 0:
        thread_pool.add_job(HighPriorityJob(process_rule_pool, thread_pool, rule, page_num + 1))

    if counter > 0:
        print('[{:d}]  Rule<{}>  Found {:d} new items to download'.format(thread_pool.job_queue.qsize(), rule.name,
                                                                          counter))


def process_rule_post(thread_pool: ThreadPool, rule: Rule, before_id: int = None):
    counter = 0
    items = get_post_listing(rule, before_id)
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
            thread_pool.add_job(LowPriorityJob(download_item, thread_pool, rule, item['file_url'], filename))

    # if we found items to download with the last before_id value, try the next listing
    if len(items) > 0:
        thread_pool.add_job(HighPriorityJob(process_rule_post, thread_pool, rule, before_id))

    # Did we actually queue any new jobs?
    if counter > 0:
        print('[{:d}]  Rule<{}>  Found {:d} new items to download'.format(thread_pool.job_queue.qsize(), rule.name,
                                                                          counter))


def sync(rules: List[Rule], max_workers: int):
    print('Starting e621sync with {:d} threads'.format(max_workers))
    thread_pool = ThreadPool(max_workers=max_workers)
    for rule in rules:
        pool_id = rule.get_pool_id()
        if pool_id is None:
            thread_pool.add_job(HighPriorityJob(process_rule_post, thread_pool, rule))
        else:
            thread_pool.add_job(HighPriorityJob(process_rule_pool, thread_pool, rule, 1))
    thread_pool.run()
    print('Done')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='Specify a configuration file to load (default: config.toml)',
                        default='config.toml')
    command_line_args = parser.parse_args()

    try:
        config = Configuration().load(command_line_args.config)
    except FileNotFoundError:
        print('Unable to find config file: {}'.format(command_line_args.config))
        sys.exit(1)
    except ConfigurationException as e:
        print('Unable to load config file: {}'.format(command_line_args.config))
        print(e)
        sys.exit(1)

    sync(config.rules, config.max_workers)
