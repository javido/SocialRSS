# -*- coding: utf-8 -*-
"""Menú Herramientas de la ventana principal (mixin de VentanaPrincipal): herramientas generales que no dependen de
una red concreta."""

import logging

log = logging.getLogger(__name__)


class _HerramientasMixin:
    def _registrar_acciones_herramientas(self, accion):
        accion("herr-filtros", self.herr_filtros)
        accion("herr-fragmentos", self.herr_fragmentos)
        accion("herr-copias", self.herr_copias)
        accion("herr-migrar", self.herr_migrar)
        accion("herr-borrar", self.herr_borrar)
        accion("herr-registro", self.herr_registro)

    def herr_filtros(self):
        from .dialogos_herramientas import DialogoFiltrosContenido
        DialogoFiltrosContenido(self).present()

    def herr_fragmentos(self):
        from .dialogos_herramientas import DialogoFragmentos
        DialogoFragmentos(self).present()

    def herr_copias(self):
        from .dialogos_herramientas import DialogoCopias
        DialogoCopias(self, self.get_application()).present()

    def herr_migrar(self):
        from .dialogos_herramientas import DialogoMigracion
        DialogoMigracion(self, self.get_application()).present()

    def herr_borrar(self):
        from .dialogos_herramientas import DialogoBorrado
        DialogoBorrado(self).present()

    def herr_registro(self):
        from .dialogos_herramientas import DialogoRegistro
        DialogoRegistro(self).present()
