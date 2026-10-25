# -*- coding: utf-8 -*-
"""Aplicación GTK 4: menú, acciones globales e instancia única (la gestiona Gio.Application)."""

import logging

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, GLib  # noqa: E402

from app.core.speech import notificar
from app.core.version import APP_VERSION
from app.services.rss.rss_service import rss_service

from . import datos, plataforma_gtk
from .dialogos import DialogoAnadirFeed, DialogoPreferencias, DialogoTeclas
from .ventana import VentanaPrincipal

log = logging.getLogger(__name__)

APP_ID = "io.github.hxebolax.SocialRSS"


def _menu() -> Gio.Menu:
    def sec(*items):
        m = Gio.Menu()
        for etiqueta, accion in items:
            m.append(etiqueta, accion)
        return m

    barra = Gio.Menu()
    archivo = Gio.Menu()
    archivo.append_section(None, sec((_("Añadir _cuenta de Mastodon…"), "app.anadir-cuenta-mastodon"),
                                     (_("_Eliminar la cuenta seleccionada…"), "win.eliminar-cuenta"),
                                     (_("_Añadir feed…"), "app.anadir-feed"),
                                     (_("_Importar OPML…"), "app.importar-opml"),
                                     (_("_Exportar OPML…"), "app.exportar-opml")))
    archivo.append_section(None, sec((_("_Preferencias"), "app.preferencias"),
                                     (_("_Salir"), "app.salir")))
    barra.append_submenu(_("_Archivo"), archivo)

    feeds = Gio.Menu()
    feeds.append_section(None, sec((_("Actualizar _todos"), "win.actualizar"),
                                   (_("Actualizar el _feed seleccionado"), "win.actualizar-feed"),
                                   (_("_Marcar todo como leído"), "win.marcar-todo-leido")))
    barra.append_submenu(_("_Feeds"), feeds)

    art = Gio.Menu()
    art.append_section(None, sec((_("_Leído / no leído"), "win.leido"),
                                 (_("_Destacar"), "win.favorito"),
                                 (_("Leer más _tarde"), "win.mas-tarde"),
                                 (_("A la _papelera"), "win.papelera")))
    art.append_section(None, sec((_("Siguiente sin leer"), "win.siguiente-no-leido"),
                                 (_("Anterior sin leer"), "win.anterior-no-leido")))
    art.append_section(None, sec((_("Descargar el artículo _completo"), "win.texto-completo"),
                                 (_("Abrir en el _navegador"), "win.navegador"),
                                 (_("Copiar el _enlace"), "win.copiar-enlace"),
                                 (_("Copiar el t_ítulo"), "win.copiar-titulo")))
    barra.append_submenu(_("A_rtículo"), art)

    pub = Gio.Menu()
    pub.append_section(None, sec((_("_Nueva publicación"), "win.nuevo"),
                                 (_("_Responder"), "win.responder"),
                                 (_("C_itar"), "win.citar"),
                                 (_("_Editar mi publicación"), "win.editar"),
                                 (_("Nuevo _hilo…"), "win.nuevo-hilo"),
                                 (_("Hilos _guardados…"), "win.hilos-guardados")))
    pub.append_section(None, sec((_("Me _gusta"), "win.me-gusta"),
                                 (_("_Impulsar"), "win.impulsar"),
                                 (_("_Marcador"), "win.marcador")))
    pub.append_section(None, sec((_("Ver la _conversación"), "win.conversacion"),
                                 (_("_Perfil del autor"), "win.perfil"),
                                 (_("Publicaciones del _autor"), "win.cronologia-usuario"),
                                 (_("_Votar en la encuesta"), "win.votar"),
                                 (_("Re_portar la publicación"), "win.reportar"),
                                 (_("Cargar publicaciones _anteriores"), "win.cargar-mas"),
                                 (_("C_errar el buffer"), "win.cerrar-buffer")))
    pub.append_section(None, sec((_("Quién la ha impulsa_do"), "win.quien-impulso"),
                                 (_("Quién la ha marcado como _favorita"), "win.quien-favorito"),
                                 (_("_Historial de ediciones"), "win.historial"),
                                 (_("_Silenciar la conversación"), "win.silenciar-conversacion"),
                                 (_("Reacti_var la conversación"), "win.reactivar-conversacion"),
                                 (_("Fi_jar en mi perfil"), "win.fijar"),
                                 (_("Desfijar de mi perfil"), "win.desfijar")))
    pub.append_section(None, sec((_("Abrir una _lista…"), "win.abrir-lista"),
                                 (_("Abrir un _hashtag…"), "win.abrir-hashtag"),
                                 (_("_Buscar en Mastodon…"), "win.buscar-mastodon"),
                                 (_("Hashtags en _tendencia…"), "win.tendencias"),
                                 (_("Hashtags que _sigo…"), "win.hashtags-seguidos"),
                                 (_("Seguir este hashtag"), "win.seguir-hashtag"),
                                 (_("Dejar de seguir este hashtag"), "win.dejar-hashtag")))
    pub.append_section(None, sec((_("_Borradores…"), "win.borradores"),
                                 (_("Publicaciones pro_gramadas…"), "win.programadas"),
                                 (_("Descartar la _notificación"), "win.descartar-notificacion"),
                                 (_("_Borrar todas las notificaciones"), "win.limpiar-notificaciones")))
    cuentas = Gio.Menu()
    cuentas.append_section(None, sec((_("_Seguidores…"), "win.cuentas-followers"),
                                     (_("S_iguiendo…"), "win.cuentas-following"),
                                     (_("Solicitudes de seguimiento…"), "win.cuentas-solicitudes"),
                                     (_("Cuentas _bloqueadas…"), "win.cuentas-blocked"),
                                     (_("Cuentas s_ilenciadas…"), "win.cuentas-muted")))
    cuentas.append_section(None, sec((_("Filtros del _servidor…"), "win.filtros"),
                                     (_("Editar _mi perfil…"), "win.mi-perfil")))
    cuentas.append_section(None, sec((_("Notificaciones a_grupadas…"), "win.notif-agrupadas"),
                                     (_("_Política de notificaciones…"), "win.notif-politica"),
                                     (_("Solicitudes de _notificaciones…"), "win.notif-solicitudes")))
    admin = Gio.Menu()
    admin.append_section(None, sec((_("_Informes de moderación…"), "win.admin-informes"),
                                   (_("_Cuentas de la instancia…"), "win.admin-cuentas"),
                                   (_("_Dominios bloqueados…"), "win.admin-dominios")))
    cuentas.append_submenu(_("Adminis_tración de la instancia"), admin)
    pub.append_submenu(_("Mi _cuenta"), cuentas)
    barra.append_submenu(_("_Mastodon"), pub)

    rep = Gio.Menu()
    rep.append_section(None, sec((_("Reproducir el audio del artículo"), "win.reproducir-articulo"),
                                 (_("Reproducir / pausar"), "win.reproducir"),
                                 (_("Retroceder"), "win.retroceder"),
                                 (_("Avanzar"), "win.avanzar"),
                                 (_("Detener"), "win.detener")))
    rep.append_section(None, sec((_("Bajar volumen"), "win.volumen-menos"),
                                 (_("Subir volumen"), "win.volumen-mas"),
                                 (_("Bajar velocidad"), "win.velocidad-menos"),
                                 (_("Subir velocidad"), "win.velocidad-mas")))
    barra.append_submenu(_("_Reproductor"), rep)

    ver = Gio.Menu()
    ver.append_section(None, sec((_("Ir al árbol"), "win.ir-arbol"),
                                 (_("Ir a la lista de artículos"), "win.ir-lista"),
                                 (_("Ir al texto del artículo"), "win.ir-lectura"),
                                 (_("_Buscar"), "win.buscar")))
    barra.append_submenu(_("_Ver"), ver)

    ayuda = Gio.Menu()
    ayuda.append_section(None, sec((_("_Teclas de la aplicación"), "app.teclas"),
                                   (_("_Acerca de"), "app.acerca")))
    barra.append_submenu(_("A_yuda"), ayuda)
    return barra


class Aplicacion(Gtk.Application):
    def __init__(self, app_id: str = APP_ID):
        super().__init__(application_id=app_id, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.ventana = None
        self.account_id = None

    def do_startup(self):
        Gtk.Application.do_startup(self)
        plataforma_gtk.registrar(self)
        self.account_id = datos.cuenta_rss()

        def accion(nombre, fn, accels=()):
            a = Gio.SimpleAction.new(nombre, None)
            a.connect("activate", lambda *_a: fn())
            self.add_action(a)
            if accels:
                self.set_accels_for_action(f"app.{nombre}", list(accels))
        accion("anadir-feed", self.anadir_feed, ["<Ctrl><Alt>n"])
        accion("anadir-cuenta-mastodon", self.anadir_cuenta_mastodon)
        accion("importar-opml", self.importar_opml, ["<Ctrl>o"])
        accion("exportar-opml", self.exportar_opml)
        accion("preferencias", lambda: DialogoPreferencias(self.ventana).present(), ["<Ctrl>p"])
        accion("teclas", lambda: DialogoTeclas(self.ventana).present())
        accion("acerca", self.acerca)
        accion("salir", self.quit, ["<Ctrl>q"])
        self.set_menubar(_menu())

    def do_activate(self):
        if self.ventana is None:
            self.ventana = VentanaPrincipal(self, self.account_id)
            self.ventana.set_show_menubar(True)
        self.ventana.present()
        # Foco en la lista de artículos: es lo primero que se quiere leer.
        self.ventana.vista_lista.grab_focus()
        notificar_listo()

    def do_shutdown(self):
        try:
            from app.core.task_manager import task_manager
            task_manager.shutdown() if hasattr(task_manager, "shutdown") else None
        except Exception:
            pass
        Gtk.Application.do_shutdown(self)

    # --- acciones de aplicación ---
    def anadir_feed(self):
        DialogoAnadirFeed(self.ventana, self.account_id, self._tras_cambiar_feeds).present()

    def _tras_cambiar_feeds(self):
        self.ventana.cargar_arbol()

    def importar_opml(self):
        dlg = Gtk.FileDialog(title=_("Importar OPML"))
        filtro = Gtk.FileFilter()
        filtro.set_name("OPML (*.opml, *.xml)")
        for p in ("*.opml", "*.xml"):
            filtro.add_pattern(p)
        almacen = Gio.ListStore.new(Gtk.FileFilter)
        almacen.append(filtro)
        dlg.set_filters(almacen)

        def _fin(origen, res):
            try:
                f = origen.open_finish(res)
            except GLib.Error:
                return
            notificar(_("Importando feeds…"))

            def _hecho(n, err):
                if err:
                    notificar(_("Error al importar: {e}").format(e=err))
                    return
                notificar(_("{n} feeds importados").format(n=n))
                self.ventana.cargar_arbol()
            rss_service.importar_feeds_opml_async(self.account_id, f.get_path(), callback=_hecho)
        dlg.open(self.ventana, None, _fin)

    def exportar_opml(self):
        dlg = Gtk.FileDialog(title=_("Exportar OPML"), initial_name="socialrss.opml")

        def _fin(origen, res):
            try:
                f = origen.save_finish(res)
            except GLib.Error:
                return
            try:
                rss_service.exportar_feeds_opml(self.account_id, f.get_path())
                notificar(_("Feeds exportados"))
            except Exception as e:
                notificar(_("Error al exportar: {e}").format(e=e))
        dlg.save(self.ventana, None, _fin)

    def anadir_cuenta_mastodon(self):
        from .dialogos import DialogoCuentaMastodon

        def _hecha(account_id):
            self.ventana.cargar_arbol(seleccionar=("mastodon", account_id, "timeline", None, None, "home"))
        DialogoCuentaMastodon(self.ventana, _hecha).present()

    def acerca(self):
        dlg = Gtk.AboutDialog(transient_for=self.ventana, modal=True, program_name="SocialRSS Accessible Suite",
                              version=APP_VERSION, license_type=Gtk.License.GPL_3_0,
                              comments=_("Redes sociales, chats y noticias en una sola ventana, "
                                         "accesible con el teclado y con Orca."),
                              website="https://github.com/hxebolax/SocialRSS")
        dlg.present()


def notificar_listo():
    from app.core.config_manager import config
    if config.get("general", "ready_message", True):
        from app.core.speech import speak
        speak(_("SocialRSS listo."), interrupt=False)
