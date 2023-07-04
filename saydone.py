#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
 Authors:
   yifengyou <842056007@qq.com>
"""
import argparse
import json
import os
import datetime
import subprocess
import sys
import multiprocessing
import queue
import requests

import select

CURRENT_VERSION = "0.1.0"
PIPE_PATH = "/var/log/saydone"
LOG_PATH = "/var/log/saydone.log"
DEBUG = False


# weixin : https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=f93f7403-bcbd-4053-be85-339a8017601c
# PROMPT_COMMAND='if [ -e /var/log/saydone ]; then echo "$? $USER `fc -ln -0`" > /var/log/saydone ; fi'

class Wecom():
    """
    企业微信群聊机器人
    官方文档：https://developer.work.weixin.qq.com/document/path/91770
    每个机器人发送的消息不能超过20条/分钟，大概3s一条即可
    """

    def __init__(self, key=None):
        if key is None:
            raise Exception(" wecom api key is None ")
        self._key = key

    def do_send(self, data):
        res = None
        headers = {'Content-Type': 'application/json'}
        url = f'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={self._key}'
        r = requests.post(url=url, headers=headers, data=json.dumps(data))
        # print(r.text)
        try:
            res = json.loads(r.text)
        except:
            pass
        if r.status_code == 200 and res and 'errcode' in res and 0 == res['errcode']:
            print('[+] wecomBot 发送成功')
        else:
            print('[-] wecomBot 发送失败')
            print(r.text)

    def send_markdown(self, msg):
        data = {
            "msgtype": "markdown",
            "markdown": {
                "content": msg,
            },
        }
        self.do_send(data)

    def send_text(self, msg="", mentioned_mobile_list=[]):
        data = {
            "msgtype": "text",
            "text": {
                "content": msg,
                "mentioned_list": [],
                "mentioned_mobile_list": mentioned_mobile_list,
            }
        }
        self.do_send(data)


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
        print(f"  sudo saydone {' '.join(sys.argv[1:])}")
        sys.exit(1)


# 定义一个消费者函数，接受一个队列作为参数
def sender(args):
    q = args.q
    wecom_sender = Wecom(key='f93f7403-bcbd-4053-be85-339a8017601c')
    # 从队列中获取字符串，并发送请求到服务器
    while True:
        msg = q.get()
        print(f"sender got {msg} from queue")
        wecom_sender.send_text(msg=msg)


def creator(args):
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
            info = f"ret:{ret} user:{user} time:{current_time} cmd:{cmd}\n"
            log_file.write(info)
            log_file.flush()
            args.q.put(info)


def handle_daemon(args):
    # 创建一个队列，用于存储生产者和消费者之间的数据
    args.q = multiprocessing.Queue()

    # 创建一个生产者
    p1 = multiprocessing.Process(target=creator, args=(args,))
    # 创建两个消费者进程，并启动它们
    c1 = multiprocessing.Process(target=sender, args=(args,))
    c2 = multiprocessing.Process(target=sender, args=(args,))

    p1.start()
    c1.start()
    c2.start()
    p1.join()
    c1.join()
    c2.join()

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
