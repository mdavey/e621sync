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

    # Build complete list of all data first
    # For now, just be reasonable and don't build large searches?
    # TODO: Add --everything command line argument to re-check and fetch everything, else just sync recent stuff?
    before_id = None
    download_list = []
    while True:
        items = get_list(rule['tags'], before_id)

        if len(items) == 0:
            break

        print('Found {} items'.format(len(items)))

        for item in items:
            filename = rule['download_directory'] + str(item['id']) + '_' + item['md5'] + '.' + item['file_ext']

            # keep track of were we are up to
            if before_id is None or item['id'] < before_id:
                before_id = item['id']

            if not os.path.exists(filename):
                download_list.append({'id': item['id'], 'url': item['file_url'], 'dest': filename})

    print('Found {} new items to fetch'.format(len(download_list)))

    with concurrent.futures.ThreadPoolExecutor(max_workers=CONFIG['max_workers']) as executor:
        futures = {executor.submit(download, item['url'], item['dest']): item for item in download_list}

        for future in concurrent.futures.as_completed(futures):
            item = futures[future]
            try:
                bytes_written = future.result()
                print('Download {} (size: {})'.format(item['dest'], bytes_written))
            except Exception as e:
                print('Download {} failed: {}'.format(item['dest'], e))


def get_list(tag_string, before_id=None):
    args = {'tags': tag_string, 'limit': CONFIG['list_limit']}
    if before_id is not None:
        args['before_id'] = before_id

    r = requests.get('https://e621.net/post/index.json', args, headers={'User-Agent': USER_AGENT}, timeout=30)
    return r.json()


def download(url, filename):
    r = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=30)

    with open(filename, 'wb') as f:
        return f.write(r.content)


if __name__ == '__main__':
    conf = toml.load(open('./config.toml'))

    for rule_name, rule in dict.items(conf['rules']):
        run_rule(rule_name, rule)
