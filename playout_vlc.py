#!/usr/bin python3
# -*- coding: utf-8 -*-

import os
from os import listdir
from os.path import isfile, join
import sys, shutil
from subprocess import Popen, PIPE, call
from threading import Thread
import logging
import fnmatch
import json
import socket
from time import sleep, strftime, gmtime
from datetime import datetime, timedelta, time
from jinja2 import Template
import vlc

logging.basicConfig(filename="/home/pi/playout/playout.log", level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d-%b %H:%M:%S')

def check(file):
  proc = Popen("ffprobe -v error -show_format " + file, shell=True, stdout=PIPE, stderr=PIPE)
  proc.wait()
  da = proc.communicate()
  if len(da[0]) > 0:
    rez = -1
    logging.error(str(da[1][:-2])[2:])
  else:
    rez = 1
  return rez

def duration(file):
  proc = Popen("ffprobe -v error -show_streams " + "\"" + file + "\"", shell=True, stdout=PIPE, stderr=PIPE)
  proc.wait()
  da = proc.communicate()
  p = str(da[0])[(str(da[0]).find("duration=") + 9):]
  if p != '':
    p = str(da[0])[(str(da[0]).find("duration=") + 9):]
    p = p[:p.find("\\")]
    fps = str(da[0])[(str(da[0]).find("nb_frames=") + 10):]
    fps = fps[:fps.find("r")-1]
    rez = float(p[:8])
  else:
    rez = -1
  return rez


def NextFile(schedule, id):
    for prog in schedule["program"]:
       if prog["id"] == 0: rez = prog["source"]
       if prog["id"] == id:
          rez = prog["source"]
          break
    return rez

def ScheduleWork(schedule): # заполнение плейлиста
    summ = 0
    i = 0
    for prog in schedule["program"]:
        prog["id"] = i
        i += 1
        if prog["source"].find(".stream") < 0:
           dur = duration(prog["source"])
        else:
           if prog["dur"] == 0:
              sdur = prog["source"][prog["source"].find(".")+1:prog["source"].rfind(".")]
              if sdur != '':
                 dur = int(sdur)*60
              else:
                 dur = 600
           else:
              dur = prog["dur"]*60
           prog["source"] = prog["stream"]
        if dur > 0:
           prog["dur"] = dur
           prog["strdur"] = strftime("%H:%M:%S", gmtime(dur))
           summ += dur
        else:
           prog["dur"] = 0
           prog["strdur"] = strftime("%H:%M:%S", gmtime(0))
    schedule["rotation"] = summ
    return schedule


def Analitic(schedule): # разбор плей лист
    dnow = datetime.now()
    shour = int(schedule["start"][:schedule["start"].find(":")])
    smin = int(schedule["start"][schedule["start"].find(":")+1:schedule["start"].rfind(":")])
    dstart = datetime.combine(dnow, time(shour,smin,0)) # время старта
    rotation = schedule["rotation"]

    if (dstart < dnow):
       dd = (dnow - dstart).seconds
       dd = dd - (dd//rotation)*rotation
    else:
       dd = (dstart - dnow).seconds
       dd = rotation - dd - (dd//rotation)*rotation

    print ("now",dnow.strftime("%H.%M.%S"),"delta",dd)

    return dd

def html_up(schedule): # обновление html
    html = open('/home/pi/playout/templates/index.html').read()
    template = Template(html)
    fhtml = open("/var/www/html/index.html", "w")
    fhtml.write( template.render(items = schedule,  rot = strftime("%H:%M:%S", gmtime(schedule["rotation"]))))
    fhtml.close()

def read_folders(schedule, path):
    files = [f for f in listdir(path) if isfile(join(path, f))]
    i = 0
    for file in sorted(files):
        prog["id"] = i
        i += 1
        if prog["source"].find(".stream") < 0:
           dur = duration(prog["source"])
        else:
           if prog["dur"] == 0:
              sdur = prog["source"][prog["source"].find(".")+1:prog["source"].rfind(".")]
              if sdur != '':
                 dur = int(sdur)*60
              else:
                 dur = 600
           else:
              dur = prog["dur"]*60
           prog["source"] = prog["stream"]
        if dur > 0:
           prog["dur"] = dur
           prog["strdur"] = strftime("%H:%M:%S", gmtime(dur))
           summ += dur
        else:
           prog["dur"] = 0
           prog["strdur"] = strftime("%H:%M:%S", gmtime(0))
    schedule["rotation"] = summ
  return schedule

def main():
  os.system("clear")
  if len(sys.argv) < 2:
      print("Argument is empty")
      print("1. media folders full patch 2. patch to file json ")
      sys.exit()

  logging.info("BEGIN")
  root = sys.argv[1]
  jsonf = sys.argv[2]
  fjson = open(sys.argv[2])
  schedule = json.load(fjson)
  ScheduleWork(schedule)
  html_up(schedule)

  with open('schedule_air.json', 'w') as json_file:
       json.dump(schedule, json_file)

  delay_sch = Analitic(schedule)
  logging.info("START DELAY LOOP " + str(delay_sch))

  Instance = vlc.Instance('--input-repeat=-1 --aout=alsa --alsa-audio-device=plughw:0,0')

  while True:
    logging.info("START LOOP")
    for prog in schedule["program"]:
            DUR = prog["dur"]
            source = prog["source"]
            prog["out"] = 1
            html_up(schedule)
            logging.info("PLAY " + source)
            player = Instance.media_player_new()
            Media = Instance.media_new(source)
            Media_list = Instance.media_list_new([source])
            Media.get_mrl()
            player.set_media(Media)
            if player.play() == -1:
               logging.error(source)
            sleep(DUR-1)
            player.stop()
            prog["out"] = 0

    logging.info("END LOOP")


if __name__ == "__main__":
    main()
