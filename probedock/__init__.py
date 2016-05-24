#!/usr/bin/python

"""
This is a reporter for unittests to send results to ProbeDock.io
"""

import platform
import os
import re
import requests
import yaml
from collections import namedtuple


__author__ = "Benjamin Schubert <ben.c.schubert@gmail.com>"
__version__ = "0.1.0"


PROBEDOCK_CONFIG = "PROBEDOCK_CONFIG"
PROBEDOCK_PUBLISH = "PROBEDOCK_PUBLISH"


REMOVE_PARENTHESIS_REGEX = re.compile("[()]")


class ProbedockUploadFailedException(Exception):
    """
    Exception thrown when the upload of data to probedock fails

    :param url: url of the probedock server
    :param status_code: status code received from the server
    :param content: content of the answer
    """
    def __init__(self, url, status_code, content):
        self.url = url
        self.status_code = status_code
        self.content = content

    def __str__(self):
        return "Could not upload data to {}. Got error {}\n With answer : \n\n{}\n".format(
            self.url, self.status_code, self.content)


# noinspection PyMethodMayBeStatic,PyPep8Naming
class ProbeDockReporter:
    """
    TestResult reporter for Probedock.io

    :param category: category for the tests
    """
    class ProbeDockDisabledException(Exception):
        """
        Exception raised to signal that Probedock should be disabled
        """

    __configuration__ = namedtuple("configuration", ["data", "url", "headers"])
    probedock_main_configuration = os.environ.get(PROBEDOCK_CONFIG, os.path.expanduser("~/.probedock/config.yml"))

    def __init__(self, category):
        self.category = category
        self.configuration = self.load_configuration()
        self.tests = []

    @staticmethod
    def _get_context():
        """
        get information about the system we are running on

        :return: dictionary with system information
        """
        return {
            "os.architecture": platform.architecture()[0],
            "os.name": platform.system(),
            "os.version": platform.uname()[2],
            "python.implementation": platform.python_implementation(),
            "python.version": platform.python_version(),
            "python.compiler": platform.python_compiler()
        }

    def _get_test_namespace(self, test):
        """
        gets the namespace of the test (package + class normally)

        :param test: test for which to extract namespace
        :return: namespace of the test
        """
        return re.sub(REMOVE_PARENTHESIS_REGEX, "", str(test)).split(" ")[1]

    def _get_test_id(self, test):
        """
        get the test's uuid

        :param test: test for which to get the uuid
        :return: the test's uuid
        """
        return test.id()

    def _get_test_class(self, test):
        """
        get the test's class

        :param test: test for which to get the class
        :return: class of the test
        """
        return test.__class__.__name__

    def _get_test_method(self, test):
        """
        get the test's method name

        :param test: test for which to get the method name
        :return: the test's name
        """
        # noinspection PyProtectedMember
        return test._testMethodName

    def _get_test_module(self, test):
        """
        get the test module

        :param test: test for which to get the module name
        :return: the module of the test
        """
        return ".".join(test.id().split(".")[:-2])

    def _add_test(self, test, time_taken):
        """
        Add the given test to the results

        :param test: test to add to the list
        :param time_taken: time taken by the test to run
        :return: dict representing information about the test
        """
        t = {
            "a": {
                "fingerprint": self._get_test_id(test),
                "python.class": self._get_test_class(test),
                "python.method": self._get_test_method(test),
                "python.package": self._get_test_module(test)
            },
            "c": "unittest",
            "d": int(time_taken * 1000),
            "f": self._get_test_id(test),
            "g": [],
            "n": self._get_test_namespace(test) + ": " + self._get_test_method(test),
            "o": [],
            "p": True,
            "t": []
        }

        self.tests.append(t)
        return t

    def _add_test_with_traceback(self, test, time_taken, traceback):
        """
        adds a failing test to the report

        :param test: TestCase to add
        :param time_taken: time taken by the test to run
        :param traceback: test error nicely formatted
        :return: the test data
        """
        t = self._add_test(test, time_taken)
        t["m"] = traceback
        return t

    @staticmethod
    def _set_failing(test):
        """
        Sets the test given in parameter as failing

        :param test: test to mark as failing
        :return: the test given in parameter, failing
        """
        test["p"] = False
        return test

    @staticmethod
    def _set_skipped(test):
        """
        Sets the test given in parameter as skipped

        :param test: test to mark as skipped
        :return: the test given in parameter, skipped
        """
        test["v"] = False
        return test

    def addSuccess(self, test, time_taken):
        """
        adds a successful test to the list

        :param test: test to add
        :param time_taken: time taken by the test to run
        """
        self._add_test(test, time_taken)

    def addFailure(self, test, time_taken, traceback):
        """
        Add a failed test to the list

        :param test: test to add
        :param time_taken: time taken by the test to run
        :param traceback: test error already formatted
        """
        self._set_failing(self._add_test_with_traceback(test, time_taken, traceback))

    def addError(self, test, time_taken, traceback):
        """
        Add a test with error to the list

        :param test: test to add
        :param time_taken: time taken by the test to run
        :param traceback: test error already formatted
        """
        self._set_failing(self._add_test_with_traceback(test, time_taken, traceback))

    def addSkip(self, test, time_taken, reason):
        """
        Add a test that has been skipped to the list

        :param test: test to add
        :param time_taken: time taken by the test to run
        :param reason: why the test was skipped
        """
        # FIXME : use reason
        self._set_skipped(self._add_test(test, time_taken))

    def addExpectedFailure(self, test, time_taken, traceback):
        """
        Add an expected failure to the list

        :param test: test to add
        :param time_taken: time taken by the test to run
        :param traceback: test error already formatted
        """
        self._add_test_with_traceback(test, time_taken, traceback)

    def addUnexpectedSuccess(self, test, time_taken):
        """
        Add a test that should have failed but didn't to the list

        :param test: test to add
        :param time_taken: time taken by the test to run
        """
        self._set_failing(self._add_test(test, time_taken))

    def load_configuration(self):
        """
        Loads the complete ProbeDock configuration and returns a correctly formatted data
        to send it easily to ProbeDock

        :raises ProbeDockDisabledException: if tests should not be published
        :return: configuration to send to ProbeDock
        """
        with open(os.path.join(os.getcwd(), "probedock.yml")) as f:
            local_config = yaml.safe_load(f.read())

        with open(self.probedock_main_configuration) as f:
            global_config = yaml.safe_load(f.read())

        if (not global_config.get("publish", False)) or (os.environ.get(PROBEDOCK_PUBLISH, "1") == "0"):
            raise self.ProbeDockDisabledException()

        url = global_config["servers"][local_config["server"]]["apiUrl"] + "/publish"
        headers = {
            "Content-Type": "application/vnd.probe-dock.payload.v1+json; charset=UTF-8",
            "Authorization": "Bearer " + global_config["servers"][local_config["server"]]["apiToken"]
        }
        data = {
            "context": self._get_context(),
            "version": local_config["project"]["version"],
            "projectId": local_config["project"]["apiId"],
            "probe": {"name": "unittest.py", "version": __version__},
        }

        return self.__configuration__(data=data, url=url, headers=headers)

    def send_report(self, total_time):
        """
        Send the test results to the server

        :param total_time: time taken to run all the tests
        """
        self.configuration.data["duration"] = int(total_time * 1000)
        self.configuration.data["results"] = self.tests

        request = requests.post(url=self.configuration.url, json=self.configuration.data,
                                headers=self.configuration.headers)

        if request.status_code != requests.codes.accepted:
            raise ProbedockUploadFailedException(self.configuration.url, request.status_code, request.content)

        return self.configuration.url[:self.configuration.url.rindex("/")]
