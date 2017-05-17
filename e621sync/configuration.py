import toml
from typing import List

from .rule import Rule


class ConfigurationException(Exception):
    pass


class Configuration:
    def __init__(self):
        self._config = None
        self.max_workers = 4
        self.rules = []  # type: List[Rule]

    def load(self, filename: str):
        with open(filename, 'r') as f:
            self.loads(f.read())
        return self

    def loads(self, s: str):
        try:
            self._config = toml.loads(s)
        except toml.TomlDecodeError as e:
            raise ConfigurationException(e)

        self.max_workers = self._parse_int(self._config, 'max_workers', 1, 16, self.max_workers)

        list_limit = self._parse_int(self._config, 'list_limit', 10, 320, 100)
        common_tags = self._parse_list_of_strings(self._config, 'common_tags', [])
        blacklist_tags = self._parse_list_of_strings(self._config, 'blacklist_tags', [])
        minimum_score = self._parse_int(self._config, 'minimum_score', -100000, 100000, 0)

        self.rules = []
        for rule_name in self._config['rules']:
            rule_config = self._config['rules'][rule_name]
            rule = Rule(rule_name)

            # TODO: Are common tags even a good idea?  Would handling 'rating' be enough?
            rule.tags.extend(common_tags)
            rule.tags.extend(self._parse_list_of_strings(rule_config, 'tags', []))

            # Default to global settings if not set
            rule.blacklist_tags = self._parse_list_of_strings(rule_config, 'blacklist_tags', blacklist_tags)
            rule.minimum_score = self._parse_int(rule_config, 'minimum_score', -100000, 100000, minimum_score)
            rule.download_directory = self._parse_string(rule_config, 'download_directory', None)
            rule.list_limit = self._parse_int(rule_config, 'list_limit', 10, 320, list_limit)

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
    def _parse_int(config, name: str, minimum: int, maximum: int, default: int = None):
        if name not in config:
            return default

        if (type(config[name]) is not int) or \
                (config[name] > maximum) or \
                (config[name] < minimum):
            raise ConfigurationException("{} most be an integer between {} and {}".format(name, minimum, maximum))

        return config[name]

    @staticmethod
    def _parse_string(config, name: str, default: str = None):
        if name not in config:
            return default

        if type(config[name]) is not str:
            raise ConfigurationException("{} most be a string".format(name))

        return config[name]

    @staticmethod
    def _parse_list_of_strings(config, name: str, default: List[str] = None):
        if name not in config:
            return default

        if type(config[name]) is not list:
            raise ConfigurationException("{} must be an array of strings".format(name))

        for s in config[name]:
            if type(s) is not str:
                raise ConfigurationException("{} must be an array of strings: {} is not a string".format(name, s))

        return config[name]
