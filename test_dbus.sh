#!/bin/sh

if [ -z "$1" ] ; then
	echo "need name of device"
	exit 1
fi

NAME="`date +%s`-$1"

[ -d reports ] || mkdir reports

sudo su -c "cat /dev/null > /var/log/wader.log"
sudo wader-core-ctl --restart

sleep 10

nosetests -v --with-xunit --xunit-file=reports/"${NAME}".xml test/test_dbus.py

sync

sleep 5

cp /var/log/wader.log reports/"${NAME}".log

[ -f /usr/share/sounds/speech-dispatcher/test.wav ] && aplay /usr/share/sounds/speech-dispatcher/test.wav
