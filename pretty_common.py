from logging import getLogger
from paramiko import SSHClient


logger = getLogger(__name__)


def ssh_exec(ssh: SSHClient, cmd: str):
    logger.debug(cmd)
    stdout, stderr = ssh.exec_command(cmd)[1:3]
    buf = stdout.read().decode('utf-8')
    logger.debug(buf)
    print(buf)
    err_msg = stderr.read().decode('utf-8')
    if '' != err_msg:
        raise Exception('リモートサーバ上でコマンド実行に失敗: ' + err_msg)
