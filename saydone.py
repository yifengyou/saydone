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
import requests
import logging
import select

CURRENT_VERSION = "0.1.0"
PIPE_PATH = "/var/log/saydone"
LOG_PATH = "/var/log/saydone.log"

# 创建一个日志对象，设置日志级别和格式
logger = logging.getLogger("producer_consumer")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# 创建一个文件处理器，将日志输出到文件中
file_handler = logging.FileHandler(LOG_PATH)
file_handler.setFormatter(formatter)
# 将文件处理器添加到日志对象中
logger.addHandler(file_handler)


# weixin : https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=f93f7403-bcbd-4053-be85-339a8017601c

# # 定义一个函数，将上一条命令的返回值写入一个文件
# function save_exit_status() {
#   RET=$?
#   if [ -e /var/log/saydone ]; then
#         echo "$RET $USER `fc -ln -0`" > /var/log/saydone
#   fi
#   return $RET
# }
#
# # 将该函数赋给PROMPT_COMMAND变量，使其在每个提示符之前执行
# PROMPT_COMMAND=save_exit_status



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
            logger.info('[+] wecomBot 发送成功')
        else:
            logger.info('[-] wecomBot 发送失败')
            logger.info(r.text)

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


def beijing_timestamp():
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


def msg_sender(args):
    q = args.q
    wecom_sender = Wecom(key='f93f7403-bcbd-4053-be85-339a8017601c')
    while True:
        msg = q.get()

        msg_list = msg.split()
        retcode = msg_list[0]
        runuser = msg_list[1]
        cmdline = " ".join(msg_list[2:])
        timestamp = beijing_timestamp()
        format_msg = f"saydone消息播报:\n命令 : {cmdline}\n返回值 : {retcode}\n执行用户 : {runuser}\n结束时间 : {timestamp}"

        wecom_sender.send_text(msg=format_msg)
        logger.info(f"msg_sender send: \n{format_msg}")

        q.task_done()


def msg_creator(args):
    if not os.path.exists(PIPE_PATH):
        os.mkfifo(PIPE_PATH)
        os.chmod(PIPE_PATH, 0o666)

    while True:
        pipe_file = open(PIPE_PATH, "r")
        content = pipe_file.read()
        pipe_file.close()
        args.q.put(content)
        logger.info(f"msg_create created : {content}")


def handle_daemon(args):
    # 创建一个队列，用于存储生产者和消费者之间的数据
    args.q = multiprocessing.JoinableQueue()

    p1 = multiprocessing.Process(target=msg_creator, args=(args,))

    # 创建消费者进程
    c1 = multiprocessing.Process(target=msg_sender, args=(args,))
    c2 = multiprocessing.Process(target=msg_sender, args=(args,))

    p1.start()
    c1.start()
    c2.start()

    args.q.join()


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
    global CURRENT_VERSION
    check_python_version()

    # 顶层解析
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "-v", "--version",
        action="store_true",
        help="show program's version number and exit"
    )
    parser.add_argument(
        "-h", "--help",
        action="store_true",
        help="show this help message and exit"
    )
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
