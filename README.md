# Dante Traffic Monitor

This is a ~~"simple"~~ "not so simple anymore" script to monitor dante traffic consumption per user. Out-of-the-box dante proxy server can't do that, but it's possible with right logs setup and some simple parser.

The idea behind this script that it listens on port for incoming data from dante logs, parses received data and then stores it into database. Database logs are being supplied to the script via this command:\
`tail -f -n +1 /var/log/danted.log > /dev/tcp/127.0.0.1/35531`

Doing something like this allows one "dante_trafmon" (this script's name) server to collect data from multiple dante servers. By default, "dante_trafmon" listens on 127.0.0.1 and port 35531.

## Installation
A "deb" package is provided in releases page. \
`dpkg -i dante-trafmon`

Make changes to /etc/dante_trafmon.conf match your database setup (and some other settings).

## Dante log settings
Several log settings are required to capture and parse packet sized passed through dante proxy. Basically, you need to log all "ioop" (input-output) operations.

```
client pass {
        from: 0.0.0.0/0 to: 0.0.0.0/0
        #log: error connect disconnect
        log: ioop
}

client block {
        from: 0.0.0.0/0 to: 0.0.0.0/0
        #log: connect error
        log: ioop
}

socks pass {
        from: 0.0.0.0/0 to: 0.0.0.0/0
        #log: error connect disconnect
        log: ioop
}

socks block {
        from: 0.0.0.0/0 to: 0.0.0.0/0
        #log: connect error
        log: ioop
}
```

It is also possible to log traffic consumption from/to several ip adresses only.

## Database preparation
Currently, only PostgreSQL is supported. Also, no automatic database creation yet (TODO).\
 \
Create role for traffic monitor:\
`CREATE ROLE danted WITH ENCRYPTED PASSWORD 'password';`\
 \
Create database for traffic monitor:\
`CREATE DATABASE danted;`\
 \
Switch to newly created database:\
`\c danted`\
 \
Create table to store traffic:\
`CREATE TABLE traffic( username varchar, incoming integer DEFAULT 0, outgoing integer DEFAULT 0, PRIMARY KEY (username) );` \
 \
Grant required priveleges on newly created database to created role: \
`GRANT ALL PRIVILEGES ON DATABASE danted TO danted;` \
 \
Yeah, allow this too: \
`ALTER ROLE danted WITH LOGIN;` \
 \
Also grant all required privileges to table itself: \
`GRANT ALL PRIVILEGES ON TABLE traffic TO danted;` \
 \
Make some tests: \
`INSERT INTO traffic(username, incoming) VALUES (‘test01’, 1000);` \
`SELECT * FROM traffic;` \


## Running the script
There are currently two scripts to run traffic monitor on the same machine dante server itself runs.\
\
"*dante-trafmon-start*" starts the traffic monitor server (under dante_trafmon user), and will also run "tail" command to supply the log as well. The start script is recommended to be run under superuser.\
\
"*dante-trafmon-stop*" stops the traffic monitor server, and is also recommended to be run under superuser (to stop "tail" command as well).

