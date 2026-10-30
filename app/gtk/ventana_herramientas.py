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
        accion("herr-cola", self.herr_cola)
        accion("herr-estadisticas", self.herr_estadisticas)
        accion("herr-ponte-al-dia", self.herr_ponte_al_dia, ["<Ctrl><Shift>y"])
        accion("herr-buscar-global", self.herr_buscar_global, ["<Ctrl><Shift>s"])
        accion("herr-publicacion-cruzada", self.herr_publicacion_cruzada, ["<Ctrl><Shift>x"])
        accion("herr-centro-notificaciones", self.herr_centro_notificaciones, ["<Ctrl><Shift>a"])

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

    def herr_publicacion_cruzada(self, texto: str = ""):
        from .dialogos_herramientas import DialogoPublicacionCruzada
        DialogoPublicacionCruzada(self, texto).present()

    def herr_cola(self):
        from .dialogos_herramientas import DialogoColaUnificada
        DialogoColaUnificada(self).present()

    def herr_registro(self):
        from .dialogos_herramientas import DialogoRegistro
        DialogoRegistro(self).present()

    # ------------------------------------------------------------------ centro de notificaciones
    def herr_centro_notificaciones(self):
        from .dialogos_herramientas import DialogoCentroNotificaciones
        DialogoCentroNotificaciones(self, self._abrir_notificacion).present()

    def _ir_a_buffer(self, servicio: str, account_id: int, timeline: str) -> bool:
        """Selecciona en el árbol el buffer fijo de una cuenta."""
        for i in range(self.modelo_arbol.get_n_items()):
            n = self.modelo_arbol.get_row(i).get_item().nodo
            if n.servicio == servicio and n.account_id == account_id and n.timeline == timeline:
                self.seleccion_arbol.set_selected(i)
                self.enfocar_panel(self.vista_lista)
                return True
        return False

    def _abrir_notificacion(self, destino):
        """Lleva a lo que señala una notificación del centro: el hilo, el chat o el buffer de su red."""
        red = destino[0]
        try:
            if red == "mastodon" and destino[2]:
                self._abrir_buffer(destino[1], f"thread:{destino[2]}", _("Conversación"), servicio="mastodon")
            elif red == "bluesky" and destino[2]:
                self._abrir_buffer(destino[1], f"thread:{destino[2]}", _("Conversación"), servicio="bluesky")
            elif red == "x" and destino[2]:
                self._abrir_buffer(destino[1], f"thread:{destino[2]}", _("Conversación"), servicio="x")
            elif red == "telegram":
                self._tg_abrir_por_id(destino[1], destino[2], destino[3] or "")
            elif red == "matrix":
                self.mx_abrir_sala(destino[1], destino[2], destino[3] or "")
            elif red == "wsocial_convo":
                self._abrir_buffer(destino[1], f"dm:{destino[2]}", destino[3] or _("Mensajes directos"), servicio="wsocial")
            elif red == "wsocial":
                if not self._ir_a_buffer("wsocial", destino[1], "notifications"):
                    self.avisar(_("No se encontró el buffer de notificaciones de W Social"))
            elif red == "irc":
                self._irc_abrir_por_nombre(destino[1], destino[2])
            elif red == "xmpp":
                self._x_abrir_por_jid(destino[1], destino[2], destino[3])
            else:
                self.avisar(_("Ve al buffer de {0} para ver el detalle.").format(red))
        except Exception as e:
            log.warning("No se pudo abrir la notificación %s: %s", destino, e)
            self.avisar(_("No se pudo abrir: {0}").format(e))

    # ------------------------------------------------------------------ búsqueda global
    def herr_buscar_global(self, consulta: str = "", solo_rss: bool = False):
        from .dialogos_herramientas import DialogoBusquedaGlobal
        DialogoBusquedaGlobal(self, self._abrir_resultado_busqueda, consulta, solo_rss).present()

    def _abrir_resultado_busqueda(self, r: dict):
        """Abre un resultado de la búsqueda global: el hilo de la publicación, el chat o el artículo."""
        from app.core.database import db
        srv, acc = r["service"], r.get("account_id")
        try:
            if srv == "mastodon" and r.get("status_id"):
                self._abrir_buffer(acc, f"thread:{r['status_id']}", _("Conversación"), servicio="mastodon")
            elif srv in ("bluesky", "wsocial") and r.get("uri"):
                self._abrir_buffer(acc, f"thread:{r['uri']}", _("Conversación"), servicio=srv)
            elif srv == "wsocial":
                fila = db.query_one("SELECT uri FROM wsocial_posts WHERE id = ?", (r["db_id"],))
                if fila:
                    self._abrir_buffer(acc, f"thread:{fila[0]}", _("Conversación"), servicio="wsocial")
            elif srv == "x" and r.get("tweet_id"):
                self._abrir_buffer(acc, f"thread:{r['tweet_id']}", _("Conversación"), servicio="x")
            elif srv == "telegram" and r.get("chat_id") is not None:
                self._tg_abrir_por_id(acc, r["chat_id"])
            elif srv == "matrix":
                self.mx_abrir_sala(acc, r["room_id"])
            elif srv == "xmpp":
                self._x_abrir_por_jid(acc, r["chat_jid"])
            elif srv == "irc":
                self._irc_abrir_por_nombre(acc, r["channel"])
            elif srv == "rss":
                from app.services.rss.rss_service import rss_service
                from app.core.html_utils import html_a_texto
                from .dialogos_mastodon_extra import DialogoTextoLargo
                art = rss_service.obtener_articulo(r["db_id"])
                if art is None:
                    self.avisar(_("No se encontró el artículo"))
                    return
                DialogoTextoLargo(self, art.title, f"{art.title}\n\n{html_a_texto(art.content or '')}\n\n{art.link or ''}").present()
        except Exception as e:
            log.warning("No se pudo abrir el resultado %s: %s", r, e)
            self.avisar(_("No se pudo abrir: {0}").format(e))

    # ------------------------------------------------------------------ estadísticas y «ponte al día»
    def herr_estadisticas(self):
        from app.core.herramientas_extra import calcular_estadisticas, texto_estadisticas
        from app.core.task_manager import task_manager
        from .dialogos_mastodon_extra import DialogoTextoLargo
        self.avisar(_("Calculando estadísticas…"))

        def _fin(d, err):
            if err or not d:
                self.avisar(_("No se pudieron calcular las estadísticas: {0}").format(err or ""))
                return
            DialogoTextoLargo(self, _("Estadísticas de mis redes"), texto_estadisticas(d)).present()
        task_manager.start_task(lambda ctx: calcular_estadisticas(), callback=_fin, pass_context=True)

    def herr_ponte_al_dia(self):
        """Resume con la IA lo que no has leído (RSS sin leer y menciones recientes). Solo la llamada a la IA usa la red."""
        from app.core.event_bus import event_bus
        from app.core.herramientas_extra import texto_pendiente
        from app.core.task_manager import task_manager
        from .acciones_ia import ia_activa
        from .dialogos_herramientas import markdown_a_texto
        from .dialogos_mastodon_extra import DialogoTextoLargo
        if not ia_activa():
            return
        self.avisar(_("Reuniendo lo que no has leído…"))

        def _bg(ctx):
            from app.services.ai.ai_service import ai_service
            peticion = texto_pendiente()
            return ai_service.resumir_texto(peticion) if peticion else None

        def _fin(res, err):
            if err:
                event_bus.emit("sound_trigger", "ai_error")
                self.avisar(_("No se pudo generar el resumen: {0}").format(err))
                return
            if not res:
                self.avisar(_("No tienes nada pendiente de leer ahora mismo."))
                return
            event_bus.emit("sound_trigger", "ai_done")
            self.avisar(_("Resumen listo"))
            DialogoTextoLargo(self, _("Ponte al día"), markdown_a_texto(res)).present()
        task_manager.start_task(_bg, callback=_fin, pass_context=True)
