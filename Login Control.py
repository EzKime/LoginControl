from phBot import *
import time
import struct
import sqlite3
from datetime import datetime
from datetime import timedelta

pName = 'Login Control'
pVersion = '0.0.1'

"""
1=If it doesn't queue after the first 35 tries, it takes a 60-minute break.
2=If it can't queue after 70 tries, it will go to sleep mode for 24 hours. If the number of rows drops below 850, it will be awakened.
3=If it is blocked by the server, it will be blocked for 24 hours. in this case if he keeps trying the ip will be blocked
"""
maxCount = 35
userName = get_startup_data()['username']
query = ("""SELECT * FROM LoginControl WHERE userName='%s'""" % userName)

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
        minutes = int((blockingTime - dateTime).seconds / 60)
        countDown(minutes, blockCount)
    elif blockType == 1 and blockCount == 2 and blockingTime > dateTime:
        minutes = int((blockingTime - dateTime).seconds / 60)
        countDown(minutes, blockCount)
    elif blockType == 1 and blockCount == 1 and blockingTime < dateTime:
        unBlock()
    elif blockType == 1 and blockCount == 2 and blockingTime < dateTime:
        reset()
    elif blockCount == 3 and blockingTime > dateTime:
        minutes = int((blockingTime - dateTime).seconds / 60)
        countDown(minutes, blockCount)
    elif blockCount == 3 and blockingTime < dateTime:
        reset()
def countDown(minutes, blockCount):
    log(str(minutes)+' Dakika geri sayım başlıyor.')
    log(str(blockCount)+' bloke nedeni.')
    if minutes <= 1440 and blockCount >= 2:
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
                log("Sunucu durumunda ani bir dusus yasandi 5 deneme yapilabilir siraya girilmezse ise tekrardan 24 saat uyutulacak")
                break
            minutes -= 1
            log(f"{minutes} Dakika sonra bloke kaldirilacak block nedeni {blockCount}")
            time.sleep(60)
            if minutes < 1:
                reset()
    elif minutes <= 60 and blockCount == 1:
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
                log('Sunucu durumunda ani bir dusus yasandi 5 deneme yapilabilir siraya girilmezse ise tekrardan 60 dakika uyutulacak')
                break
            minutes -= 1
            log(f"{minutes} Dakika sonra bloke kaldirilacak block nedeni {blockCount}")
            time.sleep(60)
            if minutes < 1:
                unBlock()

def unBlock():
    dateTime = datetime.now()
    conn = sqlite3.connect(dataBase)
    curs = conn.cursor()
    curs.execute("Update LoginControl Set loginCount = %s, blockingTime = '%s', blockType=%s, MaxQueue=%s  WHERE userName='%s' " % (0, dateTime, 0, 0, userName))
    conn.commit()
    conn.close()
    log('Geri sayım bitti.')


def reset():
    dateTime = datetime.now()
    conn = sqlite3.connect(dataBase)
    curs = conn.cursor()
    curs.execute("Update LoginControl Set loginCount = %s, blockingTime = '%s', blockType=%s, blockCount=%s, MaxQueue=%s, logCount =%s  WHERE userName='%s' " % (0, dateTime, 0, 0, 0, 0, userName))
    conn.commit()
    conn.close()
    log('Karakter oyuna giriş yaptı. Durum Sıfırlandı.')

def block24h():
    blockingTime = datetime.now() + timedelta(minutes=1440)
    conn = sqlite3.connect(dataBase)
    curs = conn.cursor()
    curs.execute("Update LoginControl Set blockingTime = '%s', blockCount=%s WHERE userName='%s' " % (blockingTime, 3, userName))
    conn.commit()
    conn.close()
    log('Hesap 24 saat bloke edildi.')
    countDown(1440, 3)

def updateAccount():
    dateTime = datetime.now()
    conn = sqlite3.connect(dataBase)
    curs = conn.cursor()
    curs.execute(query)
    userData = curs.fetchone()
    # ilk defa kayit girilecekse buraya girilecek
    if userData is None:
        sql = "INSERT into LoginControl(userName, loginCount, blockingTime, blockType, blockCount, MaxQueue, logCount) VALUES (?,?,?,?,?,?,?)"
        val = (userName, 1, dateTime, 0, 0, 0, 1)
        curs.execute(sql, val)
        conn.commit()
        conn.close()
        log("Karakter Bilgileri Başarıyla Eklendi")
    elif userData[2] >= maxCount:
        blockCount = userData[5]
        if blockCount == 0:
            blockingTime = datetime.now() + timedelta(minutes=60)
            curs.execute("Update LoginControl Set blockingTime = '%s', blockType=%s, blockCount=%s  WHERE userName='%s' " % (blockingTime, 1, 1, userName))
            conn.commit()
            conn.close()
            log(f'Sıraya girme demesi başarısız. Kuyruk Denemesi {userData[2]} ulastıştı 60 dakika engellendi.')
            countDown(60, 1)
        elif blockCount == 1:
            blockingTime = datetime.now() + timedelta(minutes=1440)
            curs.execute("Update LoginControl Set blockingTime = '%s', blockType=%s, blockCount=%s  WHERE userName='%s' " % (blockingTime, 1, 2, userName))
            conn.commit()
            conn.close()
            log(f'Kuyruk Denemesi {userData[2]} ulastıştı bu 2. deneme 1440 dakika engellendi eger kuyruk 700 anltina duserse uyandirilacak')
            countDown(1440, 2)
    elif userData[2] < maxCount:
        loginCount = userData[2]
        logCount = userData[7]
        blockCount = userData[5]
        loginCount += 1
        logCount += 1
        log(f'Sıraya girme denemesi {loginCount} Deneme {maxCount} ulasinca deneme durdurulacak. bu {blockCount}. tur. Toplam deneme {logCount}')
        curs.execute("Update LoginControl Set loginCount = %s, logCount=%s WHERE userName='%s' " % (loginCount, logCount, userName))
        conn.commit()
        conn.close()



def handle_joymax(opcode, data):
    bloke =  'Your account is blocked for 24 hours due to repeated login attempts. Please try again when your account is unblocked.'
    bloke24 = str(data)
    if opcode == 0xA10A and bloke in bloke24:
        log('24 Saat Bloke edildin... :( ')
        block24h()
    elif opcode == 0xA10A and data == b'\x02\x1c':
        updateAccount()
    # login olunca char listesi geliyor 45063
    elif opcode == 0xA103 and data == b'\x01\x03\x00':
        reset()
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
                log('Uykudan uyandırma başladı...')
    return True

log(f'Plugin: {pName} Version {pVersion} Loaded')
