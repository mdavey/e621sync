import concurrent.futures
import os
import requests

# wow, that's a awful looking import
from configuration import Configuration


USER_AGENT = 'e621sync/0.2 (e621 username zero)'
CONFIG = Configuration()
CONFIG.load('config.toml')


def run_rule(rule):
    print('Processing: {}'.format(rule))

    if not os.path.exists(rule.download_directory):
        print('Making directory: {}'.format(rule.download_directory))
        os.makedirs(rule.download_directory)

    print('Building file list...', end='')

    # Build complete list of all data first
    # For now, just be reasonable and don't build large searches?
    # TODO: Add --everything command line argument to re-check and fetch everything, else just sync recent stuff?
    before_id = None
    download_list = []
    while True:
        items = get_list(rule.tags, before_id)

        if len(items) == 0:
            break

        print('.', end='')

        for item in items:

            # keep track of were we are up to
            if before_id is None or item['id'] < before_id:
                before_id = item['id']

            # client side tag check
            if has_blacklisted_tag(item, rule.blacklist_tags):
                continue

            filename = rule.download_directory + str(item['id']) + '_' + item['md5'] + '.' + item['file_ext']

            if not os.path.exists(filename):
                download_list.append({'id': item['id'], 'url': item['file_url'], 'dest': filename})

    count_total_items = len(download_list)
    count_completed_items = 0
    print('')
    print('Found {} new items to fetch'.format(count_total_items))

    with concurrent.futures.ThreadPoolExecutor(max_workers=CONFIG.max_workers) as executor:
        futures = {executor.submit(download, item['url'], item['dest']): item for item in download_list}

        for future in concurrent.futures.as_completed(futures):
            count_completed_items += 1
            item = futures[future]
            try:
                bytes_written = future.result()
                print('[{}/{}]  Downloaded {} (size: {})'.format(count_completed_items,
                                                                 count_total_items,
                                                                 item['dest'], bytes_written))
            except Exception as e:
                print('[{}/{}]  Download {} failed: {}'.format(count_completed_items,
                                                               count_total_items,
                                                               item['dest'], e))

    print('')


def has_blacklisted_tag(item, blacklist_tags):
    tags = item['tags'].split(' ')

    for blacklisted_tag in blacklist_tags:
        if blacklisted_tag in tags:
            return True

    return False


def get_list(tags, before_id=None):
    args = {'tags': ' '.join(tags), 'limit': CONFIG.list_limit}

    # If None, just get the latest
    if before_id is not None:
        args['before_id'] = before_id

    r = requests.get('https://e621.net/post/index.json', args, headers={'User-Agent': USER_AGENT}, timeout=30)
    json = r.json()

    if 'success' in json and json['success'] is False:
        raise Exception('Error getting list: {}'.format(json['reason']))

    return json


def download(url, filename):
    r = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=30)

    with open(filename, 'wb') as f:
        return f.write(r.content)


if __name__ == '__main__':
    for this_rule in CONFIG.rules:
        run_rule(this_rule)
