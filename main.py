#!/usr/bin/python
# -*- coding: utf-8 -*-

import getopt
import sys

from balancer import Balancer


def main(argv):
    # import random
    # import string
    # import requests
    # from dateutil import parser
    # from application.api.common import Endpoints
    #
    # seed = ''.join(random.choices(string.digits, k=18))
    # url = Endpoints.Endpoint + '/cmd' + '?randomseed={seed}'.format(seed=seed)
    # data = {'Command': 'ServerState'}
    # response = requests.post(url=url, json=data)
    # if response.status_code == 200:
    #     data = response.json()
    #     return parser.parse(data.get('Timestamp'))
    # else:
    #     pass
    #     # return datetime.now(pytz.timezone('Europe/Kiev'))
    debug = False

    try:
        opts, args = getopt.getopt(argv, "hd", [])
    except getopt.GetoptError:
        print('main.py (-d)')
        sys.exit(2)

    try:
        for opt, arg in opts:
            if opt == '-d':
                debug = True
                Balancer(debug=debug).create_application()
                return 0

            if opt == '-h':
                print('main.py (-d)')
                sys.exit()
    except Exception as error:
        print(error)
        sys.exit(2)

    Balancer(debug=debug).run()


if __name__ == '__main__':
    main(sys.argv[1:])
