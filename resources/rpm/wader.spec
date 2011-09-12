%define wader_root %{_datadir}/wader-core
%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           wader-core
Version:        %(%{__python} -c 'from wader.common.consts import APP_VERSION; print APP_VERSION')
Release:        1%{?dist}
Summary:        A ModemManager implementation written in Python
Source:         ftp://ftp.noexists.org/pub/wader/%{name}-%{version}.tar.bz2
Group:          Applications/Telephony
License:        GPL
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
BuildArch:      noarch

BuildRequires:  python-devel
%if 0%{?fedora} >= 8
BuildRequires: python-setuptools-devel
%else
BuildRequires: python-setuptools
%endif

%if 0%{?suse_version}
BuildRequires:  dbus-1-python, python-zopeinterface, python-twisted
Requires:       python-twisted, python-serial, dbus-1-python, python-tz, usb_modeswitch-data
%else
BuildRequires:  dbus-python, python-zope-interface, python-twisted-core
Requires:       python-twisted-core, pyserial, dbus-python, pytz, usb_modeswitch-data >= 20100322
%endif

Requires:       python >= 2.5, python-crypto, python-messaging >= 0.5.11, usb_modeswitch >= 1.1.0, python-gudev
Obsoletes:      ModemManager
Provides:       ModemManager

%description
Wader is a fork of the core of "Vodafone Mobile Connect Card driver for Linux",
with some of its parts rewritten and improved to be able to interact via DBus
with other applications of the Linux/OSX desktop. Wader has two main
components, a core and a simple UI. The core can be extended to support more
devices and distros/OSes through plugins.

%prep
%setup -q -n %{name}-%{version}

%build
%{__python} -c 'import setuptools; execfile("setup.py")' build

%install
%{__python} -c 'import setuptools; execfile("setup.py")' install -O1 --skip-build --root %{buildroot} --prefix=%{_prefix}

# avoid %ghost warning
touch %{buildroot}%{_datadir}/wader-core/plugins/dropin.cache

%clean
[ "%{buildroot}" != "/" ] && rm -rf %{buildroot}

%post
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

%files
%defattr(-,root,root)
%dir %{python_sitelib}/wader
%{python_sitelib}/Wader-*
%dir %{python_sitelib}/wader/common/
%dir %{python_sitelib}/wader/common/hardware/
%dir %{python_sitelib}/wader/common/oses/
%dir %{python_sitelib}/wader/common/statem/
%dir %{python_sitelib}/wader/common/backends/
%dir %{python_sitelib}/wader/contrib/
%dir %{python_sitelib}/wader/test/
%dir %{python_sitelib}/wader/plugins/

%{python_sitelib}/wader/*.py
%{python_sitelib}/wader/*.py[co]
%{python_sitelib}/wader/common/*.py
%{python_sitelib}/wader/common/*.py[co]
%{python_sitelib}/wader/common/hardware/*.py
%{python_sitelib}/wader/common/hardware/*.py[co]
%{python_sitelib}/wader/common/oses/*.py
%{python_sitelib}/wader/common/oses/*.py[co]
%{python_sitelib}/wader/common/statem/*.py
%{python_sitelib}/wader/common/statem/*.py[co]
%{python_sitelib}/wader/common/backends/*.py
%{python_sitelib}/wader/common/backends/*.py[co]
%{python_sitelib}/wader/contrib/*.py
%{python_sitelib}/wader/contrib/*.py[co]
%{python_sitelib}/wader/test/*.py
%{python_sitelib}/wader/test/*.py[co]
%{python_sitelib}/wader/plugins/*.py
%{python_sitelib}/wader/plugins/*.py[co]

%dir %{wader_root}/
%dir %{wader_root}/plugins/
%{wader_root}/*.py*
%{wader_root}/plugins/*.py*

%dir %{wader_root}/resources
%{wader_root}/resources/config
%{wader_root}/resources/extra
%ghost %{wader_root}/plugins/dropin.cache

%dir %{_sysconfdir}/udev/
%dir %{_sysconfdir}/udev/rules.d/
%{_sysconfdir}/udev/rules.d/*

%config %{_datadir}/dbus-1/system-services/org.freedesktop.ModemManager.service
%config %{_sysconfdir}/dbus-1/system.d/org.freedesktop.ModemManager.conf

%{_bindir}/wader-core-ctl

%doc LICENSE README

%changelog
* Mon Jun 06 2011 Andrew Bird <ajb@spheresystems.co.uk> 0.5.6
- 0.5.6 Update spec file
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
