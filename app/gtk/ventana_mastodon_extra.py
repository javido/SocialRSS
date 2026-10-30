# -*- coding: utf-8 -*-
"""Mastodon: colecciones, anuncios, directorio y administración avanzada de la instancia (mixin de VentanaPrincipal).

Las acciones y los métodos llevan el prefijo `ms` (Mastodon), para no chocar con los de Matrix (`mx`)."""

from .dialogos import DialogoTexto


class _MastodonExtraMixin:
    def _ms_cuenta(self):
        return self._cuenta_o_aviso()

    def _ms_dialogo(self, modulo: str, nombre: str, **kw):
        """Abre `nombre` de `app.gtk.<modulo>` con la ventana y la cuenta activa."""
        acc = self._ms_cuenta()
        if acc is None:
            return
        import importlib
        clase = getattr(importlib.import_module(f".{modulo}", __package__), nombre)
        clase(self, acc, **kw).present()

    # ------------------------------------------------------------------ colecciones
    def ms_colecciones(self, modo: str = "mias", acct: str = None):
        self._ms_dialogo("dialogos_mastodon_colecciones", "DialogoColecciones", modo=modo, acct=acct)

    def ms_colecciones_de(self):
        acc = self._ms_cuenta()
        if acc is None:
            return
        obj = self._fila_actual()
        previo = self._usuario_de(obj) if obj is not None and obj.fila.servicio == "mastodon" else ""

        def _con(texto):
            self.ms_colecciones("de", texto.strip().lstrip("@"))
        d = DialogoTexto(self, _("Colecciones de una cuenta"), _("_Cuenta (@usuario o @usuario@servidor):"), _con,
                         aceptar=_("_Ver"))
        d.entrada.set_text(previo)
        d.present()

    def ms_coleccion_anadir_autor(self):
        obj = self._contexto_mastodon()
        usuario = self._usuario_de(obj) if obj else ""
        if not usuario:
            return
        from .dialogos_mastodon_colecciones import anadir_a_mi_coleccion
        anadir_a_mi_coleccion(self, obj.fila.extra["account_id"], usuario.lstrip("@"))

    # ------------------------------------------------------------------ anuncios, directorio e instancia
    def ms_info_instancia(self):
        acc = self._ms_cuenta()
        if acc is not None:
            from .dialogos_mastodon_instancia import info_instancia
            info_instancia(self, acc)

    def ms_cuentas(self, tipo: str):
        acc = self._ms_cuenta()
        if acc is not None:
            from .dialogos_mastodon import DialogoCuentas
            DialogoCuentas(self, acc, tipo).present()

    def _registrar_acciones_mastodon_extra(self, accion):
        accion("ms-anuncios", lambda: self._ms_dialogo("dialogos_mastodon_instancia", "DialogoAnuncios"))
        accion("ms-enlaces-tendencia", lambda: self._ms_dialogo("dialogos_mastodon_instancia", "DialogoEnlacesTendencia"))
        accion("ms-info-instancia", self.ms_info_instancia)
        accion("ms-directorio", lambda: self.ms_cuentas("directorio"))
        accion("ms-sugerencias", lambda: self.ms_cuentas("sugerencias"))
        for nombre, clase in (("ms-admin-ip", "DialogoBloqueosIP"), ("ms-admin-tendencias", "DialogoTendenciasAdmin"),
                              ("ms-admin-estadisticas", "DialogoEstadisticasAdmin")):
            accion(nombre, lambda c=clase: self._ms_dialogo("dialogos_mastodon_admin_extra", c))
        for nombre, recurso in (("ms-admin-permitidos", "domain_allows"), ("ms-admin-correos", "email_domains"),
                                ("ms-admin-canonicos", "canonical_emails")):
            accion(nombre, lambda r=recurso: self._ms_dialogo("dialogos_mastodon_admin_extra", "DialogoRecursosAdmin", recurso=r))
        accion("ms-colecciones-mias", self.ms_colecciones)
        accion("ms-colecciones-donde-estoy", lambda: self.ms_colecciones("donde_estoy"))
        accion("ms-colecciones-de", self.ms_colecciones_de)
        accion("ms-coleccion-anadir-autor", self.ms_coleccion_anadir_autor)
