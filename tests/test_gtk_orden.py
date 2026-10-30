# -*- coding: utf-8 -*-
import pytest

pytest.importorskip("gi")

from app.gtk.datos import Nodo  # noqa: E402
from app.gtk.orden_arbol import _intercambiar, _reordenar_en_sitio  # noqa: E402


def test_intercambiar_con_el_vecino_visible():
    # 'x' es una clave de la otra interfaz que no se ve: el intercambio salta por encima sin tocarla
    assert _intercambiar(["a", "x", "b", "c"], ["a", "b", "c"], "b", True) == ["b", "x", "a", "c"]
    assert _intercambiar(["a", "b"], ["a", "b", "c"], "b", False) == ["a", "c", "b"]


def test_intercambiar_en_los_extremos():
    assert _intercambiar(["a", "b"], ["a", "b"], "a", True) is None
    assert _intercambiar(["a", "b"], ["a", "b"], "b", False) is None
    assert _intercambiar(["a", "b"], ["a", "b"], "z", True) is None


def test_reordenar_respeta_los_huecos_de_lo_demas():
    nodos = [Nodo(k, "timeline", servicio="mastodon", timeline=k) for k in ("home", "local", "mentions")]
    nodos.insert(1, Nodo("hilo", "timeline", servicio="mastodon", timeline="thread:1", cerrable=True))
    _reordenar_en_sitio(nodos, lambda n: None if n.cerrable else n.timeline, ["mentions", "home", "local"])
    assert [n.timeline for n in nodos] == ["mentions", "thread:1", "home", "local"]
