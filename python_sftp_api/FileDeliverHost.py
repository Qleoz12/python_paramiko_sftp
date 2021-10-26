from contextlib import contextmanager
from hashlib import md5
import paramiko
from loguru import logger as log

class FileDeliverHost():
    def __init__(self, host: str, port=1221, user=None, pwd=None, pkey=None):
        log.info("start connect host=%s, pwd=%s" % (host, self.md5sum(pwd or pkey)))
        self.sock = (host, port)
        self.user = user
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh_client.connect(hostname=host, port=port, username=user, password=pwd, pkey=pkey)
        self.sftp = self.ssh_client.open_sftp()
        self.open_file_fd = None

    @contextmanager
    def open(self, path, mode):
        self.open_file_fd = self.sftp.open(path, mode=mode, bufsize=paramiko.sftp_file.SFTPFile.MAX_REQUEST_SIZE)
        setattr(self.open_file_fd, "path", path)
        try:
            yield self.open_file_fd
        finally:
            self.open_file_fd.flush()
            self.open_file_fd.close()

    def read(self, n=paramiko.sftp_file.SFTPFile.MAX_REQUEST_SIZE):
        return self.open_file_fd.read(n)

    def write(self, content):
        return self.open_file_fd.write(content)

    def check_md5(self):
        _, stdout, stderr = self.ssh_client.exec_command("md5sum " + self.open_file_fd.path)
        md5_ = str(stdout.read(), encoding="utf-8").split(" ")[0]
        err = str(stderr.read(), encoding="utf-8")
        if len(err):
            raise MD5CheckException(err)
        return self.sock[0], self.open_file_fd.path, md5_

    def close(self):
        if self.open_file_fd:
            try:
                self.open_file_fd.close()
            except Exception as e:
                log.error("close file error: %s" % str(e))
        self.sftp.close()
        self.ssh_client.close()

    def __del__(self):
        self.close()

    def md5sum(self, s):
        if s == None:
            return "None"
        m = md5()
        m.update(bytes(s, encoding="utf-8"))
        return m.hexdigest()

class MD5CheckException(Exception):
    pass