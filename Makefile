SHELL = /bin/bash

VERSION := $(shell python -c 'from wader.common.consts import APP_VERSION; print APP_VERSION')
SOURCES := $(shell rpmbuild --eval '%{_topdir}' 2>/dev/null)/SOURCES
WCV := wader-core-$(VERSION)

all:
	@echo Usage: make deb\|rpm

rpm:
	@if [ ! -d $(SOURCES) ] ;\
	then\
		echo 'SOURCES does not exist, are you running on a non RPM based system?';\
		exit 1;\
	fi

	tar -jcvf $(SOURCES)/$(WCV).tar.bz2 --exclude=.git --transform="s/^\./$(WCV)/" .
	rpmbuild -ba resources/rpm/wader.spec

deb:
	@if [ ! -d /var/lib/dpkg ] ;\
	then\
		echo 'Debian package directory does not exist, are you running on a non Debian based system?';\
		exit 1;\
	fi

	@if ! head -1 debian/changelog | grep -q $(VERSION) ;\
	then\
		echo Changelog and package version are different;\
		exit 1;\
	fi

	dpkg-buildpackage -rfakeroot
