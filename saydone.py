#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
 Authors:
   yifengyou <842056007@qq.com>
"""
import argparse
import os
import datetime
import sys

CURRENT_VERSION = "0.1.0"
PIPE_PATH = "/var/log/saydone"
LOG_PATH = "/var/log/saydone.txt"
DEBUG = False


# PROMPT_COMMAND='if [ -e /var/log/saydone ]; then echo "$? $USER `fc -ln -0`" > /var/log/saydone ; fi'
def check_python_version():
    current_python = sys.version_info[0]
    if current_python == 3:
        return
    else:
        raise Exception('Invalid python version requested: %d' % current_python)


def timestamp():
    utc_time = datetime.datetime.utcnow()
    beijing_tz = datetime.timezone(datetime.timedelta(hours=8))
    beijing_time = utc_time.astimezone(beijing_tz)
    return beijing_time.strftime("%Y/%m/%d %H:%M:%S")


def handle_daemon(args):
    if not os.path.exists(PIPE_PATH):
        os.mkfifo(PIPE_PATH)
        os.chmod(PIPE_PATH, 0o666)
    log_file = open(LOG_PATH, "a")
    # pid = os.fork()
    # if pid == 0:
    while True:
        pipe_file = open(PIPE_PATH, "r")
        content = pipe_file.read()
        pipe_file.close()

        if content:
            content_list = content.split()
            ret = content_list[0]
            user = content_list[1]
            cmd = content_list[2:]
            current_time = timestamp()
            log_file.write(f"ret:{ret} user:{user} time:{current_time} cmd:{cmd}\n")
            log_file.flush()
    # else:
    #     exit(0)
    print(" handle daemon done!")


def handle_stop(args):
    print(" handle stop done!")


def handle_start(args):
    print(" handle start done!")


def main():
    global DEBUG, CURRENT_VERSION
    check_python_version()

    # 顶层解析
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-v", "--version", action="store_true",
                        help="show program's version number and exit")
    parser.add_argument("-h", "--help", action="store_true",
                        help="show this help message and exit")
    subparsers = parser.add_subparsers()

    # 添加子命令 start
    parser_start = subparsers.add_parser('start')
    parser_start.set_defaults(func=handle_start)
    # 添加子命令 stop
    parser_stop = subparsers.add_parser('stop')
    parser_stop.set_defaults(func=handle_stop)
    # 添加子命令 daemon
    parser_daemon = subparsers.add_parser('daemon')
    parser_daemon.set_defaults(func=handle_daemon)

    # 开始解析命令
    args = parser.parse_args()

    if args.version:
        print("saydone %s" % CURRENT_VERSION)
        sys.exit(0)
    elif args.help or len(sys.argv) < 2:
        parser.print_help()
        sys.exit(0)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
