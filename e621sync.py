import sys
import argparse
from typing import List

from e621sync.configuration import Configuration, ConfigurationException
from e621sync.threadpool import ThreadPool
from e621sync.rule import Rule
from e621sync.downloadposts import DownloadPosts
from e621sync.downloadpool import DownloadPool
from e621sync.globalsettings import VERSION


def sync(rules: List[Rule], max_workers: int):
    print('Starting e621sync {} with {:d} rules and {:d} threads'.format(VERSION, len(rules), max_workers))

    with ThreadPool(max_workers=max_workers) as thread_pool:
        for rule in rules:
            if rule.get_pool_id() is not None:
                DownloadPool(thread_pool, rule)
            else:
                DownloadPosts(thread_pool, rule)

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
