import pytest

from e621sync.rule import Rule, RuleException


class TestRule:
    def test_has_score_tag(self):
        rule = Rule('test rule')
        rule.tags = ['foo', 'bar']
        assert rule.has_score_tag() is False
        rule.tags = ['foo', 'bar', 'score:10']
        assert rule.has_score_tag() is True
        rule.tags = ['foo', 'bar', 'score:>10']
        assert rule.has_score_tag() is True
        rule.tags = ['foo', 'bar', 'score:<10']
        assert rule.has_score_tag() is True

    def test_has_blacklisted_tag(self):
        rule = Rule('test rule')
        rule.blacklist_tags = ['foo', 'bar']
        assert rule.has_blacklisted_tag(['baz']) is False
        rule.blacklist_tags = ['foo', 'bar', 'baz']
        assert rule.has_blacklisted_tag(['baz']) is True

    def test_get_pool_id(self):
        rule = Rule('test rule')
        rule.tags = ['foo', 'bar']
        assert rule.get_pool_id() is None
        rule.tags = ['pool:12345', 'bar']
        assert rule.get_pool_id() == 12345
        with pytest.raises(RuleException):
            rule.tags = ['pool:abc', 'bar']
            rule.get_pool_id()

    def test_has_set_and_needs_order_tag(self):
        rule = Rule('test rule')
        rule.tags = ['foo', 'bar']
        assert rule.has_set_and_needs_order_tag() is False
        rule.tags = ['foobar', 'set:12345', 'order:-id']
        assert rule.has_set_and_needs_order_tag() is False

        with pytest.raises(RuleException):
            rule.tags = ['foobar', 'set:12345', 'order:id']
            rule.has_set_and_needs_order_tag()

        rule.tags = ['foobar', 'set:12345']
        assert rule.has_set_and_needs_order_tag() is True
