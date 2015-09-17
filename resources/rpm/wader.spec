%define wader_root %{_datadir}/wader-core
%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           wader
Version:        %(%{__python} -c 'from wader.common.consts import APP_VERSION; print APP_VERSION')
Release:        1%{?dist}
Summary:        A ModemManager implementation written in Python
Source:         ftp://ftp.noexists.org/pub/wader/%{name}-%{version}.tar.bz2
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
%else
BuildRequires:  dbus-python, python-zope-interface, python-twisted-core
%endif

%description
Wader is a fork of the core of "Vodafone Mobile Connect Card driver for Linux",
with some of its parts rewritten and improved to be able to interact via DBus
with other applications of the Linux/OSX desktop. Wader has two main
components, a core and a client access library. The core can be extended to
support more devices and distros/OSes through plugins.

%package        core
Version:        %(%{__python} -c 'from wader.common.consts import APP_VERSION; print APP_VERSION')
Summary:        The core that controls modem devices and provides DBus services.
Group:          System Environment/Daemons
Requires:       python-epsilon, python-gudev

%if 0%{?suse_version}
Requires:       python-twisted, python-serial, dbus-1-python, python-tz, usb_modeswitch-data
%else
Requires:       python-twisted-core, pyserial, dbus-python, pytz, usb_modeswitch-data >= 20100322
%endif

Obsoletes:      ModemManager >= 0.4
Provides:       ModemManager >= 0.4

%description    core
Wader is a fork of the core of "Vodafone Mobile Connect Card driver for Linux",
this package provides the core modem device access and DBus services.



%package -n     python-wader
Version:        %(%{__python} -c 'from wader.common.consts import APP_VERSION; print APP_VERSION')
Summary:        Library that provides access to wader core.
Group:          System Environment/Libraries
Requires:       python >= 2.5, python-crypto, python-messaging >= 0.5.11, dbus-python, pytz
Conflicts:      wader-core <= 0.5.8

%description -n python-wader
Wader is a fork of the core of "Vodafone Mobile Connect Card driver for Linux",
this package provides those common parts that are likely to be reused by Modem
Manager clients written in python.

%prep
%setup -q -n %{name}-%{version}

%build
%{__python} -c 'import setuptools; execfile("setup.py")' build

%install
%{__python} -c 'import setuptools; execfile("setup.py")' install -O1 --skip-build --root %{buildroot} --prefix=%{_prefix}

# avoid ghost warning
touch %{buildroot}%{_datadir}/wader-core/plugins/dropin.cache

%clean
[ "%{buildroot}" != "/" ] && rm -rf %{buildroot}

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
    python -c "import sys; sys.path.insert(0, '/usr/share/wader-core'); from twisted.plugin import IPlugin, getPlugins;import plugins; list(getPlugins(IPlugin, package=plugins))"
    # restart wader-core
    if [ -e /var/run/wader.pid ]; then
        /usr/bin/wader-core-ctl --restart 2>/dev/null || true
    fi
fi

%files core
%defattr(-,root,root)

%dir %{wader_root}/
%dir %{wader_root}/plugins/
%dir %{wader_root}/core/
%{wader_root}/core/*.py*
%dir %{wader_root}/core/hardware/
%{wader_root}/core/hardware/*.py*
%dir %{wader_root}/core/oses/
%{wader_root}/core/oses/*.py*
%dir %{wader_root}/core/statem/
%{wader_root}/core/statem/*.py*
%dir %{wader_root}/core/backends/
%{wader_root}/core/backends/*.py*
%{wader_root}/*.py*
%{wader_root}/plugins/*.py*
%{wader_root}/test/test_dbus*.py*

%dir %{wader_root}/resources
%{wader_root}/resources/config
%{wader_root}/resources/extra
%ghost %{wader_root}/plugins/dropin.cache

%dir /lib/udev/
%dir /lib/udev/rules.d/
/lib/udev/rules.d/*

%config %{_datadir}/dbus-1/system-services/org.freedesktop.ModemManager.service
%config %{_sysconfdir}/dbus-1/system.d/org.freedesktop.ModemManager.conf

%{_bindir}/wader-core-ctl

%doc LICENSE README

%files -n python-wader
%defattr(-,root,root)
%dir %{python_sitelib}/wader
%{python_sitelib}/Wader-*
%dir %{python_sitelib}/wader/common/

%{python_sitelib}/wader/*.py
%{python_sitelib}/wader/*.py[co]
%{python_sitelib}/wader/common/*.py
%{python_sitelib}/wader/common/*.py[co]
%{python_sitelib}/wader/common/backends/*.py
%{python_sitelib}/wader/common/backends/*.py[co]

%doc LICENSE README

%changelog
* Thu Sep 17 2015 Andrew Bird <ajb@spheresystems.co.uk> 0.5.13
- 0.5.13 Release
* Tue May 22 2012 Andrew Bird <ajb@spheresystems.co.uk> 0.5.12
- 0.5.12 Release
* Thu Apr 19 2012 Andrew Bird <ajb@spheresystems.co.uk> 0.5.11
- 0.5.11 Release
* Mon Jan 23 2012 Andrew Bird <ajb@spheresystems.co.uk> 0.5.10
- 0.5.10 Release
* Fri Dec 02 2011 Andrew Bird <ajb@spheresystems.co.uk> 0.5.9
- 0.5.9 Release
* Mon Nov 14 2011 Andrew Bird <ajb@spheresystems.co.uk> 0.5.8
- 0.5.8 Release
* Sun Sep 11 2011 Andrew Bird <ajb@spheresystems.co.uk> 0.5.7
- 0.5.7 Release
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
