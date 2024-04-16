import os
import json


def get_last_file(site):
    files = os.listdir(os.path.join(os.path.join(os.path.abspath(os.curdir), 'data'), 'out'))
    site_fs = []
    for f in files:
        if site in f:
            site_fs.append(f)

    with open(os.path.join(os.path.join(os.path.join(os.path.abspath(os.curdir), 'data'), 'out'), site_fs[-1])) as f:
        data = json.load(f)
    return data


if __name__ == '__main__':
    print(get_last_file('krasnodar-avtos'))