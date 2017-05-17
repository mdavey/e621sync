from typing import List, Optional


class RuleException(Exception):
    pass


class Rule:
    def __init__(self, name: str):
        self.name = name
        self.tags = []
        self.download_directory = None
        self.blacklist_tags = []
        self.minimum_score = -10
        self.list_limit = 100

    def __str__(self) -> str:
        return "Rule<{}>  tags: {}  download_directory: {}  blacklist_tags: {}  minimum_score: {}".format(
            self.name, ','.join(self.tags), self.download_directory, ','.join(self.blacklist_tags), self.minimum_score)

    @staticmethod
    def _find_partial_tag(source_tags: List[str], partial_tag: str) -> Optional[str]:
        """Looks for a start of a string in a list of string.  If found returns the entire string, else None
           e.g.  _find_partial_tag(['foobar:123'], 'foo') -> 'foobar:123' """
        for tag in source_tags:
            if tag.find(partial_tag) == 0:
                return tag
        return None

    def has_score_tag(self) -> bool:
        """Does this rule use a 'score:' tag"""
        return self._find_partial_tag(self.tags, 'score:') is not None

    def has_set_and_needs_order_tag(self) -> bool:
        """If a 'set:' tag is used, check if the 'order:-id' tag is missing"""
        has_set = self._find_partial_tag(self.tags, 'set:')
        has_correct = self._find_partial_tag(self.tags, 'order:')

        # No set
        if has_set is None:
            return False

        # Has set, but no correct
        if has_correct is None:
            return True

        # Has set and a correct order tag
        if has_correct == 'order:-id':
            return False

        # Has set and and an order tag, but it's wrong
        raise RuleException('Rule has set: tag and order tag that is not "order:-id"')

    def has_blacklisted_tag(self, tags: List[str]) -> bool:
        """Checks if any of the passed tags are blacklisted"""
        for blacklisted_tag in self.blacklist_tags:
            if blacklisted_tag in tags:
                return True
        return False

    def get_pool_id(self) -> Optional[int]:
        pool_tag = self._find_partial_tag(self.tags, 'pool:')
        if pool_tag:
            try:
                return int(pool_tag[len('pool:'):])
            except ValueError:
                raise RuleException('pool id must be an int in: {}'.format(pool_tag))
        return None
