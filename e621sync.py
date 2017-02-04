import concurrent.futures

from configuration import Configuration


# TODO: This is getting a little out of control, So much copy-pasted code
if __name__ == '__main__':
    CONFIG = Configuration()
    CONFIG.load('config.toml')

    download_list = []
    print('Building file list...')
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONFIG.max_workers) as executor:
        futures = {executor.submit(rule.build_download_list): rule for rule in CONFIG.rules}

        for future in concurrent.futures.as_completed(futures):
            rule = futures[future]
            rule.make_download_directory()  # TODO: This doesn't seem like the right place
            try:
                new_download_items = future.result()
                download_list.extend(new_download_items)
                print('Rule<{}>  Found {:d} new items to download'.format(rule.name, len(new_download_items)))
            except Exception as e:
                print('Rule<{}>  Failed: {}\nRule Details: {}'.format(rule.name, e, rule))

    count_completed_items = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=CONFIG.max_workers) as executor:
        futures = {executor.submit(item.download): item for item in download_list}

        for future in concurrent.futures.as_completed(futures):
            count_completed_items += 1
            item = futures[future]
            try:
                bytes_written = future.result()
                print('[{}/{}]  Rule<{}> {} (size: {})'.format(count_completed_items, len(download_list),
                                                               item.rule.name, item.destination_filename,
                                                               bytes_written))
            except Exception as e:
                print('[{}/{}]  {} failed: {}'.format(count_completed_items, len(download_list), item, e))
