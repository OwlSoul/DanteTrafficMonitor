#!/usr/bin/env python3
"""This script monitors dante proxy data consumption per username"""

# pylint: disable=C0321

import argparse
import datetime
import socket
import sys
import threading
import time
import signal
import re
from collections import defaultdict
import daemon
import psycopg2
import setproctitle

LISTEN_SERVER = '127.0.0.1'
DANTE_LOG_PORT = 35531

# Database parameters, should be loaded from config
db_name = "danted"
db_username = "danted"
db_host = "localhost"
db_password = "TestPass8594"

dante_thread = None

# Verbosity: 0 - none
#            1 - minimal
#            2 - moderate
#            3 - everything
verbose = 3

# ------------                             OUTPUT                             ------------ #
# How often to write results out
WRITE_PERIOD = 2
# File to write results out
OUTFILE = 'dante_trafmon.data'
# Log structure:
#  username_1,out,in
#  username_2,out,in
#  ...
#  username_n,out,in

lock = threading.Lock()


def sigint_handler(sig, frame):
    """SIGINT Handler"""
    # pylint: disable=W0612,W0613
    print("\nINFO: SIGINT signal received! - Program will be terminated.")
    dante_thread.stop()
    sys.exit(0)


def sigusr1_handler(sig, frame):
    """SIGUSR1 Handler"""
    # pylint: disable=W0612,W0613
    print("\nINFO: SIGUSR1 signal received!")
    print("INFO: Resetting stored counters.")
    lock.acquire()
    dante_thread.traffic_dict = defaultdict(lambda: [0, 0])
    lock.release()
    print("INFO: Traffic counters were reset.")

# ---------------------------------------------------------------------------------------- #


def basic_test():
    """Basic test to ensure pytest works"""
    return "TEST"


class TimerThread(threading.Thread):
    """
    Timer thread class
    """
    log_thread = None

    def __init__(self, log_thread):
        super(TimerThread, self).__init__()
        self.log_thread = log_thread

    def data_init_from_db(self):
        """Initialize data from database"""
        conn = None

        try:
            conn = psycopg2.connect(host=db_host, database=db_name,
                                    user=db_username, password=db_password)
        except psycopg2.Error:
            print("ERROR: Unable to connect to database (data_init_from_db)")

        finally:
            if conn is not None:
                cur = conn.cursor()

                cur.execute("SELECT * FROM traffic")
                result = cur.fetchall()
                for row in result:
                    if verbose >= 3: print(row)
                    self.log_thread.traffic_dict[row[0]] = [row[2], row[1]]

                cur.close()
                conn.close()
            else:
                print("ERROR: Failed to obtain PSQL cursor (data_init_from_db")

    def run(self):
        """Timer threar "run" function"""
        global verbose
        global lock

        if self.log_thread is None:
            return

        # Getting initial data from database
        self.data_init_from_db()

        while self.log_thread.thread_running:
            lock.acquire()

            # Write to file
            self.log_thread.write_to_file(OUTFILE, self.log_thread.traffic_dict)

            # Write to PGSQL
            try:
                conn = psycopg2.connect(host=db_host, database=db_name,
                                        user=db_username, password=db_password)
            except psycopg2.Error:
                print("ERROR: Unable to connect to database (main cycle)")

            cur = conn.cursor()

            # "UPSERT" operation using ON CONFLICT
            for key, value in self.log_thread.traffic_dict.items():
                if verbose >= 2: print("  ", key, ':', value[1], '  ', value[0])
                cur.execute("INSERT INTO traffic(username, outgoing, incoming)"
                            "VALUES ('"+str(key)+"',"+str(value[1])+","+str(value[0])+")"
                            "ON CONFLICT(username) DO UPDATE "
                            "SET outgoing="+str(value[1])+",incoming="+str(value[0])+"")

            conn.commit()
            cur.close()
            conn.close()
            lock.release()

            print("INFO: "+str(datetime.datetime.now())+" - Data write to database (OK)")

            time.sleep(WRITE_PERIOD)


class LogThread(threading.Thread):
    """
    Logging thread class
    """
    LOG_TYPE_NONE = 0
    LOG_TYPE_DANTE = 1

    name = 'Thread'
    thread_running = True

    log_type = LOG_TYPE_NONE
    server = '127.0.0.1'
    port = 30000

    # Dictionary to keep traffic
    traffic_dict = defaultdict(lambda: [0, 0])

    def __init__(self, name, log_type, server, port):
        super(LogThread, self).__init__()
        self.name = name
        self.log_type = log_type
        self.server = server
        self.port = port

    ''' RUN '''
    def run(self):
        print("INFO: Thread "+self.name+" started. Port: "+str(DANTE_LOG_PORT))

        timer = TimerThread(log_thread=self)
        timer.start()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(5)

        try:
            sock.bind((self.server, self.port))
        except socket.error:
            print("Socket bind "+self.server+":"+str(self.port)+" failed!")
            sys.exit(1)

        sock.listen(5)

        while self.thread_running:
            try:
                conn, addr = sock.accept()
            except socket.timeout:
                continue

            print("Connection established: "+str(addr))
            while self.thread_running:
                conn.settimeout(5)

                # Receiving data
                try:
                    data = conn.recvfrom(4096)
                except socket.timeout:
                    continue

                # If data received, parce it
                if data != (b'', None):
                    string = data[0].decode("utf-8")
                    lines = string.splitlines()
                    # Parsing log string
                    lock.acquire()
                    for line in lines:
                        print("L:", line)
                        # Outgoing traffic
                        regex = r'.*username\%(.*)@.*->.*\((.*)\)'
                        res = re.match(regex, line)
                        if res:
                            if verbose >= 3: print('  OUT:', res.groups())
                            self.traffic_dict[res.groups()[0]][0] += int(res.groups()[1])
                        else:
                            # Incoming Traffic
                            regex = r'.*->.*username\%(.*)@.*\((.*)\)'
                            res = re.match(regex, line)
                            if res:
                                if verbose >= 3: print('  IN :', res.groups())
                                self.traffic_dict[res.groups()[0]][1] += int(res.groups()[1])
                        print("-----")
                        print("")
                    lock.release()

                else:
                    break

            conn.shutdown(socket.SHUT_RDWR)
        sock.shutdown(socket.SHUT_RDWR)

        print("INFO: Thread "+self.name+" terminated.")

    def stop(self):
        self.thread_running = False

    @staticmethod
    def write_to_file(filename, out_dict):
        global lock

        file_handler = open(filename, "w")
        for key, value in out_dict.items():
            file_handler.write(key+','+str(value[0])+','+str(value[1])+'\n')
        file_handler.close()

# ------------                           MAIN                                 ------------ #


def do_main_program():
    """
    Launch the tread to listen for incoming data about dante traffic,
    then enter eternal cycle.
    """
    global dante_thread
    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGUSR1, sigusr1_handler)

    dante_thread = LogThread("DANTE", LogThread.LOG_TYPE_DANTE, LISTEN_SERVER, DANTE_LOG_PORT)
    dante_thread.start()

    while 1:
        time.sleep(1)


if __name__ == "__main__":
    # Setting process name
    setproctitle.setproctitle("dante_trafmon")

    do_daemonize = False
    # Parse arguments
    parser = argparse.ArgumentParser(description="Dante traffic monitor, counts"
                                                 "traffic used by different users"
                                                 "of dante proxy server.")
    parser.add_argument("--daemon", action="store_true", default=False, help="Daemonize process.")

    args = parser.parse_args()
    if args.daemon:
        do_daemonize = True

    # Prepare daemon context
    if do_daemonize:
        logfile = open('daemon.log', 'w')
        context = daemon.DaemonContext(stdout=logfile, stderr=logfile)
        context.open()

        with context:
            do_main_program()
    else:
        do_main_program()
    sys.exit(0)
