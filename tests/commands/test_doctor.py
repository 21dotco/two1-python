""" Doctor command unit tests """
# standard python imports
import subprocess
import time
import unittest.mock as mock

# 3rd party imports
import pytest

# two1 imports
# importing the class directly to get around renaming doctor
from two1.commands.doctor import Check
from two1.commands.doctor import Doctor


@pytest.mark.parametrize("url, return_value, server_port", [
    ("http://0.0.0.0:8000", True, 8000),
    ("http://0.0.0.0:8001", False, 8000),
    ("http://0.0.0.0", False, 8000),
    ("https://0.0.0.0:8000", True, 8000),
    ("https://0.0.0.0", False, 8000),
    ])
def test_make_http_connection(doctor, url, return_value, server_port):
    """ Fires up an http server to check functionality of make_connection """
    server_cmd = "python3 -m http.server {}"
    proc = subprocess.Popen([server_cmd.format(server_port)], shell=True, stdout=subprocess.PIPE)
    time.sleep(.5)
    assert doctor.make_http_connection(url) == return_value
    proc.kill()
    proc.wait()


@pytest.mark.parametrize("checks, expected_length", [
    ({
        "type1": [
            Check("name", "message", "value", Check.Result.PASS),
            Check("name", "message", "value", Check.Result.FAIL),
            Check("name", "message", "value", Check.Result.SKIP),
            Check("name", "message", "value", Check.Result.WARN)]}, 4),
    ({
        "type1": [
            Check("name", "message", "value", Check.Result.FAIL),
            Check("name", "message", "value", Check.Result.FAIL)],
        "type2": [
            Check("name", "message", "value", Check.Result.FAIL),
            Check("name", "message", "value", Check.Result.FAIL)]}, 4),
    ({"type1": []}, 0)])
def test_get_checks(doctor, checks, expected_length):
    """ Ensures the function get_checks is returning a flat list of checks """
    # sets the checks list manually instead of running tests
    doctor.checks = checks

    returned_checks = doctor.get_checks()
    assert isinstance(returned_checks, list)
    assert len(returned_checks) == expected_length


@pytest.mark.parametrize("checks, expected_length, result_filter", [
    ({
        "type1": [
            Check("name", "message", "value", Check.Result.PASS),
            Check("name", "message", "value", Check.Result.FAIL),
            Check("name", "message", "value", Check.Result.SKIP),
            Check("name", "message", "value", Check.Result.WARN)]},
     1,
     Check.Result.PASS),
    ({
        "type1": [
            Check("name", "message", "value", Check.Result.FAIL),
            Check("name", "message", "value", Check.Result.FAIL)],
        "type2": [
            Check("name", "message", "value", Check.Result.FAIL),
            Check("name", "message", "value", Check.Result.FAIL)]},
     0,
     Check.Result.WARN),
    ({
        "type1": [
            Check("name", "message", "value", Check.Result.FAIL),
            Check("name", "message", "value", Check.Result.FAIL)],
        "type2": [
            Check("name", "message", "value", Check.Result.FAIL),
            Check("name", "message", "value", Check.Result.FAIL)]},
     4,
     Check.Result.FAIL),
    ({"type1": []}, 0, Check.Result.PASS),
    ({"type1": []}, 0, "donkey")])
def test_get_checks_with_result_filter(doctor, checks, expected_length, result_filter):
    """ Checks that get_checks returns a flat list of checks and uses a search filter """
    # sets the checks list manually instead of running tests
    doctor.checks = checks

    if not isinstance(result_filter, Check.Result):
        with pytest.raises(ValueError):
            returned_checks = doctor.get_checks(result_filter)
    else:
        returned_checks = doctor.get_checks(result_filter)
        assert isinstance(returned_checks, list)
        assert len(returned_checks) == expected_length


@pytest.mark.parametrize("test_checks", [
    ({
        "type1": [
            Check("name", "message", "value", Check.Result.PASS),
            Check("name", "message", "value", Check.Result.FAIL),
            Check("name", "message", "value", Check.Result.SKIP),
            Check("name", "message", "value", Check.Result.WARN)]}),
    ({
        "type1": [
            Check("name", "message", "value", Check.Result.FAIL),
            Check("name", "message", "value", Check.Result.FAIL)],
        "type2": [
            Check("name", "message", "value", Check.Result.FAIL),
            Check("name", "message", "value", Check.Result.FAIL)]}),
    ({"type1": []})])
def test_to_dict(doctor, test_checks):
    """ Ensures that the Doctor.to_doct is returning the correct dict values
        for all check data members
    """
    # sets the checks list manually instead of running tests
    doctor.checks = test_checks

    doc_dict = doctor.to_dict()
    assert isinstance(doc_dict, dict)
    for check_type in test_checks.keys():
        for check_obj, check_dict in zip(test_checks[check_type], doc_dict[check_type]):
            assert check_obj.name == check_dict["name"]
            assert check_obj.message == check_dict["message"]
            assert check_obj.value == check_dict["value"]
            assert check_obj.result.name == check_dict["result"]


@pytest.mark.integration
def test_doctor_integration(doctor):
    """ Runs the full doctor suite of tests and ensures there are no failures"""
    specialties = Doctor.SPECIALTIES

    # Gets a dict of the types of checks and the functions of that check type as a list
    expected_doctor_checks = {check_type: [] for check_type in specialties.keys()}
    for attr_name in dir(doctor):
        for check_type in specialties.keys():
            if attr_name.startswith("check_{}".format(check_type)) and callable(getattr(doctor, attr_name)):
                expected_doctor_checks[check_type].append(attr_name)

    # runs each of the different checks
    for check_type in expected_doctor_checks.keys():
        doctor.checkup(check_type)

    # gets the results from all checks in dict form
    appointment_results = doctor.to_dict()

    # iterates over all expected checks ensuring they were actually called
    for check_type in expected_doctor_checks.keys():
        expected_check_functions = expected_doctor_checks[check_type]
        actual_check_functions = appointment_results[check_type]
        for check_result in actual_check_functions:
            assert check_result['name'] in expected_check_functions

        assert len(actual_check_functions) == len(expected_check_functions)

    # makes sure there are no failures
    assert len(doctor.get_checks(Check.Result.FAIL)) == 0


@pytest.mark.parametrize('system, release_os, check_status', [
    ('Linux', '4.0.0', Check.Result.PASS),
    ('Darwin', '14.5.0', Check.Result.PASS),
])
def test_doctor_operating_system_check(doctor, system, release_os, check_status):
    """ Unit test the ability to check the user's operating system."""
    with mock.patch('platform.system', mock.Mock(return_value=system)), mock.patch('platform.release', mock.Mock(return_value=release_os)):  # nopep8
        status, _, actual_os = doctor.check_general_operating_system_release()
    assert status == check_status
    assert actual_os == release_os
