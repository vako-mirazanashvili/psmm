#!/usr/bin/env python3
# job5 - check that we can reach the mariadb server
# no ssh here, direct connection on the mysql port (3306)
import mysql.connector
from mysql.connector import Error

db_host = "172.16.131.147"   # sql server
db_port = 3306
db_user = "psmm_user"        # database user (not the same as the ssh user monitor)
db_pass = "********"
db_name = "psmm"

def test_connection():
    try:
        # same as "mysql -h ip -u user -p" but in python
        conn = mysql.connector.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_pass,
            database=db_name
        )

        if conn.is_connected():
            print("connected ok")
            cursor = conn.cursor()  # the cursor lets us run sql queries
            cursor.execute("SELECT DATABASE();")
            result = cursor.fetchone()
            print(result[0])

    except Error as e:
        print("fail:", e)  # wrong password, server down, firewall...

    finally:
        # always close, else connections stay open on the server
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

test_connection()
