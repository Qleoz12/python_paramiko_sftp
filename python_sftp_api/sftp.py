#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time         : 2021/2/1 14:52
# @Author       : xwh
# @File         : file.py
# @Description  : 带进度的文件分发 支持密码 私钥文件 私钥字符串 另外定期检查文件是否过期 过期删除
import mimetypes
import os
import tempfile
import zipfile
from functools import partial
from hashlib import md5
from io import BytesIO
from os.path import getsize
import time
from tempfile import SpooledTemporaryFile

from fastapi import UploadFile

from python_sftp_api.FileDeliverHost import FileDeliverHost
from loguru import logger as log
from stat import S_IMODE, S_ISDIR, S_ISREG
from fastapi.responses import FileResponse,StreamingResponse


def file_callback(host, remote_path, c, t):
    # redis.hset("file_deliver", "%s_%s" % (host, remote_path), value="%2.f" % ((c / t) * 100))
    log.info(str(c), str(t))
    #
    log.info("%.2f %%" % ((c / t) * 100))

def mkdir_p(sftp, remote_directory):
    """Change to this directory, recursively making new folders if needed.
    Returns True if any folders were created."""
    if remote_directory == '/':
        # absolute path so change directory to root
        sftp.chdir('/')
        return
    if remote_directory == '':
        # top-level relative directory must exist
        return
    try:
        sftp.chdir(remote_directory) # sub-directory exists
    except IOError:
        dirname, basename = os.path.split(remote_directory.rstrip('/'))
        mkdir_p(sftp, dirname) # make parent directories
        sftp.mkdir(basename) # sub-directory missing, so created it
        sftp.chdir(basename)
        return True

def task(host_info, file: UploadFile, fileSize, remote_path, callback):
    client = FileDeliverHost(host_info["host"], user=host_info["user"],pwd=host_info["pwd"], pkey=host_info["pkey"])
    mkdir_p(client.sftp,remote_path)
    print(file.file.tell())
    file.file.seek(0)
    print(file.file.tell())
    sftpproperteies = client.sftp.putfo(file.file, os.path.join(remote_path+"/"+file.filename),fileSize, callback=callback)
    log.info(host_info["host"] + " done")
    log.info("close connect host=%s, pwd=%s" % (host_info["host"], md5sum(host_info["pwd"])))

def task0(host_info, file, fileSize, remote_path, callback):
    # redis.hset("file_deliver", "%s_%s" % (host_info["host"], remote_path), value="connect host")
    client = FileDeliverHost(host_info["host"], pwd=host_info["pwd"], pkey=host_info["pkey"])
    # redis.hset("file_deliver", "%s_%s" % (host_info["host"], remote_path), value="upload")
    sftpproperteies=client.sftp.put(file, remote_path, callback=callback)
    print(host_info["host"] + " done")
    client.close()

def taskDownload(host_info,remote_path,local_path):
    client = FileDeliverHost(host_info["host"],user=host_info["user"], pwd=host_info["pwd"], pkey=host_info["pkey"])
    list=get_r_portable(client.sftp,remote_path)
    print(host_info["host"] + " done")
    something=zipfileV(list,client.sftp)
    client.close()
    return something

def md5sum( s):
        if s == None:
            return "None"
        m = md5()
        m.update(bytes(s, encoding="utf-8"))
        return m.hexdigest()



def get_r_portable(sftp, remotedir,  preserve_mtime=False):
    list=[]
    for entry in sftp.listdir(remotedir):
        remotepath = remotedir + "/" + entry
        mode = sftp.stat(remotepath).st_mode
        if S_ISDIR(mode):
            get_r_portable(sftp, remotepath, preserve_mtime)
        elif S_ISREG(mode):
            # sftp.get(remotepath, localpath, preserve_mtime=preserve_mtime)
            list.append(remotepath)
    return list

def zipfileV(filenames,sftp):
    zip_subdir = "archive"
    zip_filename = "%s.zip" % zip_subdir
    zip_io = BytesIO()
    for fpath in filenames:
        fdir, fname = os.path.split(fpath)
        # flo = BytesIO()
        # sftp.getfo(fpath, flo)
        # with zipfile.ZipFile(zip_io, 'w', zipfile.ZIP_DEFLATED) as archive:
        #     flo.prefetch()
        #     archive.writestr(fname,flo)
        #     # Reset file pointer
        #     flo.seek(0)
        file_object = BytesIO()
        with sftp.open(fpath, "rb") as fl:
            fl.prefetch()
            df = pd.read_csv(FileWithProgress(fl), sep=' ')


class FileWithProgress:

    def __init__(self, fl):
        self.fl = fl
        self.size = fl.stat().st_size
        self.p = 0

    def read(self, blocksize):
        r = self.fl.read(blocksize)
        self.p += len(r)
        print(str(self.p) + " of " + str(self.size))
        return r
if __name__ == '__main__':

    from multiprocessing.pool import Pool
    from multiprocessing import Process

    hosts = ["10.1.151.61"]  # , "172.16.0.17", "172.16.0.16", "172.16.0.18"]
    pwd = "MK?cd2pCc)P!`gh9"
    path = "/H:/adjuntos/afiliaciones/giphy.gif"
    local_path = "D:/Downloads/giphy.gif"
    file_size = getsize(local_path)
    processes = []
    start = time.time()
    for host in hosts:
        name = "%s_%s" % (host, path)
        p = Process(
            target=task0,
            args=({
                      "host": host,
                      "pwd": pwd,
                      "pkey": None
                  },
                  local_path, path, partial(file_callback, host, path)),
            name=name
        )
        p.start()
        print("start")
        processes.append((name, p))

    print("use %.2f s" % (time.time() - start))

    # print(redis.hget("file_deliver", "172.16.0.13_/root/test.png"))