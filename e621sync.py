import concurrent.futures
import requests
import sys
import os.path
import argparse
import toml


USER_AGENT = 'e621sync/0.31 (e621 username zero)'
HTTP_DEFAULT_TIMEOUT = 30


class ConfigurationException(Exception):
    pass


class Configuration:
    def __init__(self):
        self._config = None
        self.max_workers = 4
        self.list_limit = 100
        self.common_tags = []
        self.blacklist_tags = []
        self.minimum_score = -10
        self.rules = []

    def load(self, filename):
        with open(filename, 'r') as f:
            self.loads(f.read())
        return self

    def loads(self, s):

        try:
            self._config = toml.loads(s)
        except toml.TomlDecodeError as e:
            raise ConfigurationException(e)

        self.list_limit = self._parse_int(self._config, 'list_limit', 10, 320, self.list_limit)
        self.max_workers = self._parse_int(self._config, 'max_workers', 1, 16, self.max_workers)
        self.common_tags = self._parse_list_of_strings(self._config, 'common_tags', self.common_tags)

        # TODO: Probably shouldn't need to use these values, except to fill in the Rules?
        self.blacklist_tags = self._parse_list_of_strings(self._config, 'blacklist_tags', self.blacklist_tags)
        self.minimum_score = self._parse_int(self._config, 'minimum_score', -100000, 100000, self.minimum_score)

        self.rules = []
        for rule_name in self._config['rules']:
            rule_config = self._config['rules'][rule_name]
            rule = Rule(rule_name)

            # TODO: Are common tags even a good idea?  Would handling 'rating' be enough?
            rule.tags.extend(self.common_tags)
            rule.tags.extend(self._parse_list_of_strings(rule_config, 'tags', []))

            # Default to global settings if not set
            rule.blacklist_tags = self._parse_list_of_strings(rule_config, 'blacklist_tags', self.blacklist_tags)
            rule.minimum_score = self._parse_int(rule_config, 'minimum_score', -100000, 100000, self.minimum_score)
            rule.download_directory = self._parse_string(rule_config, 'download_directory', None)
            rule.list_limit = self._parse_int(rule_config, 'list_limit', 10, 320, self.list_limit)

            # Sets are not ordered by id like general searches.  To make sure all items are found, need to order the
            # results by id (highest to lowest).  Check if the user used a 'set:' with an 'order:-id' and fix it.
            # TODO: And then hope that we don't go over 6 tags
            if rule.has_set_and_needs_order_tag():
                rule.tags.append('order:-id')

            if len(rule.tags) < 6 and not rule.has_score_tag():
                rule.tags.append('score:>{}'.format(rule.minimum_score))

            # TODO: should we try and apply some of the blacklist tags here too if < 6 tags?

            if len(rule.tags) == 0:
                raise ConfigurationException("Rule {} has no tags".format(rule_name))

            if len(rule.tags) > 6:
                raise ConfigurationException("Rule {} has more than 6 tags".format(rule_name))

            if len(rule.tags) != len(set(rule.tags)):
                raise ConfigurationException("Rule {} has duplicate tags".format(rule_name))

            if rule.download_directory is None:
                raise ConfigurationException("Rule {} has no download directory".format(rule_name))

            self.rules.append(rule)

    @staticmethod
    def _parse_int(config, name, minimum, maximum, default):
        if name not in config:
            return default

        if (type(config[name]) is not int) or \
                (config[name] > maximum) or \
                (config[name] < minimum):
            raise ConfigurationException("{} most be an integer between {} and {}".format(name, minimum, maximum))

        return config[name]

    @staticmethod
    def _parse_string(config, name, default):
        if name not in config:
            return default

        if type(config[name]) is not str:
            ConfigurationException("{} most be a string".format(name))

        return config[name]

    @staticmethod
    def _parse_list_of_strings(config, name, default):
        if name not in config:
            return default

        if type(config[name]) is not list:
            raise ConfigurationException("{} must be an array of strings".format(name))

        for s in config[name]:
            if type(s) is not str:
                raise ConfigurationException("{} must be an array of strings: {} is not a string".format(name, s))

        return config[name]


class Rule:
    def __init__(self, name):
        self.name = name
        self.tags = []
        self.download_directory = None
        self.blacklist_tags = []
        self.minimum_score = -10
        self.list_limit = 100

    def __str__(self):
        return "Rule<{}>  tags: {}  download_directory: {}  blacklist_tags: {}  minimum_score: {}".format(
            self.name, ','.join(self.tags), self.download_directory, ','.join(self.blacklist_tags), self.minimum_score)

    def has_score_tag(self):
        """Does this rule use a 'score:' tag"""
        for tag in self.tags:
            if tag.find('score:') == 0:
                return True
        return False

    def has_set_and_needs_order_tag(self):
        """If a 'set:' tag is used, check if the 'order:-id' tag is missing"""
        has_set = False
        has_correct_order = False
        for tag in self.tags:
            if tag.find('set:') == 0:
                has_set = True
            elif tag == 'order:-id':
                has_correct_order = True

        return has_set and not has_correct_order

    def make_download_directory(self):
        if not os.path.exists(self.download_directory):
            os.makedirs(self.download_directory)

    def build_download_list(self):
        """
        Returns list of DownloadItem
        Uses before_id to keep requesting list_limit items at a time
        """
        before_id = None
        download_list = []
        while True:
            items = self._get_list(before_id)

            if len(items) == 0:
                break

            for item in items:
                # keep track of were we are up to
                if before_id is None or item['id'] < before_id:
                    before_id = item['id']

                # client side tag check
                if self._has_blacklisted_tag(item['tags'].split(' ')):
                    continue

                filename = '{}{:d}_{}.{}'.format(self.download_directory, item['id'], item['md5'], item['file_ext'])

                if not os.path.exists(filename):
                    download_list.append(DownloadItem(self, item['file_url'], filename))

        return download_list

    def _get_list(self, before_id=None):
        """Get the raw data for post/index.json"""
        args = {'tags': ' '.join(self.tags), 'limit': self.list_limit}

        # If None, just get the latest
        if before_id is not None:
            args['before_id'] = before_id

        r = requests.get('https://e621.net/post/index.json', args, headers={'User-Agent': USER_AGENT},
                         timeout=HTTP_DEFAULT_TIMEOUT)
        json = r.json()

        if 'success' in json and json['success'] is False:
            raise Exception('Error getting list: {}'.format(json['reason']))

        return json

    def _has_blacklisted_tag(self, tags):
        """Checks if any of the passed tags are blacklisted"""
        for blacklisted_tag in self.blacklist_tags:
            if blacklisted_tag in tags:
                return True

        return False


class DownloadItem:
    def __init__(self, rule, url, destination_filename):
        self.rule = rule
        self.url = url
        self.destination_filename = destination_filename

    def __str__(self):
        return 'DownloadItem<{}>  {}  {}'.format(self.rule.name, self.url, self.destination_filename)

    def download(self):
        r = requests.get(self.url, headers={'User-Agent': USER_AGENT}, HTTP_DEFAULT_TIMEOUT=30)

        with open(self.destination_filename, 'wb') as f:
            return f.write(r.content)


def build_complete_download_list(rules, max_workers):
    download_list = []
    print('Found {:d} rules.  Building download list...'.format(len(rules)))

    for rule in rules:
        rule.make_download_directory()

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(rule.build_download_list): rule for rule in rules}

        for future in concurrent.futures.as_completed(futures):
            rule = futures[future]
            try:
                new_download_items = future.result()
                download_list.extend(new_download_items)
                print('Rule<{}>  Found {:d} new items to download'.format(rule.name, len(new_download_items)))
            except Exception as e:
                print('Rule<{}>  Failed: {}\nRule Details: {}'.format(rule.name, e, rule))

    return download_list


def start_downloading(download_list, max_workers):
    count_completed_items = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(item.download): item for item in download_list}

        for future in concurrent.futures.as_completed(futures):
            count_completed_items += 1
            item = futures[future]
            try:
                bytes_written = future.result()
                print('[{}/{}]  Rule<{}>  {} ({:.0f KB})'.format(count_completed_items, len(download_list),
                                                                 item.rule.name, item.destination_filename,
                                                                 bytes_written / 1024))
            except Exception as e:
                print('[{}/{}]  {} failed: {}'.format(count_completed_items, len(download_list), item, e))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config',
                        help='Specify a configuration file to load (default: config.toml)',
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

    download_list = build_complete_download_list(config.rules, config.max_workers)
    start_downloading(download_list, config.max_workers)


if __name__ == '__main__':
    main()
