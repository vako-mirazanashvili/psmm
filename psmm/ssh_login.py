#!/usr/bin/env python3
# job3 - connect to a server with ssh and run one command
# uses paramiko, it is the lib that does the ssh part
import paramiko

host = "172.16.131.150"   # ip of the server (ftp here)
port = 22
user = "monitor"
key = "/root/.ssh/id_ed25519"   # my private key, used instead of a password
cmd = "df -h"                    # command to run on the server

def connect(host, port, user, key, cmd):
    client = paramiko.SSHClient()
    # if the server is unknown, trust it (ssh normally asks yes/no)
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # the real login, same as typing ssh monitor@host but with the key
        client.connect(host, port=port, username=user, key_filename=key)

        # run the command on the OTHER machine, gives back 3 things
        stdin, stdout, stderr = client.exec_command(cmd)

        out = stdout.read().decode()  # decode because it comes as bytes
        err = stderr.read().decode()

        if out:
            print(out)
        if err:
            print(err)

    except Exception as e:
        print("fail:", e)  # wrong ip, key problem, server down...

    finally:
        client.close()  # close the connection, like typing exit

connect(host, port, user, key, cmd)
