import argparse
import sys
import time
import urllib2
import urlparse
import ifuzz_logger

import sex


HELP_TEXT = 'Send reset command to ezOutlet EZ-11b device.'


def _get_url(hostname, path):
    return urlparse.urlunparse(('http', hostname, path, '', '', ''))


class EzOutletReset:
    """Uses ezOutlet EZ-11b to reset a device.

    Uses the ezOutlet EZ-11b Internet IP-Enabled Remote Power Reboot Switch to
    reset a device under test (DUT).

    In addition to reset(), post_fail() is provided, meant to be given as a
    callback to a Session object.

    It uses undocumented but simple CGI scripts.
    """
    DEFAULT_RESET_DELAY = 3.05
    DEFAULT_TIMEOUT = 30
    DEFAULT_WAIT_TIME = 0
    RESET_URL_PATH = '/reset.cgi'
    EXPECTED_RESPONSE_CONTENTS = '0,0'
    NO_RESPONSE_MSG = "No response from EzOutlet. timeout value: {0}"
    UNEXPECTED_RESPONSE_MSG = ("Unexpected response from EzOutlet. Expected: " +
                               repr(EXPECTED_RESPONSE_CONTENTS) +
                               " Actual: {0}")
    LOG_REQUEST_MSG = 'HTTP GET {0}'

    def __init__(self, hostname, wait_time=0, timeout=DEFAULT_TIMEOUT, reset_delay=DEFAULT_RESET_DELAY):
        """
        Args:
            hostname: Hostname or IP address of device.
            wait_time: Time in seconds to allow the device being reset
                to reboot. See also reset_delay.
            timeout: Time in seconds to wait for the EzOutlet to respond.
            reset_delay: Time the EzOutlet waits before switching back on.
        """
        self._hostname = hostname
        self._dut_reset_time = wait_time
        self._timeout = timeout
        self._reset_delay = reset_delay

    @property
    def url(self):
        return _get_url(self._hostname, self.RESET_URL_PATH)

    def post_fail(self, logger, *args, **kwargs):
        """Call reset() and log actions.

        See reset() docstring for details.

        This method will log actions associated with HTTP communication. It
        assumes that a test step is already opened.

        Args:
            logger (ifuzz_logger.IFuzzLogger):
                For logging communications with outlet device.
            *args: Kept for forward-compatibility.
            **kwargs: Kept for forward-compatibility.

        Raises:
            sex.SulleyRuntimeError: If the reset fails due to:
                - no response in self._timeout seconds or
                - unexpected response contents (see
                  EzOutletReset.EXPECTED_RESPONSE_CONTENTS)
        """
        _ = args  # only for forward-compatibility
        _ = kwargs  # only for forward-compatibility

        logger.log_info(self.LOG_REQUEST_MSG.format(self.url))

        try:
            response = self.reset()
            logger.log_recv(response)
        except sex.SullyRuntimeError as e:
            logger.log_info(e.message)
            raise

    def reset(self):
        """Send reset request to ezOutlet, check response, wait for reset.

        After sending HTTP request and receiving response, wait
        self._reset_delay + self._dut_reset_time seconds.

        If the outlet does not respond (after self._timeout seconds), or gives
        an unexpected response, this method will raise an exception.

        Returns: HTTP response contents.

        Raises:
            sex.SulleyRuntimeError: If the reset fails due to:
                - no response in self._timeout seconds or
                - unexpected response contents (see
                  EzOutletReset.EXPECTED_RESPONSE_CONTENTS)
        """
        response = self._http_get(self.url)

        self._check_response_raise_if_unexpected(response)

        self._wait_for_reset()

        return response

    def _http_get(self, url):
        """HTTP GET and return response.

        Args:
            url: Target to GET.

        Returns: Response contents.

        Raises:
            sex.SulleyRuntimeError: If the reset fails due to:
                - no response in self._timeout seconds
        """
        try:
            return urllib2.urlopen(url, timeout=self._timeout).read()
        except urllib2.URLError:
            raise sex.SullyRuntimeError(self.NO_RESPONSE_MSG.format(self._timeout)), \
                None, \
                sys.exc_info()[2]

    def _check_response_raise_if_unexpected(self, response):
        """Raise if response is unexpected.

        Args:
            response: Response.

        Returns: None
        """
        if response != self.EXPECTED_RESPONSE_CONTENTS:
            raise sex.SullyRuntimeError(self.UNEXPECTED_RESPONSE_MSG.format(response))

    def _wait_for_reset(self):
        """Sleep for self._reset_delay + self._dut_reset_time.

        Returns: None
        """
        time.sleep(self._reset_delay + self._dut_reset_time)

HELP_TEXT_TARGET_ARG = 'IP address/hostname of ezOUtlet device.'
HELP_TEXT_RESET_TIME_ARG = 'Time in seconds to wait for UUT to reset.' \
                     ' Note that the script already waits {0} seconds for the' \
                     ' ezOutlet to turn off and on.'.format(EzOutletReset.DEFAULT_RESET_DELAY)
RESET_TIME_ARG_SHORT = '-t'
RESET_TIME_ARG_LONG = '--reset-time'


def parse_args(argv):
    parser = argparse.ArgumentParser(description=HELP_TEXT)
    parser.add_argument('target', help=HELP_TEXT_TARGET_ARG)
    parser.add_argument(RESET_TIME_ARG_LONG, RESET_TIME_ARG_SHORT,
                        type=float,
                        default=0,
                        help=HELP_TEXT_RESET_TIME_ARG)
    return parser.parse_args(argv[1:])


def main(argv):
    parsed_args = parse_args(argv)
    ez_outlet = EzOutletReset(hostname=parsed_args.target,
                              wait_time=parsed_args.reset_time)
    ez_outlet.reset()


if __name__ == "__main__":
    main(sys.argv)
