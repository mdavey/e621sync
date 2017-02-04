import requests
import os.path


class Rule:
    def __init__(self, name):
        self.name = name
        self.tags = []
        self.download_directory = None
        self.blacklist_tags = []
        self.minimum_score = -10
        self.list_limit = 100
        self.user_agent = 'e621sync/0.3 (e621 username zero)'  # TODO Placing this here is a little odd

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

        r = requests.get('https://e621.net/post/index.json', args, headers={'User-Agent': self.user_agent}, timeout=30)
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
        r = requests.get(self.url, headers={'User-Agent': self.rule.user_agent}, timeout=30)

        with open(self.destination_filename, 'wb') as f:
            return f.write(r.content)
