import pytest
import requests
import numpy as np
from ezomero import json_api, store_connection_params
from ezomero import get_image_ids, get_image
from pathlib import Path


def test_connect_params(omero_params, tmp_path, monkeypatch):
    user, password, host, web_host, port, secure = omero_params

    # params should override environment variables
    monkeypatch.setenv("OMERO_USER", 'fail')
    monkeypatch.setenv("OMERO_PASS", 'fail')
    monkeypatch.setenv("OMERO_WEB_HOST", 'fail')

    # params should override config file
    conf_txt = ("[JSON]\n"
                "omero_user = fail\n"
                "omero_web_host = fail\n")
    conf_path = tmp_path / '.ezomero'
    conf_path.write_text(conf_txt)

    login_rsp, session, base_url = json_api.create_json_session(
                                        user, password, web_host=web_host,
                                        config_path=str(tmp_path))
    r = session.get(base_url)
    assert login_rsp['success']
    assert base_url is not None
    assert r.status_code == 200


def test_connect_env(omero_params, tmp_path, monkeypatch):
    user, password, host, web_host, port, secure = omero_params
    monkeypatch.setenv("OMERO_USER", user)
    monkeypatch.setenv("OMERO_PASS", password)
    monkeypatch.setenv("OMERO_WEB_HOST", web_host)

    # env should override config file
    conf_txt = ("[JSON]\n"
                "omero_user = fail\n"
                "omero_web_host = fail\n")

    # test sanitizing input
    with pytest.raises(TypeError):
        login_rsp, session, base_url = json_api.create_json_session(
                                        config_path=100)

    conf_path = Path.home() / '.ezomero'
    conf_path.write_text(conf_txt)

    # test no input to config path defaulting to home
    login_rsp, session, base_url = json_api.create_json_session()
    assert login_rsp['success']

    conf_path = tmp_path / '.ezomero'
    conf_path.write_text(conf_txt)
    login_rsp, session, base_url = json_api.create_json_session(
                                        config_path=str(tmp_path))
    assert login_rsp['success']
    with pytest.raises(requests.exceptions.HTTPError):
        login_rsp, session, base_url = json_api.create_json_session(
                                        user='fake_user')


def test_connect_config(omero_params, tmp_path):
    user, password, host, web_host, port, secure = omero_params
    conf_txt = ("[JSON]\n"
                f"omero_user = {user}\n"
                f"omero_web_host = {web_host}\n")
    conf_path = tmp_path / '.ezomero'
    conf_path.write_text(conf_txt)
    login_rsp, session, base_url = json_api.create_json_session(
                                        password=password,
                                        config_path=str(tmp_path))
    assert login_rsp['success']


def test_store_conn_params(omero_params, tmp_path):
    user, password, host, web_host, port, secure = omero_params
    store_connection_params(user=user, group="", host=host, port=port,
                            secure=True, web_host=web_host,
                            config_path=str(tmp_path))
    login_rsp, session, base_url = json_api.create_json_session(
                                        password=password,
                                        config_path=str(tmp_path))
    assert login_rsp['success']


def test_get_rendered_jpegs(omero_params, conn, pyramid_fixture):
    user, password, host, web_host, port, secure = omero_params
    pyr_id = get_image_ids(conn)[-1]
    img, pix = get_image(conn, pyr_id)
    login_rsp, session, base_url = json_api.create_json_session(
                                        user, password, web_host=web_host)
    with pytest.raises(TypeError):
        jpeg = json_api.get_rendered_jpeg('test', base_url, pyr_id, 1)
    with pytest.raises(TypeError):
        jpeg = json_api.get_rendered_jpeg(session, 10, pyr_id, 1)
    with pytest.raises(TypeError):
        jpeg = json_api.get_rendered_jpeg(session, base_url, 'test', 1)
    with pytest.raises(TypeError):
        jpeg = json_api.get_rendered_jpeg(session, base_url, pyr_id, '1')

    with pytest.raises(requests.exceptions.HTTPError):
        jpeg = json_api.get_rendered_jpeg(session, base_url, 99999, 1)
    with pytest.raises(requests.exceptions.ConnectionError):
        jpeg = json_api.get_rendered_jpeg(session,
                                          'http://messedupbaseurl', 99999, 1)

    jpeg = json_api.get_rendered_jpeg(session, base_url, pyr_id, 1)
    assert np.shape(pix)[2] == np.shape(jpeg)[0]  # xdim = xdim
    assert np.shape(pix)[3] == np.shape(jpeg)[1]  # ydim = ydim
    assert np.shape(jpeg)[2] == 3  # RGB image

    jpeg = json_api.get_rendered_jpeg(session, base_url, pyr_id, 3.0)
    assert round(np.shape(pix)[2]/3) == np.shape(jpeg)[0]
    assert round(np.shape(pix)[3]/3) == np.shape(jpeg)[1]
    assert np.shape(jpeg)[2] == 3
