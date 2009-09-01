%define wader_root %{_datadir}/wader-core
%define python_sitearch %(%{__python} -c 'from distutils import sysconfig; print sysconfig.get_python_lib()')

Name:           wader
Version:        0.3.6
Release:        1%{?dist}
Summary:        A ModemManager implementation written in Python
Source:         ftp://ftp.noexists.org/pub/wader/%{name}-%{version}.tar.bz2
Group:          Applications/Telephony
License:        GPL

%description
Wader is a fork of the core of "Vodafone Mobile Connect Card driver for Linux",
with some of its parts rewritten and improved to be able to interact via DBus
with other applications of the Linux/OSX desktop. Wader has two main
components, a core and a simple UI. The core can be extended to support more
devices and distros/OSes through plugins.

%package core
Summary:        The core of Wader
Group:          Applications/Telephony
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
BuildRequires:  python-devel, python-setuptools
Requires:       /usr/bin/eject
%if 0%{?suse_version}
BuildRequires:  hal, dbus-1-python, python-messaging, python-epsilon, python-zopeinterface, update-desktop-files
Requires:       python-twisted, python-serial, dbus-1-python
%else
BuildRequires:  dbus-python, python-zope-interface, python-twisted-core
Requires:       python-twisted-core, pyserial, dbus-python
%endif
%if %{defined moblin}
BuildRequires:  gettext
%endif

Requires:       python-twisted-conch, python-crypto, python-pytz, python-messaging, python-epsilon, usb_modeswitch, ozerocdoff
Conflicts:      ModemManager
Provides:       org.freedesktop.ModemManager

%description core
Wader core is a full ModemManager v0.2 implementation. It can be extended to
support more devices and distros/OSes through plugins.

%prep
%setup -q

%build
%{__make} -C resources/po/ mo

CFLAGS="%{optflags}" %{__python} setup.py build
CFLAGS="%{optflags}" %{__python} setup-gtk.py build

%install
%{__python} setup.py install --skip-build --root=%{buildroot} --prefix=%{_prefix}
%{__python} setup-gtk.py install --skip-build --root=%{buildroot} --prefix=%{_prefix}

# gettext
%{__mkdir_p} %{buildroot}%{_datadir}
%{__cp} -R resources/po/locale %{buildroot}%{_datadir}

# ppp-ip scripts
%{__mkdir_p} %{buildroot}%{_sysconfdir}/ppp/ip-up.d
%{__mkdir_p} %{buildroot}%{_sysconfdir}/ppp/ip-down.d
%{__install} -m0755 resources/config/95wader-up %{buildroot}%{_sysconfdir}/ppp/ip-up.d/95wader-up
%{__install} -m0755 resources/config/95wader-down %{buildroot}%{_sysconfdir}/ppp/ip-down.d/95wader-down

%if 0%{?suse_version}
%suse_update_desktop_file wader-gtk
%endif

# avoid %ghost warning
touch %{buildroot}%{_datadir}/wader-core/plugins/dropin.cache

%clean
%{__rm} -rf %{buildroot}

%post core
if [ $1 = 1 ]; then
    # kill modem-manager asap
    kill -9 `pidof modem-manager` 2> /dev/null
fi
if [ $1 = 2 ]; then
    # remove traces of old dir
    if [ -d /usr/share/wader ]; then
        rm -rf /usr/share/wader
    fi
    # update plugins cache
    rm -rf /usr/share/wader-core/plugins/dropin.cache
    python -c "from twisted.plugin import IPlugin, getPlugins;import wader.plugins; list(getPlugins(IPlugin, package=wader.plugins))"
    # restart wader-core
    if [ -e /var/run/wader.pid ]; then
        /usr/bin/wader-core-ctl --restart 2>/dev/null || true
    fi
fi

%files core
%defattr(-,root,root)
%dir %{python_sitearch}/wader
%{python_sitearch}/Wader-*
%dir %{python_sitearch}/wader/common/
%dir %{python_sitearch}/wader/common/hardware/
%dir %{python_sitearch}/wader/common/oses/
%dir %{python_sitearch}/wader/common/statem/
%dir %{python_sitearch}/wader/common/dialers/
%dir %{python_sitearch}/wader/contrib/
%dir %{python_sitearch}/wader/test/
%dir %{python_sitearch}/wader/plugins/

%{python_sitearch}/wader/*.py
%{python_sitearch}/wader/*.pyc
%{python_sitearch}/wader/common/*.py
%{python_sitearch}/wader/common/*.pyc
%{python_sitearch}/wader/common/hardware/*.py
%{python_sitearch}/wader/common/hardware/*.pyc
%{python_sitearch}/wader/common/oses/*.py
%{python_sitearch}/wader/common/oses/*.pyc
%{python_sitearch}/wader/common/statem/*.py
%{python_sitearch}/wader/common/statem/*.pyc
%{python_sitearch}/wader/common/dialers/*.py
%{python_sitearch}/wader/common/dialers/*.pyc
%{python_sitearch}/wader/contrib/*.py
%{python_sitearch}/wader/contrib/*.pyc
%{python_sitearch}/wader/test/*.py
%{python_sitearch}/wader/test/*.pyc
%{python_sitearch}/wader/plugins/*.py
%{python_sitearch}/wader/plugins/*.pyc

%dir %{wader_root}/
%dir %{wader_root}/plugins/
%{wader_root}/*.py
%{wader_root}/plugins/*.py

%dir %{wader_root}/resources
%{wader_root}/resources/config
%{wader_root}/resources/extra
%ghost %{wader_root}/plugins/dropin.cache

%dir %{_sysconfdir}/udev
%dir %{_sysconfdir}/udev/rules.d

%config %{_datadir}/dbus-1/system-services/org.freedesktop.ModemManager.service
%config %{_sysconfdir}/dbus-1/system.d/org.freedesktop.ModemManager.conf
%config %{_sysconfdir}/udev/rules.d/99-huawei-e169.rules
%config %{_sysconfdir}/udev/rules.d/99-ericsson.rules
%config %{_sysconfdir}/udev/rules.d/99-novatel-eu870d.rules
%config %{_sysconfdir}/udev/rules.d/99-novatel-mc950d.rules
%config %{_sysconfdir}/udev/rules.d/99-novatel-mc990d.rules
%config %{_sysconfdir}/udev/rules.d/99-option-icon-225.rules

%{_sysconfdir}/ppp/ip-down.d/95wader-down
%{_sysconfdir}/ppp/ip-up.d/95wader-up
%dir %{_datadir}/hal/fdi/information/20thirdparty
%{_datadir}/hal/fdi/information/20thirdparty/10-wader-modems.fdi

%{_bindir}/wader-core-ctl

%doc LICENSE README NEWS

%changelog
* Tue May 05 2009 Pablo Marti <pmarti@warp.es> 0.3.6
- 0.3.6 Release
* Fri Apr 03 2009 Pablo Marti <pmarti@warp.es> 0.3.5
- 0.3.5 Release
* Tue Mar 03 2009 Pablo Marti <pmarti@warp.es> 0.3.4
- 0.3.4 Release
* Mon Feb 23 2009 Pablo Marti <pmarti@warp.es> 0.3.3
- 0.3.3 Release
* Thu Feb 13 2009 Pablo Marti <pmarti@warp.es> 0.3.2
- 0.3.2 Release
* Mon Feb 02 2009 Pablo Marti <pmarti@warp.es> 0.3.1
- 0.3.1 Release
* Mon Dec 01 2008 Pablo Marti <pmarti@warp.es> 0.3.0
- 0.3.0 Release
