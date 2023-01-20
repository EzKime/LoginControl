from phBot import *
import time
import struct
import sqlite3
from datetime import datetime
from datetime import timedelta

pName = 'Login Control English'
pVersion = '0.0.6'

"""
stage 1=If it doesn't queue after the first 35 tries, it takes a 60-minute break.
stage 2=If it can't queue after 70 tries, it will go to sleep mode for 24 hours. If the number of rows drops below 850, it will be awakened.
stage 3=If it is blocked by the server, it will be blocked for 24 hours. in this case if he keeps trying the ip will be blocked
"""

userName = get_startup_data()['username']
query = ("""SELECT * FROM LoginControl WHERE userName='%s'""" % userName)
maxCount = 99
minSec = 60
block1 = 60
block24 = 1440
dataBase = get_config_dir() + "AccountLoginControl.db3"
con = sqlite3.connect(dataBase)
cur = con.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS "LoginControl" ("Id" INTEGER NOT NULL, "userName" TEXT NOT NULL,"loginCount" INTEGER NOT NULL,"blockingTime" TEXT,"blockType" INTEGER,"blockCount" INTEGER,"MaxQueue" INTEGER,"logCount" INTEGER,PRIMARY KEY("Id"))')
con.commit()
con.close()

def connected():
    conn = sqlite3.connect(dataBase)
    curs = conn.cursor()
    curs.execute(query)
    accData = curs.fetchone()
    blockType = accData[4]
    blockCount = accData[5]
    dateTime =  datetime.now()
    blockingTime = datetime.fromisoformat(accData[3])
    if blockType == 1 and blockCount == 1 and blockingTime > dateTime:
        minutes = int((blockingTime - dateTime).seconds / minSec)
        countDown(minutes, blockCount)
    elif blockType == 1 and blockCount == 2 and blockingTime > dateTime:
        minutes = int((blockingTime - dateTime).seconds / minSec)
        countDown(minutes, blockCount)
    elif blockType == 1 and blockCount == 1 and blockingTime < dateTime:
        unBlock()
    elif blockType == 1 and blockCount == 2 and blockingTime < dateTime:
        reset()
    elif blockCount == 3 and blockingTime > dateTime:
        minutes = int((blockingTime - dateTime).seconds / minSec)
        countDown(minutes, blockCount)
    elif blockCount == 3 and blockingTime < dateTime:
        reset()
def countDown(minutes, blockCount):
    log(f' The {minutes}-minute countdown begins..')
    log(str(blockCount)+' reason for blocking.')
    if minutes <= 2880 and blockCount >= 2:
        while range(minutes):
            dateTime = datetime.now()
            conn = sqlite3.connect(dataBase)
            curs = conn.cursor()
            curs.execute(query)
            userData = curs.fetchone()
            if userData[6] > 0 and userData[5] != 3:
                curs.execute("Update LoginControl Set loginCount = '%s', blockingTime = '%s', blockType = %s, blockCount = %s, MaxQueue = %s  WHERE userName='%s' " % (30, dateTime, 0, 1, 0, userName))
                conn.commit()
                conn.close()
                log('>>>Reconnect on disconnect<<< must be active')
                log("There was a sudden drop in the server status. 5 attempts can be made. If the queue is not entered, it will be put back to sleep for 24 hours.")
                break
            minutes -= 1
            log(f"It will be unblocked after {minutes} minutes. block reason {blockCount}")
            time.sleep(minSec)
            if minutes < 1:
                reset()
    elif minutes <= 120 and blockCount == 1:
        while range(minutes):
            dateTime = datetime.now()
            conn = sqlite3.connect(dataBase)
            curs = conn.cursor()
            curs.execute(query)
            userData = curs.fetchone()
            if userData[6] > 0 and userData[5] != 3:
                curs.execute("Update LoginControl Set loginCount = '%s', blockingTime = '%s', blockType = %s, blockCount = %s, MaxQueue = %s  WHERE userName='%s' " % (30, dateTime, 0, 1, 0, userName))
                conn.commit()
                conn.close()
                log('>>>Reconnect on disconnect<<< must be active')
                log('There was a sudden drop in the server status. 5 attempts can be made. If the queue is not entered, it will be put to sleep for 60 minutes again.')
                break
            minutes -= 1
            log(f"It will be unblocked after {minutes} minutes. block reason {blockCount}")
            time.sleep(minSec)
            if minutes < 1:
                unBlock()

def unBlock():
    dateTime = datetime.now()
    conn = sqlite3.connect(dataBase)
    curs = conn.cursor()
    curs.execute("Update LoginControl Set loginCount = %s, blockingTime = '%s', blockType=%s, MaxQueue=%s  WHERE userName='%s' " % (0, dateTime, 0, 0, userName))
    conn.commit()
    conn.close()
    log('The countdown is over.')


def reset():
    dateTime = datetime.now()
    conn = sqlite3.connect(dataBase)
    curs = conn.cursor()
    curs.execute("Update LoginControl Set loginCount = %s, blockingTime = '%s', blockType=%s, blockCount=%s, MaxQueue=%s, logCount =%s  WHERE userName='%s' " % (0, dateTime, 0, 0, 0, 0, userName))
    conn.commit()
    conn.close()
    log('The character has entered the game. Status Reset.')

def block24h():
    blockingTime = datetime.now() + timedelta(minutes=block24)
    conn = sqlite3.connect(dataBase)
    curs = conn.cursor()
    curs.execute("Update LoginControl Set blockingTime = '%s', blockCount=%s WHERE userName='%s' " % (blockingTime, 3, userName))
    conn.commit()
    conn.close()
    log('The account has been blocked by the server. 24 hours blocked. Block reason 3')

def updateAccount():
    dateTime = datetime.now()
    conn = sqlite3.connect(dataBase)
    curs = conn.cursor()
    curs.execute(query)
    userData = curs.fetchone()
    # If the record is entered for the first time, it will be entered here.
    if userData is None:
        sql = "INSERT into LoginControl(userName, loginCount, blockingTime, blockType, blockCount, MaxQueue, logCount) VALUES (?,?,?,?,?,?,?)"
        val = (userName, 1, dateTime, 0, 0, 0, 1)
        curs.execute(sql, val)
        conn.commit()
        conn.close()
        log("Character information has been successfully added to the database")
    elif userData[2] >= maxCount:
        blockCount = userData[5]
        if blockCount == 0:
            blockingTime = datetime.now() + timedelta(minutes=block1)
            curs.execute("Update LoginControl Set blockingTime = '%s', blockType=%s, blockCount=%s  WHERE userName='%s' " % (blockingTime, 1, 1, userName))
            conn.commit()
            conn.close()
            log(f'The attempt to enter the queue failed. Queue attempt reached {userData[2]}, temporarily blocked for 60 minutes. If there is a sudden drop in the server, 5 attempts will be given if the Queue is <850.')
        elif blockCount == 1:
            blockingTime = datetime.now() + timedelta(minutes=block24)
            curs.execute("Update LoginControl Set blockingTime = '%s', blockType=%s, blockCount=%s  WHERE userName='%s' " % (blockingTime, 1, 2, userName))
            conn.commit()
            conn.close()
            log(f'The attempt to enter the queue failed. This is the 2nd try. Queue attempt reached {userData[2]}, temporarily blocked for 1440 minutes. If there is a sudden drop in the server, 5 attempts will be given if the Queue is <850.')
    elif userData[2] < maxCount:
        loginCount = userData[2]
        logCount = userData[7]
        blockCount = userData[5]
        loginCount += 1
        logCount += 1
        log(f'Queuing attempt {loginCount} will be stopped when attempt {maxCount} is reached. This is stage {blockCount+1}. Total attempts {logCount}')
        curs.execute("Update LoginControl Set loginCount = %s, logCount=%s WHERE userName='%s' " % (loginCount, logCount, userName))
        conn.commit()
        conn.close()

def handle_joymax(opcode, data):
    bloke =  'Your account is blocked for 24 hours due to repeated login attempts. Please try again when your account is unblocked.'
    bloke24 = str(data)
    if opcode == 0xA10A and bloke in bloke24:
        log('You have been blocked by the server for 24 hours. :( ')
        block24h()
    elif opcode == 0xA10A and data == b'\x02\x1c':
        updateAccount()
    # When the character logs into the game.
    elif opcode == 0xA103 and data == b'\x01\x03\x00':
        reset()
    '''
    elif opcode == 0x210E:
        if data[0] == 1:
            Index = 1
            MaxQueue = struct.unpack_from('<H', data, Index)[0]
            if MaxQueue <= 850:
                dataBase2 = get_config_dir() + "AccountLoginControl.db3"
                conn = sqlite3.connect(dataBase2)
                curs = conn.cursor()
                curs.execute("Update LoginControl Set MaxQueue = %s WHERE blockType=%s and blockCount > %s and blockCount < %s " % (1, 1, 0, 3))
                conn.commit()
                conn.close()
                log('It started to wake up from sleep...Queue attempt Queue < 850 Stage 1 and 2 will be awakened.')
    '''
    return True

log(f'Plugin: {pName} Version {pVersion} Loaded')
