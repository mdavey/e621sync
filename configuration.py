import toml


class ConfigurationException(Exception):
    pass


class Rule:
    def __init__(self, name):
        self.name = name
        self.tags = []
        self.download_directory = None
        self.blacklist_tags = []
        self.minimum_score = -10

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

    def loads(self, s):
        self._config = toml.loads(s)

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

            # TODO: Are common tags even a good idea?
            rule.tags.extend(self.common_tags)
            rule.tags.extend(self._parse_list_of_strings(rule_config, 'tags', []))

            # Default to global settings if not set
            rule.blacklist_tags = self._parse_list_of_strings(rule_config, 'blacklist_tags', self.blacklist_tags)
            rule.minimum_score = self._parse_int(rule_config, 'minimum_score', -100000, 100000, self.minimum_score)
            rule.download_directory = self._parse_string(rule_config, 'download_directory', None)

            if rule.has_set_and_needs_order_tag():
                rule.tags.append('order:-id')

            # Sets are not ordered by id like general searches.  To make sure all items are found, need to order the
            # results by id (highest to lowest).  Check if the user used a 'set:' with an 'order:-id' and fix it.
            # TODO: And then hope that we don't go over 6 tags
            if len(rule.tags) < 6 and not rule.has_score_tag():
                rule.tags.append('score:>{}'.format(rule.minimum_score))

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


if __name__ == '__main__':
    # TODO: This doesn't count as testing
    test = Configuration()
    test.loads(open('config.toml').read())
    for this_rule in test.rules:
        print(this_rule)
