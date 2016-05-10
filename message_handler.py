#!/usr/local/env python2

import sys
import os
import select
import fcntl
import errno
import json

errno_block = {errno.EINPROGRESS, errno.EALREADY, errno.EAGAIN, errno.EWOULDBLOCK, errno.EINTR, errno.EDEADLK,
               errno.EBUSY, errno.ENOBUFS, errno.ENOMEM}

errno_fatal = {errno.ECONNABORTED, errno.EPIPE, errno.ECONNREFUSED, errno.EBADF, errno.ESHUTDOWN, errno.ENOTCONN,
               errno.ECONNRESET, errno.ETIMEDOUT, errno.EINVAL}

errno_unavailable = {errno.ECONNREFUSED, errno.EHOSTUNREACH}


def async(fd):
    try:
        fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NONBLOCK)
        return True
    except IOError:
        return False


def sync(fd):
    try:
        fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NDELAY)
        return True
    except IOError:
        return False


if not async(sys.stdin):
    print >> sys.stderr, "could not set stdin/stdout non blocking"
    sys.stderr.flush()
    sys.exit(1)


def _reader():
    received = ''

    while True:
        try:
            data = os.read(sys.stdin.fileno(), 4096)
        except IOError, exc:
            if exc.args[0] in errno_block:
                yield ''
                continue
            elif exc.args[0] in errno_fatal:
                print >> sys.stderr, "fatal error while reading on stdin : %s" % str(exc)
                sys.exit(1)

        received += data
        if '\n' in received:
            line, received = received.split('\n', 1)
            yield line + '\n'
        else:
            yield ''


def read(timeout):
    try:
        r, w, x = select.select([sys.stdin], [], [sys.stdin, ], timeout)  # pylint: disable=W0612
    except IOError, exc:
        if exc.args[0] in errno_block:
            return ''
        elif exc.args[0] in errno_fatal:
            # this may not send anything ...
            print >> sys.stderr, "fatal error during select : %s" % str(exc)
            sys.stderr.flush()
            sys.exit(1)
        else:
            # this may not send anything ...
            print >> sys.stderr, "unexpected error during select : %s" % str(exc)
            sys.stderr.flush()
            sys.exit(1)

    if not r:
        return ''

    line = _reader()

    if not line:
        return ''

    return line

try:
    while True:
        received = read(1.0)
        if received:
            print json.dumps(received)

except Exception:
    sync(sys.stdin)
