#include <Python.h>

#include <sysexits.h>
#include <sys/param.h>

#include <CoreFoundation/CoreFoundation.h>

#include <IOKit/IOKitLib.h>
#include <IOKit/serial/IOSerialKeys.h>
#include <IOKit/IOBSD.h>

static PyObject * GetModemList(io_iterator_t serialPortIterator);
static kern_return_t FindModems(io_iterator_t *matchingServices);
static PyObject * osxserialports_modems(PyObject *self, PyObject *args);

static PyObject *
GetModemList(io_iterator_t serialPortIterator)
{
    io_object_t   deviceService;
    int maxPathSize = MAXPATHLEN;

    PyObject *ret = Py_BuildValue("[]");

    /* Iterate across all devices found. */

    while ((deviceService = IOIteratorNext(serialPortIterator)))
    {
        CFTypeRef	bsdIOTTYDeviceAsCFString;
        CFTypeRef	bsdIOTTYBaseNameAsCFString;
        CFTypeRef	bsdIOTTYSuffixAsCFString;
        CFTypeRef	bsdCalloutPathAsCFString;
        CFTypeRef	bsdDialinPathAsCFString;

        Boolean     result;

        char        name[MAXPATHLEN]; /* MAXPATHLEN = 1024 */
        char        base[MAXPATHLEN];
        char        suffix[MAXPATHLEN];
        char        callout[MAXPATHLEN];
        char        dialin[MAXPATHLEN];

        PyObject *d;

        bsdIOTTYDeviceAsCFString = IORegistryEntryCreateCFProperty(deviceService,
                                                            CFSTR(kIOTTYDeviceKey),
                                                            kCFAllocatorDefault,
                                                            0);
        bsdIOTTYBaseNameAsCFString = IORegistryEntryCreateCFProperty(deviceService,
                                                            CFSTR(kIOTTYBaseNameKey),
                                                            kCFAllocatorDefault,
                                                            0);
        bsdIOTTYSuffixAsCFString = IORegistryEntryCreateCFProperty(deviceService,
                                                            CFSTR(kIOTTYSuffixKey),
                                                            kCFAllocatorDefault,
                                                            0);
        bsdCalloutPathAsCFString = IORegistryEntryCreateCFProperty(deviceService,
                                                            CFSTR(kIOCalloutDeviceKey),
                                                            kCFAllocatorDefault,
                                                            0);
        bsdDialinPathAsCFString = IORegistryEntryCreateCFProperty(deviceService,
                                                            CFSTR(kIODialinDeviceKey),
                                                            kCFAllocatorDefault,
                                                            0);

        if (bsdIOTTYDeviceAsCFString)
        {
            result = CFStringGetCString(bsdIOTTYDeviceAsCFString,
                                        name,
                                        maxPathSize,
                                        kCFStringEncodingASCII);
            CFRelease(bsdIOTTYDeviceAsCFString);
        }

        if (bsdIOTTYBaseNameAsCFString)
        {
            result = CFStringGetCString(bsdIOTTYBaseNameAsCFString,
                                        base,
                                        maxPathSize,
                                        kCFStringEncodingASCII);
            CFRelease(bsdIOTTYBaseNameAsCFString);
        }

        if (bsdIOTTYSuffixAsCFString)
        {
            result = CFStringGetCString(bsdIOTTYSuffixAsCFString,
                                        suffix,
                                        maxPathSize,
                                        kCFStringEncodingASCII);
            CFRelease(bsdIOTTYSuffixAsCFString);
        }

        if (bsdCalloutPathAsCFString)
        {
            result = CFStringGetCString(bsdCalloutPathAsCFString,
                                        callout,
                                        maxPathSize,
                                        kCFStringEncodingASCII);
            CFRelease(bsdCalloutPathAsCFString);
        }

        if (bsdDialinPathAsCFString)
        {
            result = CFStringGetCString(bsdDialinPathAsCFString,
                                        dialin,
                                        maxPathSize,
                                        kCFStringEncodingASCII);
            CFRelease(bsdDialinPathAsCFString);
        }

        d = Py_BuildValue("{s:s,s:s,s:s,s:s,s:s}",
                          "name", name,
                          "base", base,
                          "suffix", suffix,
                          "callout", callout,
                          "dialin", dialin);

        if (PyList_Append(ret, d)) {
            Py_DECREF(d);
            goto error;
        } else {
            Py_DECREF(d);
        }
    }

error:
    /* Release the io_service_t now that we are done with it. */
    (void) IOObjectRelease(deviceService);
    return ret;
}

static kern_return_t
FindModems(io_iterator_t *matchingServices)
{
    kern_return_t           kernResult;
    mach_port_t             masterPort;
    CFMutableDictionaryRef  classesToMatch;

    kernResult = IOMasterPort(MACH_PORT_NULL, &masterPort);
    if (KERN_SUCCESS != kernResult)
    {
        /* printf("IOMasterPort returned %d\n", kernResult); */
        goto exit;
    }

    classesToMatch = IOServiceMatching(kIOSerialBSDServiceValue);
    if (classesToMatch != NULL)
    {
        CFDictionarySetValue(classesToMatch,
                             CFSTR(kIOSerialBSDTypeKey),
                             CFSTR(kIOSerialBSDModemType));
    }

    kernResult = IOServiceGetMatchingServices(masterPort, classesToMatch, matchingServices);
    if (KERN_SUCCESS != kernResult)
    {
        /* printf("IOServiceGetMatchingServices returned %d\n", kernResult); */
        goto exit;
    }

exit:
    return kernResult;
}

static PyObject *
osxserialports_modems(PyObject *self, PyObject *args)
{
    kern_return_t kernResult;
    io_iterator_t serialPortIterator;
    PyObject *ret = NULL;

    char *argstring;

    if (!PyArg_ParseTuple(args, "", &argstring)) /* No arguments */
        return NULL;

    kernResult = FindModems(&serialPortIterator);
    ret = GetModemList(serialPortIterator);

    IOObjectRelease(serialPortIterator);  /* Release the iterator. */
    if (EX_OK != kernResult) {
        Py_XDECREF(ret);
        return NULL;
    } else {
        return ret;
    }
}

static PyMethodDef
osxserialportsMethods[] = {
    {"modems", osxserialports_modems, METH_VARARGS,
    "List all serial port modems available on MacOS X."},
    {NULL, NULL, 0, NULL}           /* Sentinel */
};

void
initosxserialports(void)
{
    (void) Py_InitModule("osxserialports", osxserialportsMethods);
}

