# -*- coding: utf-8 -*-
"""Bluesky en la ventana principal (mixin de VentanaPrincipal).

Las acciones comparten teclas con Mastodon (Ctrl+B me gusta, Ctrl+R responder...): los manejadores de
ventana.py llaman aquí cuando el elemento enfocado es de Bluesky."""

import logging

from app.core.event_bus import event_bus
from app.core.speech import speak
from app.services.bluesky.bluesky_service import bluesky_service

from . import datos_bluesky

log = logging.getLogger(__name__)


class _BlueskyMixin:
    # ------------------------------------------------------------------ contexto
    def _bsky_ctx(self) -> bool:
        """True si lo que está enfocado (fila o, si no hay, nodo del árbol) es de Bluesky."""
        obj = self._fila_actual()
        if obj is not None:
            return obj.fila.servicio == "bluesky"
        n = self.nodo_actual
        return n is not None and n.servicio == "bluesky"

    def _bsky_obj(self):
        obj = self._fila_actual()
        if obj is None or obj.fila.servicio != "bluesky":
            self.avisar(_("Selecciona una publicación de Bluesky"))
            return None
        return obj

    def _bsky_cuenta(self):
        n = self.nodo_actual
        if n is not None and n.servicio == "bluesky" and n.account_id:
            return n.account_id
        cuentas = datos_bluesky.cuentas()
        if len(cuentas) == 1:
            return cuentas[0][0]
        self.avisar(_("Selecciona una cuenta de Bluesky"))
        return None

    def _bsky_post_db_id(self, obj):
        """Id local de la publicación de la fila (en una notificación, la publicación a la que se refiere)."""
        x = obj.fila.extra
        if x.get("tipo") == "notificacion":
            return f"{x['account_id']}:{x['uri']}" if x.get("uri") else None
        return obj.fila.id

    def _bsky_nodos_cuenta(self, account_id):
        for raiz in getattr(self, "arbol", []):
            if raiz.servicio == "bluesky":
                return [h for c in raiz.hijos if c.account_id == account_id for h in c.hijos]
        return []

    # ------------------------------------------------------------------ actualizar y cargar más
    def bsky_actualizar_nodo(self, nodo, silencioso: bool = False):
        clave = (nodo.account_id, nodo.timeline)
        primera = clave not in self._cargados

        def _fin(res, err):
            if err:
                if not silencioso:
                    self.avisar(_("Error al actualizar: {e}").format(e=err))
                return
            self._cargados.add(clave)
            nuevos = len(res or [])
            if nodo is self.nodo_actual and not self.busqueda:
                obj = self._fila_actual()
                self.cargar_lista(conservar_id=obj.fila.id if obj else None, incremental=True)
            if nodo.timeline == "notifications":
                bluesky_service.marcar_notificaciones_vistas_async(nodo.account_id, callback=lambda r, e: None)
            if primera or not nuevos:
                if not silencioso and nodo is self.nodo_actual:
                    self.estado.set_text(_("{t}: actualizado").format(t=nodo.titulo))
                return
            if nodo.timeline == "notifications":
                speak(_("{n} notificaciones nuevas").format(n=nuevos), interrupt=False)
                event_bus.emit("sound_trigger", "bluesky_new_notification")
            elif nodo is self.nodo_actual:
                self.avisar(_("{n} nuevas").format(n=nuevos), interrumpir=False)
        if nodo.timeline == "bookmarks":
            bluesky_service.cargar_bookmarks_async(nodo.account_id, callback=_fin)
        else:
            bluesky_service.cargar_timeline_async(nodo.account_id, nodo.timeline, callback=_fin)

    def bsky_cargar_mas(self):
        n = self.nodo_actual
        if n is None or not n.listable:
            return
        self.avisar(_("Cargando publicaciones anteriores…"))
        actual = self._fila_actual()

        def _fin(res, err):
            if err:
                self.avisar(_("Error al cargar: {e}").format(e=err))
                return
            self.cargar_lista(conservar_id=actual.fila.id if actual else None, incremental=True)
            if not (res or []):
                self.avisar(_("No hay más publicaciones"))
            else:
                self.avisar(_("{n} cargadas").format(n=len(res)))
        if n.timeline == "bookmarks":
            bluesky_service.cargar_bookmarks_async(n.account_id, cargar_mas=True, callback=_fin)
        else:
            bluesky_service.cargar_timeline_async(n.account_id, n.timeline, cargar_mas=True, callback=_fin)

    def _sondeo_bluesky(self):
        for acc_id, _n in datos_bluesky.cuentas():
            for nodo in self._bsky_nodos_cuenta(acc_id):
                if nodo.timeline in ("home", "notifications") and (acc_id, nodo.timeline) in self._cargados:
                    self.bsky_actualizar_nodo(nodo, silencioso=True)

    # ------------------------------------------------------------------ acciones sobre una publicación
    def _bsky_accion_estado(self, obj, on: str, off: str, propiedad: str, texto_on: str, texto_off: str):
        db_id = self._bsky_post_db_id(obj)
        if not db_id:
            self.avisar(_("Esta notificación no tiene publicación"))
            return
        activo = obj.get_property(propiedad)

        def _fin(res, err):
            if err:
                self.avisar(_("No se pudo: {e}").format(e=err))
                return
            obj.set_property(propiedad, not activo)
            self.avisar(texto_off if activo else texto_on)
        bluesky_service.ejecutar_accion_post_async(obj.fila.extra["account_id"], db_id, off if activo else on, callback=_fin)

    def bsky_me_gusta(self):
        obj = self._bsky_obj()
        if obj:
            self._bsky_accion_estado(obj, "like", "unlike", "favorito", _("Me gusta"), _("Me gusta quitado"))

    def bsky_republicar(self):
        obj = self._bsky_obj()
        if obj:
            self._bsky_accion_estado(obj, "repost", "unrepost", "impulsado", _("Republicado"), _("Republicación quitada"))

    def bsky_marcador(self):
        obj = self._bsky_obj()
        if not obj:
            return
        db_id = self._bsky_post_db_id(obj)
        if not db_id:
            return
        activo = obj.marcador

        def _fin(res, err):
            if err:
                self.avisar(_("No se pudo: {e}").format(e=err))
                return
            obj.marcador = not activo
            self.avisar(_("Marcador quitado") if activo else _("Añadido a marcadores"))
        (bluesky_service.borrar_bookmark_async if activo else bluesky_service.crear_bookmark_async)(
            obj.fila.extra["account_id"], db_id, callback=_fin)

    def bsky_nuevo(self):
        acc = self._bsky_cuenta()
        if acc is not None:
            from .dialogos_bluesky import DialogoPublicarBsky
            DialogoPublicarBsky(self, acc).present()

    def bsky_responder(self):
        obj = self._bsky_obj()
        x = obj.fila.extra if obj else {}
        if not obj or not x.get("uri"):
            return
        from .dialogos_bluesky import DialogoPublicarBsky
        DialogoPublicarBsky(self, x["account_id"], responde_a=x["uri"]).present()

    def bsky_citar(self):
        obj = self._bsky_obj()
        x = obj.fila.extra if obj else {}
        if not obj or not x.get("uri"):
            return
        from .dialogos_bluesky import DialogoPublicarBsky
        DialogoPublicarBsky(self, x["account_id"], cita_uri=x["uri"]).present()

    def bsky_borrar(self):
        obj = self._bsky_obj()
        if not obj:
            return
        x = obj.fila.extra
        if not x.get("propio") or x.get("tipo") == "notificacion":
            self.avisar(_("Solo puedes borrar tus propias publicaciones"))
            return
        from .dialogos import confirmar_async

        def _hacer():
            def _fin(res, err):
                if err:
                    self.avisar(_("No se pudo borrar: {e}").format(e=err))
                    return
                for i in range(self.almacen_lista.get_n_items()):
                    if self.almacen_lista.get_item(i) is obj:
                        self.almacen_lista.remove(i)
                        n = self.almacen_lista.get_n_items()
                        if n:
                            self.seleccion_lista.set_selected(min(i, n - 1))
                        break
                self.avisar(_("Publicación borrada"))
            bluesky_service.borrar_post_async(x["account_id"], x["uri"], callback=_fin)
        confirmar_async(self, _("¿Borrar esta publicación? No se puede deshacer."), _hacer, etiqueta_si=_("Borrar"))

    # ------------------------------------------------------------------ hilos, cuentas y búsquedas
    def bsky_conversacion(self):
        obj = self._bsky_obj()
        x = obj.fila.extra if obj else {}
        if not obj or not x.get("uri"):
            return
        self._abrir_buffer(x["account_id"], f"thread:{x['uri']}", _("Conversación de {n}").format(n=obj.fila.autor),
                           servicio="bluesky")

    def bsky_abrir_cronologia(self, account_id: int, did: str, handle: str):
        self._abrir_buffer(account_id, f"author:{did}", _("Publicaciones de @{u}").format(u=handle), servicio="bluesky")

    def bsky_cronologia_usuario(self):
        obj = self._bsky_obj()
        x = obj.fila.extra if obj else {}
        if not obj or not x.get("usuario"):
            return
        did = x.get("did") or x["usuario"]
        self.bsky_abrir_cronologia(x["account_id"], did, x["usuario"])

    def bsky_perfil(self):
        obj = self._bsky_obj()
        x = obj.fila.extra if obj else {}
        if not obj or not x.get("usuario"):
            return
        from .dialogos_bluesky import DialogoPerfilBsky
        DialogoPerfilBsky(self, x["account_id"], x.get("did") or x["usuario"]).present()

    def bsky_buscar(self):
        acc = self._bsky_cuenta()
        if acc is None:
            return
        from .dialogos import DialogoTexto

        def _buscar(texto):
            self._abrir_buffer(acc, f"search:{texto}", _("Búsqueda: {t}").format(t=texto), servicio="bluesky")
        DialogoTexto(self, _("Buscar en Bluesky"), _("_Buscar:"), _buscar,
                     _("Busca publicaciones. Puedes usar #hashtags y from:usuario."), _("_Buscar")).present()

    def bsky_abrir_feed(self):
        self._bsky_elegir("feed")

    def bsky_abrir_lista(self):
        self._bsky_elegir("list")

    def _bsky_elegir(self, tipo: str):
        acc = self._bsky_cuenta()
        if acc is None:
            return
        self.avisar(_("Leyendo tus feeds…") if tipo == "feed" else _("Leyendo tus listas…"))

        def _fin(items, err):
            if err:
                self.avisar(_("No se pudo leer: {e}").format(e=err))
                return
            if not items:
                self.avisar(_("No tienes feeds guardados") if tipo == "feed" else _("No tienes listas"))
                return
            from .dialogos import DialogoElegir

            def _elegido(i):
                it = items[i]
                self._abrir_buffer(acc, f"{tipo}:{it['uri']}", (_("Feed {t}") if tipo == "feed" else _("Lista {t}")).format(t=it["name"]),
                                   servicio="bluesky")
            DialogoElegir(self, _("Abrir un feed") if tipo == "feed" else _("Abrir una lista"),
                          _("_Feed:") if tipo == "feed" else _("_Lista:"), [it["name"] for it in items], _elegido,
                          _("_Abrir")).present()
        (bluesky_service.obtener_feeds_guardados_async if tipo == "feed" else bluesky_service.obtener_listas_async)(
            acc, callback=_fin)

    def bsky_eliminar_cuenta(self):
        n = self.nodo_actual
        if n is None or n.servicio != "bluesky" or not n.account_id:
            self.avisar(_("Selecciona una cuenta de Bluesky"))
            return
        from .dialogos import confirmar_async
        acc = n.account_id
        nombre = next((nm for i, nm in datos_bluesky.cuentas() if i == acc), "")

        def _hacer():
            bluesky_service.eliminar_cuenta(acc)
            datos_bluesky.EXTRA.pop(acc, None)
            self.cargar_arbol(conservar=False)
            self.avisar(_("Cuenta eliminada"))
        confirmar_async(self, _("¿Eliminar la cuenta {n} y sus datos de este equipo?").format(n=nombre), _hacer,
                        etiqueta_si=_("Eliminar"))
