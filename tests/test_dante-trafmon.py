import dante_trafmon

def test_initial():
    """Most basic test to ensure pytest DEFINITELY works with this configuration"""
    assert True == True

def test_basic():
    """Basic test to ensure pytest works"""
    app = dante_trafmon.Application()
    assert app.basic_test() == "TEST"

#----                        DATABASE CONNECTION TESTS                     ----#

def test_database_not_reachable_at_start():
    """Behaviour if database is not reachable at start"""
    app = dante_trafmon.Application()
    app.dante_thread = dante_trafmon.LogThread(name="DANTE",
                                               log_type=dante_trafmon.LogThread.LOG_TYPE_DANTE,
                                               application=app)
    app.dante_thread.timer_thread = dante_trafmon.TimerThread(log_thread=app.dante_thread,
                                                              application=app)

    app.db_hostname = "10.254.254.254"
    app.db_name = "danted"
    app.db_username = "danted"
    app.db_password = "TestPass8594"
    result, result_msg = app.dante_thread.timer_thread.data_init_from_db()
    assert result == 1

def test_server_does_not_have_pgsql():
    """Behaviour if database is reachable but isn't serving"""
    app = dante_trafmon.Application()
    app.dante_thread = dante_trafmon.LogThread(name="DANTE",
                                               log_type=dante_trafmon.LogThread.LOG_TYPE_DANTE,
                                               application=app)
    app.dante_thread.timer_thread = dante_trafmon.TimerThread(log_thread=app.dante_thread,
                                                              application=app)

    app.db_hostname = "127.0.0.2"
    app.db_name = "danted"
    app.db_username = "danted"
    app.db_password = "TestPass8594"
    result, result_msg = app.dante_thread.timer_thread.data_init_from_db()
    assert result == 1
