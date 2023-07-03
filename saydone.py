#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
 Authors:
   yifengyou <842056007@qq.com>
"""
import argparse
import os
import datetime
import subprocess
import sys

import select

CURRENT_VERSION = "0.1.0"
PIPE_PATH = "/var/log/saydone"
LOG_PATH = "/var/log/saydone.log"
DEBUG = False


# weixin : https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=f93f7403-bcbd-4053-be85-339a8017601c
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


def check_privilege():
    if os.getuid() == 0:
        return
    else:
        print("superuser root privileges are required to run")
        print(f"  sudo kdev {' '.join(sys.argv[1:])}")
        sys.exit(1)


def handle_daemon(args):
    if not os.path.exists(PIPE_PATH):
        os.mkfifo(PIPE_PATH)
        os.chmod(PIPE_PATH, 0o666)
    log_file = open(LOG_PATH, "a")

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

    print(" handle daemon done!")


def handle_stop(args):
    retcode, _, _ = do_exe_cmd("sudo systemctl stop saydone.service", print_output=True)
    print(f" handle stop done! ret={retcode}")


def handle_start(args):
    retcode, _, _ = do_exe_cmd("sudo systemctl start saydone.service", print_output=True)
    print(f" handle start done! ret={retcode}")


def do_exe_cmd(cmd, print_output=False, shell=False):
    stdout_output = ''
    stderr_output = ''
    if isinstance(cmd, str):
        cmd = cmd.split()
    elif isinstance(cmd, list):
        pass
    else:
        raise Exception("unsupported type when run do_exec_cmd", type(cmd))

    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell)
    while True:
        rlist, _, _ = select.select([p.stdout, p.stderr], [], [], 0.1)
        for f in rlist:
            line = f.readline().decode('utf-8').strip()
            if line:
                if f == p.stdout:
                    if print_output == True:
                        print("STDOUT", line)
                    stdout_output += line + '\n'
                    sys.stdout.flush()
                elif f == p.stderr:
                    if print_output == True:
                        print("STDERR", line)
                    stderr_output += line + '\n'
                    sys.stderr.flush()
        if p.poll() is not None:
            break
    return p.returncode, stdout_output, stderr_output


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
