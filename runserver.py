#!/usr/bin/env python

#-----------------------------------------------------------------------
# runserver.py
# Author: Bryan Wang, Joanna Tang, Joseph Xu
#-----------------------------------------------------------------------

from sys import argv, exit, stderr
from verbatims import app

def main():

    if len(argv) != 2:
        print('Usage: ' + argv[0] + ' port', file=stderr)
        exit(1)

    try:
        port = int(argv[1])
    except Exception:
        print('Port must be an integer.', file=stderr)
        exit(1)

    try:
        app.run(host='0.0.0.0', port=port, debug=True, ssl_context='adhoc')
    except Exception as ex:
        print(ex, file=stderr)
        exit(1)

if __name__ == '__main__':
    main()
