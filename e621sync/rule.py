from typing import List


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

    def has_score_tag(self) -> bool:
        """Does this rule use a 'score:' tag"""
        for tag in self.tags:
            if tag.find('score:') == 0:
                return True
        return False

    def has_set_and_needs_order_tag(self) -> bool:
        """If a 'set:' tag is used, check if the 'order:-id' tag is missing"""
        has_set = False
        has_correct_order = False
        for tag in self.tags:
            if tag.find('set:') == 0:
                has_set = True
            elif tag == 'order:-id':
                has_correct_order = True

        return has_set and not has_correct_order

    def has_blacklisted_tag(self, tags: List[str]) -> bool:
        """Checks if any of the passed tags are blacklisted"""
        for blacklisted_tag in self.blacklist_tags:
            if blacklisted_tag in tags:
                return True

        return False
