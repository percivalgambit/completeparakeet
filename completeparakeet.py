#!/usr/bin/python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, send_from_directory, request, redirect, url_for
from werkzeug import secure_filename

from collections import OrderedDict
from GoogleScraper import scrape_with_config, GoogleSearchError
import os
import random
import sys

IMAGES_FOLDER = 'images'
UPLOAD_FOLDER = 'upload'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

completed_items = []

@app.route('/', methods=['GET', 'POST'])
def complete_parakeet():
    context = {}
    context['completed_items'] = completed_items
    if request.method == 'GET':
        context['parakeet_img'] = ''
    if request.method == 'POST':
        itemNumberName = request.form['itemNumberName']
        description = request.form['description']
        file = request.files['file']
        if not itemNumberName:
            context['invalid_form_msg'] = 'You must include an item number/name'
            return render_template('index.html', **context)

        # make a directory for the uploads
        try:
            os.mkdir(app.config['UPLOAD_FOLDER'])
        except FileExistsError:
            pass

        try:
            os.mkdir(os.path.join(app.config['UPLOAD_FOLDER'], itemNumberName))
        except FileExistsError:
            context['invalid_form_msg'] = 'That item has already been completed!'
            return render_template('index.html', **context)

        new_item = {'itemNumberName': itemNumberName}

        if description:
            with open(os.path.join(app.config['UPLOAD_FOLDER'], itemNumberName, 'description.txt'), 'w') as descriptionFile:
                descriptionFile.write(description)
            new_item['description'] = description

        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], itemNumberName, filename))
            new_item['file_link'] = os.path.join(app.config['UPLOAD_FOLDER'], itemNumberName, filename)

        completed_items.append(new_item)

        image = os.path.join(IMAGES_FOLDER, random.choice(os.listdir(IMAGES_FOLDER)))
        context['parakeet_img'] = image
    return render_template('index.html', **context)

@app.route('/images/<image>')
def get_parakeet_img(image):
    return send_from_directory(IMAGES_FOLDER, image, as_attachment=True, attachment_filename="parakeet")

@app.route('/parakeet')
def get_parakeet():
    image = os.path.join(IMAGES_FOLDER, random.choice(os.listdir(IMAGES_FOLDER)))
    return render_template('parakeet.html', image=image)

def scrape_images(keyword, num_pages):

    config = {
        'SCRAPING': {
            'keyword': keyword,
            'search_engines': 'google,bing,yahoo',
            'search_type': 'image',
            'num_pages_for_keyword': num_pages,
            'scrape_method': 'http'

        }
    }

    try:
        search = scrape_with_config(config)
    except GoogleSearchError as e:
        print(e)

    image_urls = []

    for serp in search.serps:
        image_urls.extend(
            list(OrderedDict.fromkeys([link.link for link in serp.links]))
        )

    import threading,requests, os, urllib

    class FetchResource(threading.Thread):
        """Grabs a web resource and stores it in the target directory"""
        def __init__(self, target, urls):
            super().__init__()
            self.target = target
            self.urls = urls

        def run(self):
            for url in self.urls:
                url = urllib.parse.unquote(url)
                with open(os.path.join(self.target, url.split('/')[-1]), 'wb') as f:
                    try:
                        content = requests.get(url).content
                        f.write(content)
                    except Exception as e:
                        pass
                    print('[+] Fetched {}'.format(url))

    # make a directory for the results
    try:
        os.mkdir(IMAGES_FOLDER)
    except FileExistsError:
        pass

    # fire up 100 threads to get the images
    num_threads = 100

    threads = [FetchResource(IMAGES_FOLDER, []) for i in range(num_threads)]

    while image_urls:
        for t in threads:
            try:
                t.urls.append(image_urls.pop())
            except IndexError as e:
                break

    threads = [t for t in threads if t.urls]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

def get_completed_item(itemNumberName):
    item_data = {}
    item_data['itemNumberName'] = itemNumberName
    for data in os.listdir(os.path.join(app.config['UPLOAD_FOLDER'], item)):
        if data == 'description.txt':
            description = ''
            with open(os.path.join(app.config['UPLOAD_FOLDER'], itemNumberName, data), 'r') as description_file:
                description = description_file.read()
            item_data['description'] = description
        else:
            item_data['file_link'] = os.path.join(app.config['UPLOAD_FOLDER'], itemNumberName, data)
    return item_data


if os.path.exists(app.config['UPLOAD_FOLDER']):
        for item in os.listdir(app.config['UPLOAD_FOLDER']):
            completed_items.append(get_completed_item(item))

if __name__ == '__main__':
    if '--no-scrape' not in sys.argv:
        scrape_images('"cute parakeet"', 10)
    app.run()
