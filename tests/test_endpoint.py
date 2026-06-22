import pytest

from custom_components.solisart.api.endpoint import EndpointStrategy


def test_local_only():
    s = EndpointStrategy("local", "http://192.0.2.1", None)
    assert s.candidates() == ["http://192.0.2.1"]

def test_cloud_only():
    s = EndpointStrategy("cloud", None, "https://my.solisart.fr")
    assert s.candidates() == ["https://my.solisart.fr"]

def test_fallback_prefers_local():
    s = EndpointStrategy("fallback", "http://192.0.2.1", "https://my.solisart.fr")
    assert s.candidates() == ["http://192.0.2.1", "https://my.solisart.fr"]

def test_fallback_with_only_local_is_valid():
    s = EndpointStrategy("fallback", "http://192.0.2.1", None)
    assert s.candidates() == ["http://192.0.2.1"]

def test_invalid_mode_raises():
    with pytest.raises(ValueError):
        EndpointStrategy("nonsense", "http://x", None).candidates()

def test_local_without_local_url_raises():
    with pytest.raises(ValueError):
        EndpointStrategy("local", None, None).candidates()
