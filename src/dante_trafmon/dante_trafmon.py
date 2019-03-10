#!/usr/bin/env python3
"""This script monitors dante proxy data consumption per username"""

# pylint: disable=C0321

import os
import argparse
import configparser
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

# pylint: enable=R0902
class Application:
    """
    Main application class
    """

    VERSION = "1.0.0"

    _default_config = "/etc/dante_trafmon.conf"

    # NOTE: Since dante_trafmon can collect data from multiple dante servers,
    #       giving it permissions to mess with dante's log is not a right decision.
    #       This line is left as a reminder for sins of the past.
    #_log_recreate = 60


    # Database parameters, probably should be loaded from config
    # ----                          Database name                        ---- #
    _db_name = "danted"

    @property
    def db_name(self):
        """ Database name getter"""
        return self._db_name

    @db_name.setter
    def db_name(self, value):
        """ Database name setter"""
        self._db_name = value

    # ----                        Database username                      ---- #
    _db_username = "danted"

    @property
    def db_username(self):
        """ Database username getter"""
        return self._db_username

    @db_username.setter
    def db_username(self, value):
        """ Database username setter"""
        self._db_username = value

    # ----                        Database hostname                      ---- #
    _db_hostname = "127.0.0.1"

    @property
    def db_hostname(self):
        """ Database hostname setter"""
        return self._db_hostname

    @db_hostname.setter
    def db_hostname(self, value):
        """ Database hostname getter"""
        self._db_hostname = value

    # ----                         Database password                     ---- #
    _db_password = "password"

    @property
    def db_password(self):
        """ Database password setter"""
        return self._db_password

    @db_password.setter
    def db_password(self, value):
        """ Database password getter"""
        self._db_password = value

    # ----                           Listen address                      ---- #
    _listen_address = "127.0.0.1"

    @property
    def listen_address(self):
        """ Listen address getter"""
        return self._listen_address

    @listen_address.setter
    def listen_address(self, value):
        """ Listen address setter"""
        self._listen_address = value

    # ----                            Listen port                        ---- #
    _listen_port = 35531

    @property
    def listen_port(self):
        """ Listen port getter"""
        return self._listen_port

    @listen_port.setter
    def listen_port(self, value):
        """ Listen port setter"""
        self._listen_port = value

    # ----                            Write period                       ---- #
    # How often to write results out
    _write_period = 2

    @property
    def write_period(self):
        """ Write period getter"""
        return self._write_period

    @write_period.setter
    def write_period(self, value):
        """ Write period setter"""
        self._write_period = value

    # ----                             Daemon log                        ---- #

    _daemon_log = "/tmp/dante_trafmon.log"

    @property
    def daemon_log(self):
        """ Daemon log getter"""
        return self._daemon_log

    @daemon_log.setter
    def daemon_log(self, value):
        """ Daemon log setter"""
        self._daemon_log = value

    # ------------------------------------------------------------------------#
    dante_thread = None

    # Verbosity: 0 - none
    #            1 - minimal
    #            2 - moderate
    #            3 - everything
    verbose = 3

    # Daemonize the program or not?
    do_daemonize = False

    # File to write results out
    OUTFILE = 'dante_trafmon.data'

    # Log structure:
    #  username_1,out,in
    #  username_2,out,in
    #  ...
    #  username_n,out,in

    lock = threading.Lock()

    def __init__(self):
        # Setting process name
        setproctitle.setproctitle("dante_trafmon")

        self.do_daemonize = False

    def parse_config_file(self, configfile):
        """Parse the configuration file"""
        config = configparser.ConfigParser()
        config.read(configfile)

        if "general" in config:
            self.write_period = int(config["general"]["write_period"])
            self.daemon_log = str(config["general"]["trafmon_log"])
            self.listen_address = str(config["general"]["listen_address"])
            self.listen_port = int(config["general"]["listen_port"])

        if "database" in config:
            self.db_name = config["database"]["db_name"]
            self.db_username = config["database"]["db_username"]
            self.db_hostname = config["database"]["db_hostname"]
            self.db_password = config["database"]["db_password"]

        if self.verbose >= 2:
            print("\nINFO : " + str(datetime.datetime.now()) +
                  " Config loaded:")
            print("  write_period   =", str(self.write_period))
            print("  trafmon_log    =", str(self.daemon_log))
            print("  listen_address =", str(self.listen_address))
            print("  listen_port    =", str(self.listen_port))
            print("")
            print("  db_hostname    = ", str(self.db_hostname))
            print("  db_name        = ", str(self.db_name))
            print("  db_username    = ", str(self.db_username))
            print("  db_password    = ", str(self.db_password))
            print("")

    @staticmethod
    def basic_test():
        """Basic test to ensure pytest works"""
        return "TEST"

    def sigint_handler(self, signl, frame):
        """SIGINT Handler"""
        # pylint: disable=W0612,W0613
        print("\nINFO : " + str(datetime.datetime.now()) +
              " SIGINT signal received! Program will be terminated.")
        self.dante_thread.stop()
        self.dante_thread.timer.join()
        self.dante_thread.join()

    def sigterm_handler(self, signl, frame):
        """SIGTERM Handler"""
        print("\nINFO : " + str(datetime.datetime.now()) + " SIGTERM signal received!")
        self.sigint_handler(signl, frame)

    def sigusr1_handler(self, signl, frame):
        """SIGUSR1 Handler"""
        # pylint: disable=W0612,W0613
        print("\nINFO : " + str(datetime.datetime.now()) + " SIGUSR1 signal received!")
        print("INFO: " + str(datetime.datetime.now()) + " Resetting stored counters.")
        self.lock.acquire()
        self.dante_thread.traffic_dict = defaultdict(lambda: [0, 0])
        self.lock.release()
        print("INFO : " + str(datetime.datetime.now()) + " Traffic counters were reset.")

    def do_main_program(self):
        """
        Launch the tread to listen for incoming data about dante traffic,
        then enter eternal cycle.
        """
        #self.parse_config_file("config/dante_trafmon.conf")

        signal.signal(signal.SIGINT, self.sigint_handler)
        signal.signal(signal.SIGTERM, self.sigterm_handler)
        signal.signal(signal.SIGUSR1, self.sigusr1_handler)

        self.dante_thread = LogThread("DANTE",
                                      LogThread.LOG_TYPE_DANTE,
                                      self)
        self.dante_thread.start()

        while self.dante_thread.thread_running:
            time.sleep(1)

    def execute(self):
        """Execute main application"""

        # Parse arguments
        parser = argparse.ArgumentParser(description="Dante traffic monitor, counts"
                                                     "traffic used by different users"
                                                     "of dante proxy server.")
        parser.add_argument("--daemon", action="store_true", default=False,
                            help="Daemonize process.")

        parser.add_argument("--config", default=self._default_config,
                            help="Configuration file.")

        args = parser.parse_args()
        if args.daemon:
            self.do_daemonize = True

        # Read configuration file
        if not os.path.isfile(args.config):
            print("ERROR: " + str(datetime.datetime.now()) + " config file not found " +
                  "(" + args.config + ")")
            print("       Terminating the program.")
            sys.exit(1)
        else:
            pass
            self.parse_config_file(args.config)

        # Prepare daemon context
        if self.do_daemonize:
            logfile = open(self.daemon_log, 'w')
            context = daemon.DaemonContext(stdout=logfile, stderr=logfile)
            context.open()

            with context:
                self.do_main_program()
        else:
            self.do_main_program()

# ---------------------------------------------------------------------------------------- #


class TimerThread(threading.Thread):
    """
    Timer thread class, will write data to database every write_period seconds
    """
    log_thread = None
    app = None

    def __init__(self, application, log_thread):
        super(TimerThread, self).__init__()
        self.log_thread = log_thread
        self.app = application

    def data_init_from_db(self):
        """Initialize data from database. This is important, if script cannot receive data
        from database if should halt.
        TODO: This behaviour should probably be changed later."""
        result = 0
        result_msg = "OK!"

        if self.app.verbose >= 3:
            print("INFO : " + str(datetime.datetime.now()) +
                  " Database: '" + self.app.db_name +
                  " Hostname: " + self.app.db_hostname +
                  " User: " + self.app.db_name +
                  " Password: " + self.app.db_password)

        try:
            conn = psycopg2.connect(host=self.app.db_hostname,
                                    database=self.app.db_name,
                                    user=self.app.db_username,
                                    password=self.app.db_password,
                                    connect_timeout=5)
        # pylint: disable=C0103
        except psycopg2.OperationalError as e:
            print("ERROR: " + str(datetime.datetime.now()) +
                  " Unable to connect to database (data_init_from_db)")
            print("ERROR: " + str(datetime.datetime.now()) + " " + str(e))
            result = 1
            result_msg = str(e)
        # pylint: enable=C0103
        else:
            if conn is not None:
                cur = conn.cursor()

                cur.execute("SELECT * FROM traffic")
                res = cur.fetchall()
                for row in res:
                    if self.app.verbose >= 3: print(row)
                    self.log_thread.traffic_dict[row[0]] = [row[2], row[1]]

                cur.close()
                conn.close()
            else:
                print("ERROR: " + str(datetime.datetime.now()) +
                      " Failed to obtain PSQL cursor (data_init_from_db)")

        return result, result_msg

    def run(self):
        """Timer threar "run" function"""

        if self.log_thread is None:
            return

        # Getting initial data from database
        result, result_msg = self.data_init_from_db()
        if result != 0:
            print("ERROR: " + str(datetime.datetime.now()) +
                  " Database is not available, terminating now.")
            self.log_thread.stop()
            return

        while self.log_thread.thread_running:
            self.app.lock.acquire()

            # Write to file
            # ERROR: No write rights under non-root user in Vagrant.
            #        Suspending for now
            #self.log_thread.write_to_file(self.app.OUTFILE,
            #                              self.log_thread.traffic_dict)

            # Write to PGSQL
            result, result_msg = self.log_thread.write_to_pgsql(self.log_thread.traffic_dict)

            self.app.lock.release()

            if result == 0:
                print("INFO : "+str(datetime.datetime.now())+" Data write to database (OK)")
            else:
                print("INFO : " + str(datetime.datetime.now()) + " Data write to database (FAIL)")

            time.sleep(self.app.write_period)


class LogThread(threading.Thread):
    """
    One thread for one data source, currently only one data source exists anyway -
    data redirected from danted.log to socket.
    """
    LOG_TYPE_NONE = 0
    LOG_TYPE_DANTE = 1

    name = 'Thread'
    app = None
    timer = None

    thread_running = True

    log_type = LOG_TYPE_NONE

    # Dictionary to keep traffic
    traffic_dict = defaultdict(lambda: [0, 0])

    def __init__(self, name, log_type, application):
        super(LogThread, self).__init__()
        self.name = name
        self.log_type = log_type
        self.app = application

    def run(self):
        """
        Run separate thread
        """
        print("INFO : " + str(datetime.datetime.now()) +
              " Thread " + self.name + " started. Port: " + str(self.app.listen_port))

        self.timer = TimerThread(log_thread=self, application=self.app)
        self.timer.start()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(5)

        try:
            sock.bind((self.app.listen_address,
                       self.app.listen_port))
        except socket.error:
            print("INFO : " + str(datetime.datetime.now()) +
                  " Socket bind " + self.app.listen_address +
                  ":" + str(self.app.listen_port) + " failed!")
            sys.exit(1)

        sock.listen(5)

        while self.thread_running:
            try:
                conn, addr = sock.accept()
            except socket.timeout:
                continue

            print("INFO : " + str(datetime.datetime.now()) +
                  " Connection established: "+str(addr))
            while self.thread_running:
                conn.settimeout(5)

                # Receiving data
                try:
                    data = conn.recvfrom(4096)
                except socket.timeout:
                    continue

                # If data received, parse it
                if data != (b'', None):
                    string = data[0].decode("utf-8")
                    lines = string.splitlines()
                    # Parsing log string
                    self.app.lock.acquire()
                    for line in lines:
                        print("L:", line)
                        # Outgoing traffic
                        regex = r'.*username\%(.*)@.*->.*\((.*)\)'
                        res = re.match(regex, line)
                        if res:
                            if self.app.verbose >= 3: print('  OUT:', res.groups())
                            self.traffic_dict[res.groups()[0]][0] += int(res.groups()[1])
                        else:
                            # Incoming Traffic
                            regex = r'.*->.*username\%(.*)@.*\((.*)\)'
                            res = re.match(regex, line)
                            if res:
                                if self.app.verbose >= 3: print('  IN :', res.groups())
                                self.traffic_dict[res.groups()[0]][1] += int(res.groups()[1])
                        print("-----")
                        print("")
                    self.app.lock.release()

                else:
                    break

            conn.shutdown(socket.SHUT_RDWR)
        sock.shutdown(socket.SHUT_RDWR)

        print("INFO : " + str(datetime.datetime.now()) +
              " Thread "+self.name+" terminated.")

    def stop(self):
        """ Set the thread to stop"""
        self.thread_running = False

    @staticmethod
    def write_to_file(filename, out_dict):
        """Write current collected data of users traffic consumption to file"""
        file_handler = open(filename, mode="w+")
        for key, value in out_dict.items():
            file_handler.write(key+','+str(value[0])+','+str(value[1])+'\n')
        file_handler.close()

    def write_to_pgsql(self, out_dict):
        """Write current collected data of users traffic consumption to PostgreSQL database"""
        result = 0
        result_msg = ""
        try:
            conn = psycopg2.connect(host=self.app.db_hostname,
                                    database=self.app.db_name,
                                    user=self.app.db_username,
                                    password=self.app.db_password,
                                    connect_timeout=5)
        # pylint: disable=C0103
        except psycopg2.OperationalError as e:
            print("ERROR: " + str(datetime.datetime.now()) +
                  " Unable to connect to database (main cycle)")
            print("ERROR: " + str(datetime.datetime.now()) + " " + str(e))
            result = 1
            result_msg = str(e)
        # pylint: enable=C0103
        else:
            cur = conn.cursor()

            # "UPSERT" operation using ON CONFLICT
            # pylint: disable=C0301
            for key, value in out_dict.items():
                if self.app.verbose >= 2: print("  ", key, ':', value[1], '  ', value[0])
                cur.execute("INSERT INTO traffic(username, outgoing, incoming)"
                            "VALUES ('" + str(key) + "'," + str(value[0]) + "," + str(value[1]) + ")"
                            "ON CONFLICT(username) DO UPDATE "
                            "SET outgoing=" + str(value[0]) +
                            ",incoming=" + str(value[1]) + "")
            # pylint: enable=C0301

            conn.commit()
            cur.close()
            conn.close()

        return result, result_msg

# ------------                           MAIN                                 ------------ #

#pylint: disable=C0103
if __name__ == "__main__":
    app = Application()
    app.execute()
    sys.exit(0)
