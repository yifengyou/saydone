#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
 Authors:
   yifengyou <842056007@qq.com>
"""

import os
import datetime

# 有名管道的路径
PIPE_PATH = "/var/log/saydone"
LOG_PATH = "/var/log/saydone.txt"


# PROMPT_COMMAND='if [ -e /var/log/saydone ]; then echo "$? $USER `fc -ln -0`" > /var/log/saydone ; fi'

def timestamp():
    utc_time = datetime.datetime.utcnow()
    beijing_tz = datetime.timezone(datetime.timedelta(hours=8))
    beijing_time = utc_time.astimezone(beijing_tz)
    return beijing_time.strftime("%Y/%m/%d %H:%M:%S")


if __name__ == "__main__":
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
