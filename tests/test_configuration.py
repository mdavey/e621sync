import pytest

from e621sync.configuration import Configuration, ConfigurationException

example_configuration_header = '''
list_limit = 100
max_workers = 4
common_tags = [ "rating:safe" ]
blacklist_tags = [ "duck" ]
minimum_score = 10
'''

example_configuration_duplicate_rules = example_configuration_header + '''
[rules.rule1]
tags = [ "foobar" ]
download_directory = "./foo/"

[rules.rule1]
tags = [ "tagme" ]
minimum_score = 2
blacklist_tags = []
download_directory = "./bar/"
'''

example_configuration_1 = example_configuration_header + '''
[rules.rule]
tags = [ "foobar" ]
download_directory = "./foo/"
'''

example_configuration_2 = example_configuration_header + '''
[rules.rule]
tags = [ "tagme" ]
minimum_score = 2
blacklist_tags = []
download_directory = "./bar/"
'''


class TestConfiguration:
    def test_parse_int(self):
        # normal
        assert Configuration._parse_int({'value': 123}, 'value', minimum=100, maximum=200, default=111) == 123
        assert Configuration._parse_int({'value': 100}, 'value', minimum=100, maximum=200, default=111) == 100
        assert Configuration._parse_int({'value': 200}, 'value', minimum=100, maximum=200, default=111) == 200

        # missing
        assert Configuration._parse_int({'value': 123}, 'missing_value', minimum=100, maximum=200, default=111) == 111

        # below minimum
        with pytest.raises(ConfigurationException):
            Configuration._parse_int({'value': 99}, 'value', minimum=100, maximum=200, default=111)

        # above maximum
        with pytest.raises(ConfigurationException):
            Configuration._parse_int({'value': 201}, 'value', minimum=100, maximum=200, default=111)

        # wrong type
        with pytest.raises(ConfigurationException):
            Configuration._parse_int({'value': '150'}, 'value', minimum=100, maximum=200, default=111)

    def test_parse_string(self):
        # normal
        assert Configuration._parse_string({'value': 'foo'}, 'value', default='bar') == 'foo'

        # missing
        assert Configuration._parse_string({'value': 'foo'}, 'missing_value', default='bar') == 'bar'

        # wrong type
        with pytest.raises(ConfigurationException):
            Configuration._parse_string({'value': 150}, 'value', default='bar')

    def test_parse_list_of_strings(self):
        # working
        assert Configuration._parse_list_of_strings({'l': ['a', 'b']}, 'l', ['default']) == ['a', 'b']

        # missing
        assert Configuration._parse_list_of_strings({'l': ['a', 'b']}, 'missing', ['default']) == ['default']

        # wrong type 1
        with pytest.raises(ConfigurationException):
            Configuration._parse_list_of_strings({'l': 'foobar'}, 'l', ['default'])

        # wrong type 2
        with pytest.raises(ConfigurationException):
            Configuration._parse_list_of_strings({'l': ['a', 123, 'b']}, 'l', ['default'])

    def test_loading_duplicate_rules(self):
        c = Configuration()
        with pytest.raises(ConfigurationException):
            c.loads(example_configuration_duplicate_rules)

    def test_loading_rules(self):
        c = Configuration()
        c.loads(example_configuration_1)

        assert c.max_workers == 4

        r = c.rules[0]

        assert r.tags == ['rating:safe', 'foobar', 'score:>10']  # eek
        assert r.has_blacklisted_tag(['duck'])
        assert r.minimum_score == 10
        assert r.list_limit == 100
        assert r.download_directory == './foo/'

        c.loads(example_configuration_2)
        r = c.rules[0]

        assert r.tags == ['rating:safe', 'tagme', 'score:>2']
        assert r.blacklist_tags == []
