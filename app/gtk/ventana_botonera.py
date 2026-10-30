# -*- coding: utf-8 -*-
"""Botonera de acciones bajo la lista (mixin de VentanaPrincipal).

Opcional, como en Windows: se activa por red en Preferencias (`<red>.show_action_buttons`; la bandeja tiene la suya,
`inbox.show_action_buttons`). Los botones cambian con el elemento enfocado y sus etiquetas reflejan el estado («Me gusta» o
«Quitar me gusta»). Cada uno activa la misma acción de la ventana que el menú y los atajos, así que en la bandeja actúan sobre
la red de origen de la fila. El último abre el menú contextual completo.

Se llega a ella con Tab desde la lista; Izquierda y Derecha pasan de un botón a otro."""

import logging

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gdk, Gtk  # noqa: E402

from app.core.config_manager import config

log = logging.getLogger(__name__)

# Redes que tienen casilla en Preferencias (clave de configuración -> nombre).
REDES_BOTONERA = (("rss", "RSS"), ("mastodon", "Mastodon"), ("bluesky", "Bluesky"), ("wsocial", "W Social"),
                  ("x", "X"), ("telegram", "Telegram"), ("reddit", "Reddit"), ("peertube", "PeerTube"),
                  ("inbox", "la bandeja de entrada"))
_ESTADOS = ("leido", "favorito", "mas_tarde", "impulsado", "marcador")


def botones_de_fila(obj, servicio: str):
    """[(etiqueta, acción de la ventana)] de las acciones más usadas sobre una fila, según su red y lo que sea."""
    f = obj.fila
    tipo = f.extra.get("tipo", "")
    mas = (_("Más acciones…"), "win.menu-contextual")
    solo = [(_("Acciones…"), "win.menu-contextual")]
    if servicio in ("mastodon", "bluesky", "wsocial", "x"):
        if tipo not in ("estado", "notificacion"):
            return solo
        if servicio == "mastodon":
            fav, imp = _("Quitar favorito") if obj.favorito else _("Favorito"), \
                _("Quitar impulso") if obj.impulsado else _("Impulsar")
        elif servicio == "x":
            fav, imp = _("Quitar me gusta") if obj.favorito else _("Me gusta"), \
                _("Deshacer retweet") if obj.impulsado else _("Retweet")
        else:
            fav, imp = _("Quitar me gusta") if obj.favorito else _("Me gusta"), \
                _("Deshacer repost") if obj.impulsado else _("Repostear")
        botones = [(_("Responder"), "win.responder"), (fav, "win.me-gusta")]
        if not (servicio == "mastodon" and f.extra.get("visibilidad") == "direct"):
            botones.append((imp, "win.impulsar"))
        return botones + [(_("Conversación"), "win.conversacion"), mas]
    if servicio == "reddit":
        if tipo not in ("post", "comentario"):
            return solo
        botones = [(_("Voto +"), "win.me-gusta"), (_("Voto -"), "win.voto-negativo"),
                   (_("Quitar guardado") if obj.marcador else _("Guardar"), "win.marcador"), (_("Responder"), "win.responder")]
        if tipo == "post":
            botones.append((_("Comentarios"), "win.conversacion"))
        return botones + [mas]
    if servicio == "peertube":
        if tipo in ("notificacion", "lista", "canal"):
            return solo
        return [(_("Reproducir"), "win.reproducir"), (_("Ver detalles"), "win.pt-detalles"),
                (_("Abrir en el navegador"), "win.navegador"), mas]
    if servicio == "telegram":
        if tipo == "chat":
            return [(_("Abrir conversación"), "win.abrir-chat")] + solo
        return [(_("Responder"), "win.responder")] + solo
    if servicio == "rss":
        return [(_("Marcar no leído") if obj.leido else _("Marcar leído"), "win.leido"),
                (_("Quitar destacado") if obj.favorito else _("Destacar"), "win.favorito"),
                (_("Quitar de leer más tarde") if obj.mas_tarde else _("Leer más tarde"), "win.mas-tarde")] + solo
    return solo


class _BotoneraMixin:
    def _crear_botonera(self):
        self.botonera = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, margin_top=4, margin_bottom=4,
                                margin_start=6, margin_end=6, visible=False, accessible_role=Gtk.AccessibleRole.GROUP)
        self.botonera.update_property([Gtk.AccessibleProperty.LABEL], [_("Acciones del elemento")])
        self._botonera_firma = None
        self._botonera_timer = 0
        self._botonera_obj = None
        self._botonera_ids = []
        ctl = Gtk.EventControllerKey()
        ctl.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        ctl.connect("key-pressed", self._on_tecla_botonera)
        self.botonera.add_controller(ctl)
        return self.botonera

    # ------------------------------------------------------------------ cuándo se ve
    def _botonera_activada(self) -> bool:
        n = self.nodo_actual
        if n is None:
            return False
        clave = "inbox" if n.servicio == "bandeja" else n.servicio
        return bool(config.get(clave, "show_action_buttons", False))

    def programar_botonera(self, *_a):
        """Rehace la botonera cuando el usuario se detiene (al recorrer la lista no se reconstruye en cada paso)."""
        if self._botonera_timer:
            GLib.source_remove(self._botonera_timer)
        self._botonera_timer = GLib.timeout_add(120, self._actualizar_botonera)

    def _vigilar_fila_botonera(self, obj):
        """Si cambia el estado de la fila enfocada (me gusta, leído...), las etiquetas de los botones cambian con él."""
        if obj is self._botonera_obj:
            return
        if self._botonera_obj is not None:
            for i in self._botonera_ids:
                self._botonera_obj.disconnect(i)
        self._botonera_obj, self._botonera_ids = obj, []
        if obj is not None:
            self._botonera_ids = [obj.connect(f"notify::{p}", self.programar_botonera) for p in _ESTADOS]

    def _actualizar_botonera(self):
        self._botonera_timer = 0
        obj = self._fila_actual()
        self._vigilar_fila_botonera(obj)
        if obj is None or not self._botonera_activada():
            self.botonera.set_visible(False)
            self._botonera_firma = None
            return GLib.SOURCE_REMOVE
        servicio = obj.fila.servicio
        botones = botones_de_fila(obj, servicio)
        firma = tuple(b[1] for b in botones)
        existentes = self._botones_botonera()
        if firma == self._botonera_firma and len(existentes) == len(botones):
            for w, (et, _ac) in zip(existentes, botones):       # mismas acciones: solo cambia el texto, el foco se queda
                if w.get_label() != et:
                    w.set_label(et)
        else:
            foco = next((i for i, w in enumerate(existentes) if w.has_focus()), None)
            for w in existentes:
                self.botonera.remove(w)
            for et, ac in botones:
                b = Gtk.Button(label=et)
                b.connect("clicked", lambda _b, a=ac: self.activate_action(a, None))
                self.botonera.append(b)
            self._botonera_firma = firma
            if foco is not None:
                nuevos = self._botones_botonera()
                if nuevos:
                    nuevos[min(foco, len(nuevos) - 1)].grab_focus()
        self.botonera.set_visible(bool(botones))
        return GLib.SOURCE_REMOVE

    def _botones_botonera(self):
        res, w = [], self.botonera.get_first_child()
        while w is not None:
            res.append(w)
            w = w.get_next_sibling()
        return res

    # ------------------------------------------------------------------ teclado
    def _on_tecla_botonera(self, ctl, keyval, keycode, estado):
        if keyval not in (Gdk.KEY_Left, Gdk.KEY_Right) or estado & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.ALT_MASK):
            return False
        botones = self._botones_botonera()
        actual = next((i for i, w in enumerate(botones) if w.has_focus()), None)
        if actual is None:
            return False
        j = actual + (1 if keyval == Gdk.KEY_Right else -1)
        if 0 <= j < len(botones):
            botones[j].grab_focus()
        return True

    def botonera_con_foco(self) -> bool:
        foco = self.get_focus()
        return foco is not None and (foco is self.botonera or foco.is_ancestor(self.botonera))

    def enfocar_botonera(self) -> bool:
        botones = self._botones_botonera()
        if not self.botonera.get_visible() or not botones:
            return False
        botones[0].grab_focus()
        return True
