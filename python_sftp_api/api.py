import logging
import multiprocessing
import traceback
from functools import partial
import threading,time
from typing import List

import uvicorn
from fastapi import FastAPI, Form, UploadFile, File
from loguru import logger as log

from python_sftp_api.sftp import task, taskDownload, file_callback

file_router = FastAPI()


@file_router.post("/file_deliver")
async def create_file_deliver(
        files: List[UploadFile] = File(...),
        host: str = Form(...),
        path: str = Form(...),
        user: str = Form(...),
        password: str = Form(...),
        foldercode: str = Form(...)
):
    # Request.json() https://www.cnblogs.com/mazhiyong/p/13345076.html
    log.info("create ssh connection")
    processes = []
    try:
        for file in files:
            name = "%s_%s" % (host, file)

            content_assignment = await file.read()
            len(content_assignment)
            p = threading.Thread(
                target=task,
                args=({
                          "host": host,
                          "user": user,
                          "pwd": password,
                          "pkey": None
                      },
                      file,len(content_assignment), path+foldercode,partial(file_callback, host, path)),
                name=name
            )
            p.start()
            print("start" +name+p.pid)
            processes.append((name, p))

        for t in processes:
            t.join()
    except Exception as e:
        tb = traceback.format_exc()
        print(tb)
        print(e)


log.info("ssh connection done")


@file_router.get("/file_deliver")
async def query_file_deliver(host: str = Form(...),
                             path: str = Form(...),
                             user: str = Form(...),
                             password: str = Form(...),
                             foldercode: str = Form(...),
                             localpath: str = Form(...)):
    return taskDownload({
        "host": host,
        "user": user,
        "pwd": password,
        "pkey": None
    }, path + foldercode, localpath)


if __name__ == "__main__":
    multiprocessing.log_to_stderr(logging.DEBUG)
    uvicorn.run(file_router, host="0.0.0.0", port=8000)
