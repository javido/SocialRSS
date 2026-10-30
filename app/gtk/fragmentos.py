# -*- coding: utf-8 -*-
"""Fragmentos de texto reutilizables: Ctrl+Mayús+J en un campo de redacción inserta uno de los guardados. Se guardan en
`general/snippets` de la configuración, los mismos que usa la versión de Windows."""

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from app.core.config_manager import config
from app.core.speech import notificar


def obtener_fragmentos() -> list:
    datos = config.get("general", "snippets", [])
    return [d for d in datos if isinstance(d, dict) and d.get("texto")]


def instalar_fragmentos(vista: Gtk.TextView):
    """Activa Ctrl+Mayús+J en un campo de redacción. Llamar una vez por campo."""
    if vista is None or getattr(vista, "_fragmentos_instalado", False):
        return
    vista._fragmentos_instalado = True

    def _insertar(*_a):
        if not obtener_fragmentos():
            notificar(_("No tienes fragmentos guardados. Créalos desde Herramientas → «Fragmentos de texto»."))
            return True
        from .dialogos_herramientas import DialogoElegirFragmento

        def _poner(texto):
            buf = vista.get_buffer()
            buf.delete_selection(True, True)
            buf.insert_at_cursor(texto)
            vista.grab_focus()
            notificar(_("Fragmento insertado."))
        DialogoElegirFragmento(vista.get_root(), _poner).present()
        return True
    ctl = Gtk.ShortcutController()
    ctl.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("<Ctrl><Shift>j"), Gtk.CallbackAction.new(_insertar)))
    vista.add_controller(ctl)
