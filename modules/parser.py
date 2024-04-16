import pandas as pd
import requests
import time
import json
import re

from datetime import datetime

from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from tqdm import tqdm
from transliterate import translit, get_available_language_codes


def get_soup(url):
    return BeautifulSoup(requests.get(url, headers={'user-agent': UserAgent().random}).text, 'lxml')


brands_dict = {}


def get_brand_id(brand):
    if not brand in brands_dict.keys():
        brands_dict[brand] = len(brands_dict.keys())
    return brands_dict[brand]


def parse_mainpage(url):
    SITE = url[:-1]

    soup = get_soup(url)
    brands = soup.find_all(class_='logobar--brand')
    data = pd.DataFrame()

    for brand in tqdm(brands):
        try:
            soup = get_soup(f"{SITE}{brand.find('a')['href']}")
            cards = soup.find_all(class_='catalog--brands-list--brand--model-card')

            for card in cards:
                row = pd.DataFrame()

                row.loc[0, 'brand'] = brand.text.strip()
                row.loc[0, 'url'] = f"{SITE}{card.find('a')['href']}"
                row.loc[0, 'name'] = card.find(class_='brand-model').text.strip()
                row.loc[0, 'old_price'] = int(
                    card.find(class_='price-old rub').text.strip().replace(u'\xa0', '').replace('от', ''))
                row.loc[0, 'new_price'] = int(
                    card.find(class_='price-new mt-2 rub').text.strip().replace(u'\xa0', '').replace('от', ''))
                row.loc[0, 'img_url'] = f"{SITE}{card.find('img')['src']}"

                data = pd.concat([data, row])
        except:
            print(f"{SITE}{brand.find('a')['href']}")

    data = data.reset_index(drop=True)

    return data, SITE


def parse_catalog(data, SITE):
    result = []
    colorshex = []
    for i in tqdm(data.index):  # data.index
        url = data.loc[i, 'url']
        soup = get_soup(url)
        car = {
            'brand': data.loc[i, 'brand'],
            'brand_alias': data.loc[i, 'url'].split('/')[-3],
            'brand_sort_order': get_brand_id(data.loc[i, 'brand']),

            'model_full': data.loc[i, 'name'].replace(data.loc[i, 'brand'], '').strip(),
            'model_alias': data.loc[i, 'url'].split('/')[-2],

            'body': soup.find(class_='color-text-blur font-500').text.strip() if soup.find(
                class_='color-text-blur font-500') else soup.find(class_='color-text-blur').text.strip(),
            'body_alias': translit(soup.find(class_='color-text-blur font-500').text.strip(),
                                   reversed=True).lower() if soup.find(class_='color-text-blur font-500') else translit(
                soup.find(class_='color-text-blur').text.strip(), reversed=True).lower(),

            # 'seats': 5,  #
            # 'doors': 5,  #
            'img_url': data.loc[i, 'img_url'],

            'prices': [],
            'colors': [],
            'galleries': []
        }

        photos = soup.find_all(class_='catalog--model--gallery-thumbnail')
        i = 0
        for photo in photos:
            photo_dict = {
                'url': f"{SITE}{photo['href']}",
                'type': photo['data-img-type'],
                'sort_order': i
            }
            i += 1
            car['galleries'].append(photo_dict)

        color_imgs = soup.find(class_='catalog--model--colors-widget--carousel').find_all('img')
        colors = soup.find(class_='catalog--model--colors-widget--swatches').find_all('div')
        for color in colors:
            if '#' in color['style']:
                for color_img in color_imgs:
                    try:
                        if color_img['class'][0].replace('color-', '') == color['data-color-id']:
                            color_url = f"{SITE}{color_img['data-src']}"
                    except Exception as e:
                        print(url, e)
                color_dict = {
                    'name': None,  #
                    'colorhex': color['style'].replace('background-color: ', '').replace(';', ''),
                    'img_url': color_url
                }
                colorshex.append(color['style'].replace('background-color: ', ''))
                car['colors'].append(color_dict)

        mods_l = soup.find_all(class_='catalog--model--price-widget--modification')
        for mod_l in mods_l:
            mods = mod_l.find_all(class_='catalog--model--price-widget--modification--price-position')
            for mod in mods:
                mod_dict = {
                    'complectation': mod.find(
                        class_='catalog--model--price-widget--col-complectation flex align-center xs4 md3 pr-2').text.strip(),
                    'complectation_alias': re.sub(r'[^\w\s]', '', mod.find(
                        class_='catalog--model--price-widget--col-complectation flex align-center xs4 md3 pr-2').text.strip()).lower().replace(
                        ' ', '_'),
                    'cost': int(mod.find(
                        class_='catalog--model--price-widget--col-oldcost xs4 display-xsonly-hidden px-2').text.strip()),
                    'cost_discount': int(
                        mod.find(class_='catalog--model--price-widget--col-cost-value rub').text.strip()),
                }

                techs = mod.find_all(class_='flex align-center catalog--model--price-widget--section-row')
                for tech in techs:
                    if tech.contents[1].text.strip() == 'Тип кузова':
                        mod_dict['body'] = tech.contents[3].text.strip() if tech.contents[3].text.strip() else None
                    if tech.contents[1].text.strip() == 'Двери':
                        mod_dict['doors'] = int(tech.contents[3].text.strip()) if tech.contents[
                            3].text.strip() else None
                    if tech.contents[1].text.strip() == 'Тип топлива':
                        mod_dict['engine_type'] = tech.contents[3].text.strip() if tech.contents[
                            3].text.strip() else None
                    if tech.contents[1].text.strip() == 'Объем двигателя, см3':
                        mod_dict['engine_volume'] = int(tech.contents[3].text.strip()) if tech.contents[
                            3].text.strip() else 0
                    if tech.contents[1].text.strip() == 'Мощность двигателя, л.с.':
                        mod_dict['engine_power'] = int(tech.contents[3].text.strip()) if tech.contents[
                            3].text.strip() else None
                    if tech.contents[1].text.strip() == 'Крутящий момент':
                        mod_dict['engine_torque'] = tech.contents[3].text.strip() if tech.contents[
                            3].text.strip() else None
                    if tech.contents[1].text.strip() == 'Топливо':
                        mod_dict['fuel'] = tech.contents[3].text.strip() if tech.contents[3].text.strip() else None
                    if tech.contents[1].text.strip() == 'Тип трансмиссии':
                        mod_dict['gearbox'] = tech.contents[3].text.strip() if tech.contents[3].text.strip() else None
                        mod_dict['gearbox_auto'] = 1 if tech.contents[3].text.strip() == 'Автомат' else 0
                    if tech.contents[1].text.strip() == 'Количество передач':
                        mod_dict['gears'] = int(tech.contents[3].text.strip()) if tech.contents[
                            3].text.strip() else None
                    if tech.contents[1].text.strip() == 'Привод':
                        mod_dict['transmission'] = tech.contents[3].text.strip() if tech.contents[
                            3].text.strip() else None
                    if tech.contents[1].text.strip() == 'Габариты, мм':
                        mod_dict['dim_length'] = int(tech.contents[3].text.strip().split('/')[0]) if tech.contents[
                            3].text.strip() else None
                        mod_dict['dim_width'] = int(tech.contents[3].text.strip().split('/')[1]) if tech.contents[
                            3].text.strip() else None
                        mod_dict['dim_height'] = int(tech.contents[3].text.strip().split('/')[2]) if tech.contents[
                            3].text.strip() else None
                    if tech.contents[1].text.strip() == 'Дорожный просвет, мм':
                        mod_dict['clearence'] = int(tech.contents[3].text.strip()) if tech.contents[
                            3].text.strip() else None
                    if tech.contents[1].text.strip() == 'Колесная база, мм':
                        mod_dict['dim_base'] = int(tech.contents[3].text.strip()) if tech.contents[
                            3].text.strip() else None
                    if tech.contents[1].text.strip() == 'Количество мест':
                        mod_dict['seats'] = tech.contents[3].text.strip() if tech.contents[3].text.strip() else None
                    if tech.contents[1].text.strip() == 'Объем багажника, л.':
                        mod_dict['luggage'] = int(tech.contents[3].text.strip().split('/')[0]) if tech.contents[
                            3].text.strip() else None
                        mod_dict['luggage_max'] = int(tech.contents[3].text.strip().split('/')[0]) if tech.contents[
                            3].text.strip() else None
                        mod_dict['luggage_text'] = f"{tech.contents[3].text.strip().split('/')[0]} л" if tech.contents[
                            3].text.strip() else None
                    if tech.contents[1].text.strip() == 'Максимальная скорость, км/ч':
                        mod_dict['max_speed'] = int(tech.contents[3].text.strip()) if tech.contents[
                            3].text.strip() else None
                    if tech.contents[1].text.strip() == 'Разгон 0-100 км/ч, ч':
                        mod_dict['acceleration'] = round(float(tech.contents[3].text.strip()), 1) if tech.contents[
                            3].text.strip() else None
                    if tech.contents[1].text.strip() == 'Город, л/100 км':
                        mod_dict['consumption_city'] = round(float(tech.contents[3].text.strip()), 1) if tech.contents[
                            3].text.strip() else None
                    if tech.contents[1].text.strip() == 'Трасса, л/100 км':
                        mod_dict['consumption_highway'] = round(float(tech.contents[3].text.strip()), 1) if \
                            tech.contents[3].text.strip() else None
                    if tech.contents[1].text.strip() == 'Смешанный цикл, л/100 км':
                        mod_dict['consumption_mixed'] = round(float(tech.contents[3].text.strip()), 1) if tech.contents[
                            3].text.strip() else None
                mod_dict['active'] = 1

                mod_dict['equipments'] = []
                eqs = mod.find(
                    class_='flex wrap catalog--model--price-widget--modification--price-position--readmore-container').contents[
                    3].find_all(class_='flex align-center catalog--model--price-widget--section-row')
                i = 0
                for eq in eqs:
                    eq_dict = {
                        # 'group_name': None,
                        'name': eq.contents[1].text.strip(),
                        'sort_order': i,
                        'price': None if eq.contents[3].text.strip() == 'Есть' or eq.contents[3].text.strip() == '' or
                                         eq.contents[3].text.strip() == 'Опция' else int(
                            eq.contents[3].text.strip().replace(u'\xa0', '').replace('₽', ''))
                    }
                    i += 1
                    mod_dict['equipments'].append(eq_dict)
                car['prices'].append(mod_dict)

        result.append(car)
        time.sleep(1)

    save_url = ''
    for car in result:
        to_del = []
        for i in range(len(car['colors'])):
            if car['colors'][i]['img_url'] == save_url:
                car['colors'][i - 1]['colorhex2'] = car['colors'][i]['colorhex']
                to_del.append(car['colors'][i])
            else:
                car['colors'][i]['colorhex2'] = None
                save_url = car['colors'][i]['img_url']
        for d in to_del:
            car['colors'].remove(d)

    return result


def save_result_json(result, filename):
    # filename = url.replace('https://', '')[:-1].replace('-', '_').split('/')[0].split('.')[0]
    with open(f'../data/out/result_{filename}_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json', 'w') as file:
        json.dump(result, file, indent=4)


def parser():
    sites = pd.read_csv('../data/sites.csv')
    for i in sites.index:
        try:
            url = sites.loc[i, 'url']
            data, SITE = parse_mainpage(url)
            result = parse_catalog(data, SITE)
            save_result_json(result, sites.loc[i, 'site'])
        except Exception as e:
            print(sites.loc[i, 'site'], e)


if __name__ == '__main__':
    while True:
        parser()
        time.sleep(60*60*24)
