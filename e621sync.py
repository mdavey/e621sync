import concurrent.futures
import os
import requests
import toml


USER_AGENT = 'e621sync/0.1'
CONFIG = toml.load(open('config.toml'))


def run_rule(name, rule):
    print('Processing rule: {}'.format(name))

    if not os.path.exists(rule['download_directory']):
        print('Making directory: {}'.format(rule['download_directory']))
        os.makedirs(rule['download_directory'])

    tags = []
    tags.extend(CONFIG['common_tags'])
    tags.extend(rule['tags'])

    print('Tags: {}'.format(', '.join(tags)))

    if not check_tags(tags):
        return

    print('Building file list...', end='')

    # Build complete list of all data first
    # For now, just be reasonable and don't build large searches?
    # TODO: Add --everything command line argument to re-check and fetch everything, else just sync recent stuff?
    before_id = None
    download_list = []
    while True:
        items = get_list(tags, before_id)

        if len(items) == 0:
            break

        print('.', end='')

        for item in items:
            filename = rule['download_directory'] + str(item['id']) + '_' + item['md5'] + '.' + item['file_ext']

            # keep track of were we are up to
            if before_id is None or item['id'] < before_id:
                before_id = item['id']

            if not os.path.exists(filename):
                download_list.append({'id': item['id'], 'url': item['file_url'], 'dest': filename})

    count_total_items = len(download_list)
    count_completed_items = 0
    print('')
    print('Found {} new items to fetch'.format(count_total_items))

    with concurrent.futures.ThreadPoolExecutor(max_workers=CONFIG['max_workers']) as executor:
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


def check_tags(tags):
    """
    Quick check to see if there is anything funny about the tags
     - Check for 'set:' and no 'order:-id'
     - Check for duplicates
     - Check for more than 6 tags
    """
    has_set = False
    has_correct_order = False
    for tag in tags:
        if 'set:' in tag:
            has_set = True
        elif tag == 'order:-id':
            has_correct_order = True

    if has_set and not has_correct_order:
        print(" - Warning:  Using 'set:' tag without an 'oder:-id' tag.  May not see all results.")
        return True

    if len(tags) > 6:
        print(' - Error:  More than 6 tags specified.  API limit is 6.')
        return False

    if len(tags) != len(set(tags)):
        print(' - Warning:  Duplicate tags')
        return True

    return True


def get_list(tags, before_id=None):
    args = {'tags': ' '.join(tags), 'limit': CONFIG['list_limit']}

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
    for rule_name in CONFIG['rules']:
        run_rule(rule_name, CONFIG['rules'][rule_name])
