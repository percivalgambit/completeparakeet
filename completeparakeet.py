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

@app.route('/', methods=['GET', 'POST'])
def complete_parakeet():
    if request.method == 'GET':
        return render_template('index.html', show_parakeet=False)
    if request.method == 'POST':
        file = request.files['file']
        if file:
            # make a directory for the uploads
            try:
                os.mkdir(UPLOAD_FOLDER)
            except FileExistsError:
                pass
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return render_template('index.html', show_parakeet=True)

@app.route('/parakeet')
def get_parakeet():
    image = random.choice(os.listdir(IMAGES_FOLDER))
    return send_from_directory(IMAGES_FOLDER, image, as_attachment=True, attachment_filename="parakeet")

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


if __name__ == '__main__':
    if '--no-scrape' not in sys.argv:
        scrape_images('"cute parakeet"', 10)
    app.run(debug=True)
