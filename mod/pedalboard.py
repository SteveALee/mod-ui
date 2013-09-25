
# Copyright 2012-2013 AGR Audio, Industria e Comercio LTDA. <contato@portalmod.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os, json, logging, copy
from datetime import datetime
from bson import ObjectId
from mod.settings import (PEDALBOARD_DIR, PEDALBOARD_INDEX_PATH,
                          INDEX_PATH, EFFECT_DIR, BANKS_JSON_FILE)

from modcommon import json_handler
from mod.bank import remove_pedalboard_from_banks
from mod import indexing

class Pedalboard(object):
    class ValidationError(Exception):
        pass

    def __init__(self, uid=None):
        self.data = None
        self.clear()
        if uid:
            self.load(uid)

    def clear(self):
        self.max_instance_id = -1
        if self.data:
            width = self.data['width']
            height = self.data['height']
        else:
            width = 0
            height = 0
        self.data = {
            '_id': None,
            'metadata': {
                'title': '',
                'tstamp': None,
                },
            'width': width,
            'height': height,
            'instances': {},
            'connections': [],
            }

    def serialize(self):
        serialized = copy.deepcopy(self.data)
        serialized['instances'] = serialized['instances'].values()
        return serialized

    def unserialize(self, data):
        instances = data.pop('instances')
        data['instances'] = {}
        for instance in instances:
            data['instances'][instance['instanceId']] = instance
        self.data = data

    def load(self, uid):
        try:
            fh = open(os.path.join(PEDALBOARD_DIR, str(uid)))
        except IOError:
            logging.error('[pedalboard] Unknown pedalboard %s' % uid)
            return self.clear()
        self.unserialize(json.load(fh))
        fh.close()

    def save(self, title=None, as_new=False):
        if as_new or not self.data['_id']:
            self.data['_id'] = ObjectId()
        if title is not None:
            self.set_title(title)
        
        title = self.data['metadata']['title']

        if not title:
            raise ValidationError("Title cannot be empty")

        index = indexing.PedalboardIndex()
        try:
            existing = index.find(title=title).next()
            assert existing['id'] == unicode(self.data['_id'])
        except StopIteration:
            pass
        except AssertionError:
            raise ValidationError('Pedalboard "%s" already exists' % title)
        
        fh = open(os.path.join(PEDALBOARD_DIR, str(self.data['_id'])), 'w')
        self.data['metadata']['tstamp'] = datetime.now()
        serialized = self.serialize()
        fh.write(json.dumps(serialized, default=json_handler))
        fh.close()

        index = indexing.PedalboardIndex()
        index.add(self.data)

        return self.data['_id']

    def _port_to_list(self, port):
        port = port.split(':')
        if port[0].startswith('effect_'):
            port[0] = port[len('effect_'):]
        try:
            port[0] = int(port[0])
        except ValueError:
            pass
        return port

    def add_instance(self, url, instance_id=None, bypassed=False, x=0, y=0):
        if instance_id is None:
            instance_id = self.max_instance_id + 1
            self.max_instance_id = instance_id
        self.data['instances'][instance_id] = { 'url': url,
                                                'instanceId': instance_id,
                                                'bypassed': bool(bypassed),
                                                'x': x,
                                                'y': y,
                                                'preset': {},
                                                'addressing': {},
                                                }
        return instance_id

    def remove_instance(self, instance_id):
        try:
            self.data['instances'].pop(instance_id)
            return True
        except KeyError:
            logging.error('[pedalboard] Cannot remove unknown instance %d' % instance_id)

    def bypass(self, instance_id, value):
        try:
            self.data['instances'][instance_id]['bypassed'] = bool(value)
            return True
        except KeyError:
            logging.error('[pedalboard] Cannot bypass unknown instance %d' % instance_id)

    def connect(self, port_from, port_to):
        port_from = self._port_to_list(port_from)
        port_to = self._port_to_list(port_to)
        self.data['connections'].append([port_from[0], port_from[1], port_to[0], port_to[1]])

    def disconnect(self, port_from, port_to):
        pf = self._port_to_list(port_from)
        pt = self._port_to_list(port_to)
        # This is O(N). It will hardly be a problem, since it's only called when user is connected
        # and manually disconnects two ports, and number of connections is expected to be relatively small.
        # Anyway, if you're greping TODO, check if optimizing this is one ;-)
        for i, c in enumerate(self.data['connections']):
            if c[0] == pf[0] and c[1] == pf[1] and c[2] == pt[0] and c[3] == pt[1]:
                self.data['connections'].pop(i)
                return True

    def parameter_set(self, instance_id, port_id, value):
        try:
            self.data['instances'][instance_id]['preset'][port_id] = value
            return True
        except KeyError:
            logging.error('[pedalboard] Cannot set parameter %s of unknown instance %d' % (port_id, instance_id))

    def parameter_address(self, instance_id, port_id, addressing_type, label, ctype,
                          unit, current_value, maximum, minimum, steps,
                          hardware_type, hardware_id, actuator_type, actuator_id,
                          options):
        addressing = { 'actuator': [ hardware_type, hardware_id, actuator_type, actuator_id ],
                       'addressing_type': addressing_type,
                       'type': ctype,
                       'unit': unit,
                       'label': label,
                       'minimum': minimum,
                       'maximum': maximum,
                       'value': current_value,
                       'steps': steps,
                       'options': options,
                       }
        self.data['instances'][instance_id][port_id] = addressing

    def parameter_unaddress(self, instance_id, port_id):
        try:
            instance = self.data[instance_id]
        except KeyError:
            logging.error('[pedalboard] Cannot find instance %d to unaddress parameter %s' %
                          (instance_id, port_id))
        try:
            instance.pop(port_id)
        except KeyError:
            logging.error("[pedalboard] Trying to unaddress parameter %s in instance %d, but it's not addressed" %
                          (port_id, instance_id))

    def set_title(self, title):
        self.data['metadata']['title'] = unicode(title)

    def set_size(self, width, height):
        self.data['width'] = width
        self.data['height'] = height

    def set_position(self, instance_id, x, y):
        try:
            self.data['instances'][instance_id]['x'] = x
            self.data['instances'][instance_id]['y'] = y
            return True
        except KeyError:
            logging.error('[pedalboard] Cannot set position of unknown instance %d' % instance_id)
            

def remove_pedalboard(uid):
    # Delete pedalboard file
    fname = os.path.join(PEDALBOARD_DIR, str(uid))
    if not os.path.exists(fname):
        return False
    os.remove(fname)

    # Remove from index
    index = indexing.PedalboardIndex()
    index.delete(uid)

    return remove_pedalboard_from_banks(uid)
