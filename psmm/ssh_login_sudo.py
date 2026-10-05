#!/usr/bin/env python3
# job4 - same as job3 but the command is run with sudo
import paramiko

host = "172.16.131.150"
port = 22
user = "monitor"
key = "/root/.ssh/id_ed25519"
sudo_pass = "********"   # sudo password of monitor on the server
cmd = "ls /root"          # needs sudo to see this folder

def connect_sudo(host, port, user, key, sudo_pass, cmd):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(host, port=port, username=user, key_filename=key)

        # normal sudo asks the password in a terminal, here there is no terminal
        # so -S says "read the password from stdin"
        full_cmd = "sudo -S " + cmd

        stdin, stdout, stderr = client.exec_command(full_cmd)

        # like typing the password and pressing enter
        stdin.write(sudo_pass + "\n")
        stdin.flush()  # force send now

        out = stdout.read().decode()
        err = stderr.read().decode()

        print(out)
        print(err)
        # "[sudo] password for monitor:" in err is normal, not a real error

    except Exception as e:
        print("fail:", e)

    finally:
        client.close()

connect_sudo(host, port, user, key, sudo_pass, cmd)
