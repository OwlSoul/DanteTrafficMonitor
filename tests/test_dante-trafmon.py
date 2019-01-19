import dante_trafmon
from dante_trafmon import basic_test


def test_basic_test():
    ''' Basic test to ensure pytest works'''
    assert basic_test() == "TEST"

#----                        DATABASE CONNECTION TESTS                     ----#

def test_database_not_reachable():
    dante_trafmon.db_name = "danted"
    dante_trafmon.db_username = "danted"
    dante_trafmon.db_host = "10.254.0.254"  # This host is unreachable
    dante_trafmon.db_password = "TestPass8594"

    app =
