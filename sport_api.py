import hashlib
import json
import os

import requests
from geopy.point import Point

# disable HTTPS warnings as it might encounter certificate verification failure
import urllib3

urllib3.disable_warnings()


def read_arg(arg_name, default=''):
    value = os.getenv(arg_name)
    if value is None or not value.strip():
        # Try loading from settings.json
        try:
            with open('settings.json', 'r', encoding='utf-8') as fp:
                value = json.load(fp)[arg_name]
        except FileNotFoundError:
            print("ERROR: 未导入数据，请检查settings路径")
            exit(1)
        except Exception:
            return default
    return value


def get_routes():
    route_url = 'https://sport.fudan.edu.cn/sapi/route/list'
    params = {'userid': read_arg('USER_ID'),
              'token': read_arg('FUDAN_SPORT_TOKEN')}
    params = sign_param(params)
    data = requests.get(route_url, params=params, verify=False).json()
    try:
        route_data_list = filter(lambda route: route['points'] is not None and len(route['points']) == 1,
                                 data['data']['list'])
        return [FudanRoute(route_data) for route_data in route_data_list]
    except Exception:
        print(f"ERROR: {data['message']}")
        exit(1)


class FudanAPI:
    def __init__(self, route):
        self.route = route
        self.user_id = read_arg('USER_ID')
        self.token = read_arg('FUDAN_SPORT_TOKEN')
        self.system = read_arg('PLATFORM_OS', 'iOS 2016.3.1')
        self.device = read_arg('PLATFORM_DEVICE', 'iPhone|iPhone 13<iPhone14,5>')
        self.run_id = None

    def start(self):
        start_url = 'https://sport.fudan.edu.cn/sapi/run/start'
        params = {'userid': self.user_id,
                  'token': self.token,
                  'route_id': self.route.id,
                  'route_type': self.route.type,
                  'system': self.system,
                  'device': self.device,
                  'lng': self.route.start_point.longitude,
                  'lat': self.route.start_point.latitude}
        params = sign_param(params)
        data = requests.get(start_url, params=params, verify=False).json()
        try:
            self.run_id = data['data']['run_id']
        except Exception:
            print(f"ERROR: {data['message']}")
            exit(1)

    def update(self, point):
        update_url = 'https://sport.fudan.edu.cn/sapi/run/point'
        params = {'userid': self.user_id,
                  'token': self.token,
                  'run_id': self.run_id,
                  'lng': point.longitude,
                  'lat': point.latitude}
        params = sign_param(params)
        try:
            response = requests.get(update_url, params=params, verify=False)
            data = response.json()
            return data['message']
        except requests.RequestException:
            return "Network Error"
        except KeyError:
            return response.text

    def finish(self, point):
        finish_url = 'https://sport.fudan.edu.cn/sapi/run/finish'
        params = {'userid': self.user_id,
                  'token': self.token,
                  'run_id': self.run_id,
                  'system': self.system,
                  'device': self.device,
                  'lng': point.longitude,
                  'lat': point.latitude}
        params = sign_param(params)
        response = requests.get(finish_url, params, verify=False)
        data = json.loads(response.text)
        return data['message']


def sign_param(params):
    keys = sorted(params.keys())
    arr = []
    for k in keys:
        arr.append(str(params[k]))
    vals = ",".join(arr)
    s = "moveclub123123123" + vals
    md5_hash = hashlib.md5()
    md5_hash.update(s.encode('utf-8'))
    params["sign"] = md5_hash.hexdigest()
    return params


class FudanRoute:
    def __init__(self, data):
        self.id = data['route_id']
        self.name = data['name']
        self.type = data['types'][0]
        self.start_point = Point(data['points'][0]['lat'],
                                 data['points'][0]['lng'])

    def pretty_print(self):
        print(f"#{self.id}: {self.name}")
