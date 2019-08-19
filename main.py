# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import webapp2
import os
import cgi
from google.appengine.ext.webapp import template
from google.appengine.ext import ndb
from google.appengine.api import images
from google.appengine.ext import vendor

vendor.add('lib')

import numpy as np
from PIL import Image
import urllib2
import random
from io import BytesIO
import logging
import mimetypes

COLORS = ["#ece7d9", "#cdbfaa", "#000000", "#f4f3f3", "#f5bfca", "#1963ac", "#4f5457", "#f68d3f", "#9aa9ab", "#24aae1", "#db1280", "#d8cd4a", "#774679", "#288741", "#0d4166", "#92c9d5", "#9fc73c", "#6b232a",
          "#aa8e74", "#052a3f", "#2e3032", "#14b1be", "#ee502a", "#1e3e22", "#652257", "#d92026", "#b72327", "#129e7a", "#3f2c25", "#452971", "#f8bb15", "#00867b", "#6c9d40", "#29358d", "#f8e03a", "#5ca2d8", "#e34f94"]


def convert_color(c1, c2, data):
    # change color c1 to color c2
    (red, green, blue) = data[:, :, 0], data[:, :, 1], data[:, :, 2]
    mask = (red == c1[0]) & (green == c1[1]) & (blue == c1[2])
    data[:, :, :3][mask] = [c2[0], c2[1], c2[2]]
    return data


def hex_to_rgb(hex):
    hex = hex.lstrip('#')
    hlen = len(hex)
    return tuple(int(hex[i:i + int(hlen / 3)], 16) for i in range(0, hlen, int(hlen / 3)))


class Design(ndb.Model):
    filename = ndb.StringProperty()
    image = ndb.BlobProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)

    # def uri2view(self):  # enable get_serving_url
    #     # logging.info(str(images.get_serving_url(
    #     #     self.image.key(), secure_url=True)))
    #     # return
    #     # images.get_serving_url("aghkZXZ-Tm9uZXITCxIGRGVzaWduGICAgICA0LsJDA",
    #     # secure_url=True)
    #     # return str(images.get_serving_url(
    #     #     self.image.key(), secure_url=True))
    #     logging.info("/design_serve/" + str(self.id))
    #     # return "/design_serve/" + str(self.id)
    #     return "https://www.sockclub.com/images/squiggles.bmp"

    @classmethod
    def query_all(cls):
        return cls.query().order(-cls.created)

    @classmethod
    def get_all(cls):
        q = cls.Query()
        q.order('-created')
        return q.fetch(20)


class Colorways(ndb.Model):
    design_url = ndb.StringProperty()
    sock_colorways = ndb.BlobProperty(repeated=True)


class MainPage(webapp2.RequestHandler):

    def get(self):
        designs = Design.query_all()
        home = os.path.join(os.path.dirname(__file__),
                            'templates', "index.html")
        page = template.render(
            home, {'show_colorways': False, 'designs': designs})
        self.response.out.write(page)

    def post(self):
        designs = Design.query_all()
        design = cgi.escape(self.request.get('design'))
        file = BytesIO(
            urllib2.urlopen(design).read())
        im = Image.open(file)
        im = im.convert('RGB')
        init_colors = im.getcolors()
        orig_sock = np.array(im)
        new_sock = orig_sock.copy()
        colors_array = []
        socks_array = []

        for i in range(37):
            for c in init_colors:
                # print colors_array
                rindex = random.randint(0, 36)
                if rindex not in colors_array:
                    colors_array.append(rindex)
                    if not (c == (255, 255, 255)):
                        new_sock = convert_color(
                            c[1], hex_to_rgb(COLORS[rindex]), new_sock)
            new_im = Image.fromarray(new_sock)
            bitmap = BytesIO()
            new_im.save(bitmap, "PNG")
            image_bytes = bitmap.getvalue()
            socks_array.append(image_bytes)
            colors_array = []
            new_sock = orig_sock.copy()

        colorways = Colorways(design_url=design, sock_colorways=socks_array)
        colorways_key = colorways.put()

        home = os.path.join(os.path.dirname(__file__),
                            'templates', "index.html")
        page = template.render(
            home, {'colorways_id': colorways_key.id(), 'show_colorways': True, 'designs': designs})
        self.response.out.write(page)


class ArgyleBitmapBuilderPage(webapp2.RequestHandler):

    def get(self):
        # cgi.escape(self.request.get('username'))
        # template_id = cgi.escape(self.request.get('template_id'))

        bb = os.path.join(os.path.dirname(__file__),
                          'templates', "bitmap_builder.html")
        page = template.render(bb, {})
        self.response.out.write(page)


class FileUpload(webapp2.RequestHandler):

    def post(self):
        file_upload = self.request.POST.get("file", None)
        filename = file_upload.filename
        design = Design(filename=filename,
                        image=file_upload.file.read())
        design.put()

        self.redirect('/')


class ImgServe(webapp2.RequestHandler):

    def get(self, colorways_id, sock_id):
        logging.info('This is the sock id: ' + sock_id)
        colorways = Colorways.get_by_id(int(colorways_id))
        self.response.headers['Content-Type'] = "image/png"
        self.response.write(colorways.sock_colorways[int(sock_id)])


class DesignServe(webapp2.RequestHandler):

    def get(self, resource):

        # design = ndb.Key('Design', resource).get()
        design = Design.get_by_id(int(resource))
        # design = Design.get(resource)
        self.response.headers[
            b'Content-Type'] = mimetypes.guess_type(design.filename)[0]
        self.response.write(design.image)

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/bitmap_builder', ArgyleBitmapBuilderPage),
    webapp2.Route(r'/img_serve/<colorways_id:\d+>/<sock_id:\d+>',
                  handler=ImgServe),
    webapp2.Route(r'/file_upload', handler=FileUpload),
    webapp2.Route(r'/design_serve/<resource:(.*)>', handler=DesignServe)
], debug=True)