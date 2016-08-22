#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
import re
import urllib
import urllib2
import cookielib
import random
import mimetypes
import json
import string
from threading import Timer

_BOUNDARY_CHARS = string.digits + string.ascii_letters

_HOME_INDEX = None

class SmartRedirectHandler(urllib2.HTTPRedirectHandler):
    def http_error_301(self, req, fp, code, msg, headers):
        result = urllib2.HTTPRedirectHandler.http_error_301(
            self, req, fp, code, msg, headers)
        result.status = code
        return result
    
    def http_error_302(self, req, fp, code, msg, headers):
        result = urllib2.HTTPRedirectHandler.http_error_302(
            self, req, fp, code, msg, headers)
        result.status = code
        loc = headers['Location']

        if loc.find('index.htm') >= 0:
            _HOME_INDEX = loc
        return result

def read(path):
    sites = []
    with open(path) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            sites.append(row)

    return sites

def save(path, sites):
    with open(path, 'w') as csvfile:
        fields = ['host', 'user', 'pass']
        writer = csv.DictWriter(csvfile, fieldnames = fields)

        writer.writeheader()
        for s in sites:
            writer.writerow({'host': s['host'], 'user': s['user'], 'pass': s['pass']})

def resetDefault():
    sites = [
        {
            'host': 'bxw2341600071.my3w.com',
            'user': 'bxw2341600071',
            'pass': 'a1dsa322f'
        },
        {
            'host': 'bxw2341600035.my3w.com',
            'user': 'bxw2341600035',
            'pass': 'admin888'
        }
    ]

    save('sites.csv', sites)

def defaultHeaders():
    headers = {}
    headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.65 Safari/537.36'
    headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    headers['Accept-Language'] = 'zh-CN,zh;q=0.8,en;q=0.6,zh-TW;q=0.4'
    headers['Connection'] = 'keep-alive'
    headers['Cache-Control'] = 'no-cache'
    headers['Pragma'] = 'no-cache'
    return headers

def encode_multipart(fields, files, boundary=None):
    r"""Encode dict of form fields and dict of files as multipart/form-data.
    Return tuple of (body_string, headers_dict). Each value in files is a dict
    with required keys 'filename' and 'content', and optional 'mimetype' (if
    not specified, tries to guess mime type or uses 'application/octet-stream').

    >>> body, headers = encode_multipart({'FIELD': 'VALUE'},
    ...                                  {'FILE': {'filename': 'F.TXT', 'content': 'CONTENT'}},
    ...                                  boundary='BOUNDARY')
    >>> print('\n'.join(repr(l) for l in body.split('\r\n')))
    '--BOUNDARY'
    'Content-Disposition: form-data; name="FIELD"'
    ''
    'VALUE'
    '--BOUNDARY'
    'Content-Disposition: form-data; name="FILE"; filename="F.TXT"'
    'Content-Type: text/plain'
    ''
    'CONTENT'
    '--BOUNDARY--'
    ''
    >>> print(sorted(headers.items()))
    [('Content-Length', '193'), ('Content-Type', 'multipart/form-data; boundary=BOUNDARY')]
    >>> len(body)
    193
    """
    def escape_quote(s):
        return s.replace('"', '\\"')

    if boundary is None:
        boundary = ''.join(random.choice(_BOUNDARY_CHARS) for i in range(30))
    lines = []

    for name, value in fields.items():
        lines.extend((
            '--{0}'.format(boundary),
            'Content-Disposition: form-data; name="{0}"'.format(escape_quote(name)),
            '',
            str(value),
        ))

    for name, value in files.items():
        filename = value['filename']
        if 'mimetype' in value:
            mimetype = value['mimetype']
        else:
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        lines.extend((
            '--{0}'.format(boundary),
            'Content-Disposition: form-data; name="{0}"; filename="{1}"'.format(
                    escape_quote(name), escape_quote(filename)),
            'Content-Type: {0}'.format(mimetype),
            '',
            value['content'],
        ))

    lines.extend((
        '--{0}--'.format(boundary),
        '',
    ))
    body = '\r\n'.join(lines)

    headers = {
        'Content-Type': 'multipart/form-data; boundary={0}'.format(boundary),
        'Content-Length': str(len(body)),
    }

    return (body, headers)

def recognizeCaptcha(opener, imgUrl, imgFile):
    try:
        img = opener.open(imgUrl).read()
        f = open(imgFile, 'w')
        f.write(img)

        files = {'image': {'filename': 'captcha.jpg', 'content': img}}
        postData = {
                'username': 'hishopx',
                'password': 'mspbot@hishop',
                'typeid': '3090',
                'softid': '41173',
                'softkey': 'e40456c7e29f47218116229ed0bda2b9',
                }

        url = 'http://api.ruokuai.com/create.json'
        data, headers = encode_multipart(postData, files)
        request = urllib2.Request(url = url, data = data, headers = headers)
        
        html = urllib2.urlopen(request).read()
        js = json.loads(html)

        s = json.dumps(js, indent=2)

        if not js['Result']:
            return None

        return js['Result']
    except urllib2.URLError as e:
        return None

def postAnswer(opener, data):
    headers = defaultHeaders()
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
#    headers[':authority'] = 'breakserver.hichina.com'
#    headers[':method'] = 'POST'
#    headers[':path'] = '/answer'
#    headers[':scheme'] = 'https'
    headers['origin'] = 'https://breakserver.hichina.com'
    #headers['referer'] = _HOME_INDEX
    headers['upgrade-insecure-requests'] = '1'

    url = 'https://breakserver.hichina.com/answer'
    request = urllib2.Request(url = url, data = urllib.urlencode(data), headers = headers)
    html = opener.open(request).read()
    r = re.search(r'id="ImageYZM".+onclick="reloadcode\(\);"', html)
    if (r):
        print '>>> 验成失败，稍候重试！'
        return False

    print '>>> 验成成功！'
    return True

def openHomepage(url, username, password):
    jar = cookielib.CookieJar()
    opener = urllib2.build_opener(
        urllib2.HTTPCookieProcessor(jar),
        SmartRedirectHandler()
    )

    print '尝试访问：' + url

    headers = defaultHeaders()
    request = urllib2.Request(url = url, headers = headers)
    html = opener.open(request).read()
    r = re.search(r'id="ImageYZM".+onclick="reloadcode\(\);"', html)
    if (not r):
        print '>>> 站点正常！'
        return False
   
    fields = {}
    matches = re.finditer(r'input type="hidden" name="(.+)" value="(.+)"', html)
    for m in matches:
        fields[m.group(1)] = m.group(2)

    reg = r'type="hidden" id="username"  name="username" class="DuserName" value="(.+)"'
    r = re.search(reg, html)
    fields['username'] = r.group(1)
    fields['password'] = password
    fields['btnSubmit.x'] = int(random.uniform(1, 136))
    fields['btnSubmit.y'] = int(random.uniform(1, 44))

    codeUrl = 'https://breakserver.hichina.com/drawVerifyCode?' + random.random()

    code = None
    for i in range(3):
        code = recognizeCaptcha(opener, codeUrl, 'code.jpg')
        if (code):
            break

    if (not code):
        return False
    
    print '>>> 图片验证码：' + code
    fields['verify_code'] = code

    return postAnswer(opener, fields);

def monitor():
    sites = read('sites.csv')
    for s in sites:
        openHomepage('http://' + s['host'], s['user'], s['pass'])

    print '15秒后再次检测...\n'
    Timer(15.0, monitor).start()

if __name__ == '__main__':
    #resetDefault();
    monitor()
