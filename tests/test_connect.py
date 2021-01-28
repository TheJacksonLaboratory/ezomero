import pytest
import ezomero


def test_connection_params(omero_params, tmp_path, monkeypatch):
    # this should just work
    user, password, host, port, secure = omero_params
    conn = ezomero.connect(user, password, host=host, group='', port=port,
                           secure=True, config_path=str(tmp_path))
    assert conn.getUser().getName() == user
    conn.close()

    # params should override environment variables
    monkeypatch.setenv("OMERO_USER", 'fail')
    monkeypatch.setenv("OMERO_PASS", 'fail')
    monkeypatch.setenv("OMERO_GROUP", 'fail')
    monkeypatch.setenv("OMERO_HOST", 'fail')
    monkeypatch.setenv("OMERO_PORT", 'fail')
    monkeypatch.setenv("OMERO_SECURE", 'fail')
    conn = ezomero.connect(user, password, host=host, group='', port=port,
                           secure=True, config_path=str(tmp_path))
    assert conn.getUser().getName() == user
    conn.close()

    # params should override config file
    conf_txt = ("[DEFAULT]\n"
                "omero_user = fail\n"
                "omero_group = fail\n"
                "omero_host = fail\n"
                "omero_port = 9999\n"
                "omero_secure = True\n")
    conf_path = tmp_path / '.ezomero'
    conf_path.write_text(conf_txt)
    conn = ezomero.connect(user, password, host=host, group='', port=port,
                           secure=True, config_path=str(tmp_path))
    assert conn.getUser().getName() == user
    conn.close()


def test_connection_env(omero_params, tmp_path, monkeypatch):
    # this should just work
    user, password, host, port, secure = omero_params
    monkeypatch.setenv("OMERO_USER", user)
    monkeypatch.setenv("OMERO_PASS", password)
    monkeypatch.setenv("OMERO_HOST", host)
    monkeypatch.setenv("OMERO_PORT", port)
    monkeypatch.setenv("OMERO_SECURE", 'True')
    conn = ezomero.connect(group='')
    assert conn.getUser().getName() == user
    conn.close()
