#!/usr/bin/env python
''' simple python server example; output format supported = html, raw or json '''
import sys
import json
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

import re

import requests

from datetime import datetime,timedelta
import time
import urllib
import HTMLParser

import xml.etree.ElementTree as ET
import sqlite3
import os


FORMATS = ('html','json','raw')
format = FORMATS[0]

def utc2local (utc):
    epoch = time.mktime(utc.timetuple())
    offset = datetime.fromtimestamp (epoch) - datetime.utcfromtimestamp (epoch)
    return utc + offset
    
    
def local_time(ttime,year,month,day):
    match = re.search(r'(.{1,2}):(.{2}) {0,1}(.{2})',ttime)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        ampm = match.group(3)
        if ampm == "pm":
            if hour < 12:
                hour = hour + 12
                hour = hour % 24
        else:
            if hour == 12:
                hour = 0

        utc_dt = datetime(int(year),int(month),int(day),hour,minute,0)
        loc_dt = utc2local(utc_dt)
        ttime = "%02d:%02d" % (loc_dt.hour,loc_dt.minute)
    return ttime

def get_conn():    
    databasePath = 'source.db'  
    
    conn = sqlite3.connect(databasePath, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.execute('PRAGMA foreign_keys = ON')
    conn.row_factory = sqlite3.Row        
    return conn
    
    
def now_next_time(seconds):  
    conn = get_conn()
    c = conn.cursor()

    c.execute('SELECT *, name FROM channels')
    channels = [(row['id'], row['name'], row['icon']) for row in c]

    now = datetime.fromtimestamp(float(seconds))
    total_seconds = time.mktime(now.timetuple())

    items = []
    for (channel_id, channel_name, img_url) in channels:

        c.execute('SELECT start FROM programmes WHERE channel=?', [channel_id])
        programmes = [row['start'] for row in c]
        
        times = sorted(programmes)
        max = len(times)
        less = [i for i in times if i <= total_seconds]
        index = len(less) - 1
        if index < 0:
            continue
        now = times[index]

        c.execute('SELECT * FROM programmes WHERE channel=? AND start=?', [channel_id,now])
        now = datetime.fromtimestamp(now)
        now = "%02d:%02d" % (now.hour,now.minute)
        now_title = c.fetchone()['title']

        next = ''
        next_title = ''
        if index+1 < max: 
            next = times[index + 1]
            c.execute('SELECT * FROM programmes WHERE channel=? AND start=?', [channel_id,next])
            next = datetime.fromtimestamp(next)                
            next = "%02d:%02d" % (next.hour,next.minute)                
            next_title = c.fetchone()['title']

        after = ''
        after_title = ''
        if (index+2) < max:
            after = times[index + 2]
            c.execute('SELECT * FROM programmes WHERE channel=? AND start=?', [channel_id,after])
            after = datetime.fromtimestamp(after)
            after = "%02d:%02d" % (after.hour,after.minute)
            after_title = c.fetchone()['title']

        items.append((channel_id,channel_name,img_url,now,now_title,next,next_title,after,after_title))

    return items
    

    
def listing(channel):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT *, name FROM channels')
    channels = dict((row['id'], (row['name'], row['icon'])) for row in c)
    c.execute("SELECT * FROM programmes WHERE channel=? ORDER BY start, channel", [channel])
    last_day = ''
    items = []
    for row in c:
        channel_id = row['channel']
        (channel_name, img_url) = channels[channel_id]
        title = row['title']
        sub_title = row['sub_title']
        start = row['start']
        date = row['date']
        plot = row['description']
        season = row['series']
        episode = row['episode']
        categories = row['categories']
        
        items.append((channel_id,channel_name,img_url,title,sub_title,start,date,plot,season,episode,categories))
    c.close()
    return items
    
    
def search(programme_name):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT *, name FROM channels')
    channels = dict((row['id'], (row['name'], row['icon'])) for row in c)
    c.execute("SELECT * FROM programmes WHERE LOWER(title) LIKE LOWER(?) ORDER BY start, channel", ['%'+programme_name+'%'])
    last_day = ''
    items = []
    for row in c:
        channel_id = row['channel']
        (channel_name, img_url) = channels[channel_id]
        title = row['title']
        sub_title = row['sub_title']
        start = row['start']
        date = row['date']
        plot = row['description']
        season = row['series']
        episode = row['episode']
        categories = row['categories']
        
        items.append((channel_id,channel_name,img_url,title,sub_title,start,date,plot,season,episode,categories))
    c.close()
    return items
    
    
def channels():
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT *, name FROM channels')
    channels = dict((row['id'], (row['name'], row['icon'])) for row in c)
    return channels

    
class Handler(BaseHTTPRequestHandler):

    #handle GET command
    def do_GET(self):
        if format == 'html':
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.send_header('Content-type','text-html')
            self.end_headers()
            self.wfile.write("body")
        elif format == 'json':
            path = self.path.split('/')
            request = path[1]
            if len(path) > 2:
                arg = path[2]
            else:
                arg = ''
            #print request
            #print arg
            if request == "search":
                items = search(arg)
            elif request == "listing":
                items = listing(arg)
            elif request == "time":
                items = now_next_time(arg)
            elif request == "channels":
                items = channels()                
            #print items
            #if self.path == 
            self.request.sendall(json.dumps(items))
        else:
            self.request.sendall("%s\t%s" %('path', self.path))
        return

        
def run(port=8000):

    print('http server is starting...')

    #ip and port of servrqq
    server_address = ('127.0.0.1', port)
    httpd = HTTPServer(server_address, Handler)
    print('http server is running...listening on port %s' %port)
    httpd.serve_forever()

    
if __name__ == '__main__':
    from optparse import OptionParser
    op = OptionParser(__doc__)
    
    op.add_option("-p", default=8000, type="int", dest="port", help="port #")
    op.add_option("-f", default='json', dest="format", help="format available %s" %str(FORMATS))
    op.add_option("--no_filter", default=True, action='store_false', dest="filter", help="don't filter")
    
    opts, args = op.parse_args(sys.argv)
    
    format = opts.format
    run(opts.port)