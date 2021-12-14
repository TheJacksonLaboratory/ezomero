import pytest
import os
import ezomero
from pathlib import Path


def test_connect_params(omero_params, tmp_path, monkeypatch):
    user, password, host, web_host, port, secure = omero_params

    # params should override environment variables
    monkeypatch.setenv("OMERO_USER", 'fail')
    monkeypatch.setenv("OMERO_PASS", 'fail')
    monkeypatch.setenv("OMERO_GROUP", 'fail')
    monkeypatch.setenv("OMERO_HOST", 'fail')
    monkeypatch.setenv("OMERO_PORT", 'fail')
    monkeypatch.setenv("OMERO_SECURE", 'fail')

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


def test_connect_env(omero_params, tmp_path, monkeypatch):
    user, password, host, web_host, port, secure = omero_params
    monkeypatch.setenv("OMERO_USER", user)
    monkeypatch.setenv("OMERO_PASS", password)
    monkeypatch.setenv("OMERO_HOST", host)
    monkeypatch.setenv("OMERO_PORT", port)
    monkeypatch.setenv("OMERO_SECURE", 'True')

    # env should override config file
    conf_txt = ("[DEFAULT]\n"
                "omero_user = fail\n"
                "omero_group = fail\n"
                "omero_host = fail\n"
                "omero_port = 9999\n"
                "omero_secure = True\n")

    # test sanitizing input
    with pytest.raises(TypeError):
        conn = ezomero.connect(config_path=100)
    with pytest.raises(ValueError):
        conn = ezomero.connect(group='', secure='dunno')

    conf_path = Path.home() / '.ezomero'
    conf_path.write_text(conf_txt)

    # test no input to config path defaulting to home
    conn = ezomero.connect(group='')
    assert conn.getUser().getName() == user
    conn.close()

    conf_path = tmp_path / '.ezomero'
    conf_path.write_text(conf_txt)
    conn = ezomero.connect(group='', config_path=str(tmp_path))
    assert conn.getUser().getName() == user
    conn.close()
    conn = ezomero.connect(user='fake_user')
    assert conn is None


def test_connect_config(omero_params, tmp_path):
    user, password, host, web_host, port, secure = omero_params
    conf_txt = ("[DEFAULT]\n"
                f"omero_user = {user}\n"
                "omero_group = \n"
                f"omero_host = {host}\n"
                f"omero_port = {port}\n"
                "omero_secure = True\n")
    conf_path = tmp_path / '.ezomero'
    conf_path.write_text(conf_txt)
    conn = ezomero.connect(password=password, config_path=str(tmp_path))
    assert conn.getUser().getName() == user
    conn.close()


def test_store_conn_params(omero_params, tmp_path):
    user, password, host, web_host, port, secure = omero_params
    ezomero.store_connection_params(user=user, group="", host=host, port=port,
                                    secure=True, config_path=str(tmp_path))
    conn = ezomero.connect(password=password, config_path=str(tmp_path))
    assert conn.getUser().getName() == user
    conn.close()
    with pytest.raises(KeyError):
        _, _, _ = \
            ezomero.json_api.create_json_session(password=password,
                                                 config_path=str(tmp_path))
    os.remove(tmp_path / '.ezomero')
    ezomero.store_connection_params(user=user, group="", host=host, port=port,
                                    secure=True, web_host=web_host,
                                    config_path=str(tmp_path))
    login_rsp, session, base_url = \
        ezomero.json_api.create_json_session(password=password,
                                             config_path=str(tmp_path))
    assert login_rsp['success']
