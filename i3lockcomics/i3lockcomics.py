#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pendulum
import os
from subprocess import call
from PIL import Image
import re
import requests
import json
import glob
from random import randint
import sys
import i3lockcomics._getcomics as _getcomics

from screeninfo import get_monitors
monitors = get_monitors()
mon_w = 0
mon_h = 0
# Check which monitor is biggest
for monitor in monitors:
    temp_mon_w = int(re.search(r'monitor\((\d+)x\d+.*',
                     str(monitor)).group(1))
    temp_mon_h = int(re.search(r'monitor\(\d+x(\d+).*',
                     str(monitor)).group(1))
    if temp_mon_w > mon_w:
        mon_w = temp_mon_w
    if temp_mon_h > mon_h:
        mon_h = temp_mon_h
# Setting max width for strips
max_screen_estate = 0.8
max_w = int(int(mon_w) * max_screen_estate)
max_h = int(int(mon_h) * max_screen_estate)


def ratio_check(img_w, img_h):
    '''Calculate if the image is too wide or high. Based on this, find out how
    much the image has to be resized for it to fit within the maximum screen
    estate.'''
    global max_w
    global max_h
    img_w = int(img_w * 1.75)
    img_h = int(img_h * 1.75)
    ratio = min(max_w / img_w, max_h / img_h)
    if ratio < 1:
        img_w = int(img_w * ratio)
        img_h = int(img_h * ratio)
    return img_w, img_h


now = pendulum.now().format('YYYY-MM-DD')


def scrot(strip=False):
    # Take screenshot of screen and pixelize it, save it
    temp_folder = '{}/temp'.format(filedir)
    if not os.path.exists(temp_folder):
            call(['mkdir', temp_folder])
    temp_out = '{}/out.png'.format(temp_folder)
    call(['scrot', temp_out])
    scrot = Image.open(temp_out)
    scrot_w = int(float(scrot.size[0] * 0.1))
    scrot_h = int(float(scrot.size[1] * 0.1))
    scrot.save(temp_out)
    scrot = scrot.resize((scrot_w, scrot_h), Image.BOX)
    scrot_w = int(float(scrot_w * 10))
    scrot_h = int(float(scrot_h * 10))
    scrot = scrot.resize((scrot_w, scrot_h), Image.BOX)
    scrot.save(temp_out)

    if strip:
        if not os.path.exists(strip):
            pass
        else:
            # Change the size of the comic strip
            img = Image.open(strip)
            img_w = int(img.size[0])
            img_h = int(img.size[1])
            new_size = ratio_check(img_w, img_h)
            img_w = new_size[0]
            img_h = new_size[1]
            img = img.resize((img_w, img_h), Image.ANTIALIAS)
            img.convert('RGB').save(strip)
            # Make sure comic is placed on the primary screen
            img_w = img.size[0]
            img_h = img.size[1]
            img_w = img_w // 2
            img_h = img_h // 2
            placement_w = (int(mon_w) // 2) - img_w
            placement_h = (int(mon_h) // 2) - img_h
            scrot.paste(img, (placement_w, placement_h))
            scrot.save(temp_out)
    return temp_out


# Fetch the newest comic
try:
    random = False
    test = False
    test_comic = False
    # Get comic name as argument
    try:
        comic = str(sys.argv[1])
        if comic == 'random':
            random = True
        if comic == 'test':
            test = True
            try:
                test_comic = str(sys.argv[2])
            except:
                pass
    except(IndexError):
        random = True
        comic = 'random'
except:
    # If it can't get comic name as an argument, show error message
    print('Couldn\'t find a comic. Run the script like this \'python {}'
          ' lunch\'.'
          .format(os.path.basename(__file__)))
    _getcomics.print_comic_list()
    sys.exit()

# If run as test, test all the comic fetching
if test:
    if test_comic:
        link = eval('getcomic_{}()'.format(test_comic))
        print('{}: {}'.format(test_comic, link))
    elif test_comic is False:
        false_comics = []
        for comic in _getcomics.comics():
            link = eval('getcomic_{}()'.format(comic))
            if link is not False:
                print('{}: {}'.format(comic, link))
            else:
                false_comics.append(comic)
        if len(false_comics) > 0:
            false_text = 'These comics returned false on the links: '
            for comic in false_comics:
                if comic == false_comics[-1]:
                    false_text += 'and \'{}\'.'.format(comic)
                else:
                    false_text += '\'{}\', '.format(comic)
            print(false_text)
    sys.exit()


# Get the folder for the script
filedir = os.path.dirname(os.path.abspath(__file__))

# Set folder for the images saved by the script
strips_folder = '{}/strips/'.format(filedir)

# Get the link for today's strip as chosen
if random:
    link = _getcomics.comics()[randint(0, len(_getcomics.comics()) - 1)]
else:
    try:
        link = _getcomics.comics(comic)
    except:
        link = False

# Get a listing of the files in 'strips_folder'
strips_files = glob.glob('strips/*.*')
backup_strip = '{}/xkcd.png'.format(filedir)

# Set a backup comic strip, you know, just in case
for file in strips_files:
    if comic in file or random is False:
        backup_strip = '{}/{}'.format(filedir, file)
        break
    else:
        backup_strip = '{}/xkcd_placeholder.png'.format(filedir)

# Set filename for comic strip to be saved
strip = '{}{}-{}.jpg'.format(strips_folder, comic, now)

# Make a failsafe in case it can't fetch a comic strip at all
if link is False:
    strip = backup_strip
else:
    # ...but if all is ok, continue.
    # Check to see if the latest comic is already in place
    if not os.path.exists(strip):
        if not os.path.exists(strips_folder):
            call(['mkdir', strips_folder])
        curl = call(['curl', '-f', link, '-o', strip, '--connect-timeout',
                     '5', '--max-time', '5'])
        # If curl fails in any way, use the latest strip from same
        # comic.
        # Code 6 from curl is 'Could not resolve host'. Not much to
        # do about this, but the script should have a failsafe
        if curl is 6:
            strip = backup_strip
            # Debug
            print('error 6: make backup strip')
        # If curl get code 22 (basically a 404), try previous dates
        if curl == 22:
            # Debug
            print('error 22: 404, check earlier strips')
            i = 0
            while curl is 22:
                i += 1
                link = eval('get_{}(days={})[0]'.format(comic, i))
                now = eval('get_{}(days={})[1]'.format(comic, i))
                strip = '{}{}-{}.jpg'.format(strips_folder, comic, now)
                curl = call(['curl', '-f', link, '-o', strips])
                continue


# Run lock file
call(['i3lock', '-i', scrot(strip)])

# Maintain all the strips: keep max 5 strips at a time
# Make sure that only the images are deleted, not other files/folders
for file in strips_files:
    if '.jpg' not in file:
        strips_files.remove(file)
# Only keep the 5 newest files
if len(strips_files) > 5:
    clean_number = len(strips_files) - 5 - 1
    for i in strips_files[0:clean_number]:
        os.remove(i)