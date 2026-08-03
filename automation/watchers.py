from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemMovedEvent
from typing import Callable, Dict, Any, Optional, List
from pathlib import Path
import fnmatch
import logging
import threading
import time


logger = logging.getLogger(__name__)


class YunaFileHandler(FileSystemEventHandler):
    """
    Handler de eventos del sistema de archivos para Yuna.

    Detecta:
    - archivos creados
    - archivos modificados
    - archivos movidos/renombrados

    El handler solamente detecta eventos.
    La lógica de negocio pertenece al callback de Yuna.
    """

    DEFAULT_PATTERNS = [
        "*"
    ]

    IGNORED_NAMES = {
        ".DS_Store",
    }

    IGNORED_PREFIXES = (
        "~$",
        ".~lock.",
    )

    def __init__(
        self,
        callback: Callable[[str, str], None],
        patterns: Optional[List[str]] = None,
        debounce_seconds: float = 0.5,
    ):
        super().__init__()

        self.callback = callback
        self.patterns = patterns or self.DEFAULT_PATTERNS
        self.debounce_seconds = debounce_seconds

        self._last_events: Dict[str, float] = {}
        self._lock = threading.Lock()

    def on_created(self, event):
        if not event.is_directory:
            self._process_event("created", event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._process_event("modified", event.src_path)

    def on_moved(self, event: FileSystemMovedEvent):
        if event.is_directory:
            return

        # Para Yuna, un movimiento representa un nuevo archivo
        # disponible en la ubicación destino.
        self._process_event("moved", event.dest_path)

    def _process_event(self, event_type: str, path: str):
        path_obj = Path(path)

        if self._should_ignore(path_obj):
            return

        if not self._matches(path_obj):
            return

        if self._is_duplicate_event(event_type, path):
            return

        try:
            self.callback(event_type, str(path_obj))
        except Exception:
            logger.exception(
                "Error ejecutando callback del watcher: %s %s",
                event_type,
                path,
            )

    def _matches(self, path: Path) -> bool:
        """
        Comprueba el nombre del archivo, no la ruta completa.
        """
        name = path.name

        return any(
            fnmatch.fnmatch(name, pattern)
            for pattern in self.patterns
        )

    def _should_ignore(self, path: Path) -> bool:
        name = path.name

        if name in self.IGNORED_NAMES:
            return True

        if any(name.startswith(prefix) for prefix in self.IGNORED_PREFIXES):
            return True

        return False

    def _is_duplicate_event(self, event_type: str, path: str) -> bool:
        """
        Evita que múltiples eventos prácticamente simultáneos
        generados por macOS/Office disparen repetidamente el callback.
        """
        now = time.monotonic()
        key = f"{event_type}:{path}"

        with self._lock:
            previous = self._last_events.get(key)

            if previous is not None:
                if now - previous < self.debounce_seconds:
                    return True

            self._last_events[key] = now

            # Limpieza sencilla del cache
            if len(self._last_events) > 1000:
                cutoff = now - max(self.debounce_seconds * 10, 10)

                self._last_events = {
                    k: v
                    for k, v in self._last_events.items()
                    if v >= cutoff
                }

        return False


class FileWatcher:
    """
    Administrador del sistema de vigilancia de archivos de Yuna.
    """

    def __init__(self):
        self.observer = Observer()
        self.watches: Dict[str, Any] = {}
        self._started = False
        self._lock = threading.Lock()

    def watch(
        self,
        path: str,
        callback: Callable[[str, str], None],
        patterns: Optional[List[str]] = None,
        recursive: bool = True,
        debounce_seconds: float = 0.5,
    ):
        """
        Registra una carpeta para vigilancia.
        """

        path_obj = Path(path).expanduser().resolve()

        if not path_obj.exists():
            raise FileNotFoundError(
                f"La carpeta a vigilar no existe: {path_obj}"
            )

        if not path_obj.is_dir():
            raise NotADirectoryError(
                f"La ruta no es una carpeta: {path_obj}"
            )

        handler = YunaFileHandler(
            callback=callback,
            patterns=patterns,
            debounce_seconds=debounce_seconds,
        )

        watch = self.observer.schedule(
            handler,
            str(path_obj),
            recursive=recursive,
        )

        with self._lock:
            self.watches[str(path_obj)] = watch

        logger.info(
            "Vigilando: %s | patrones=%s | recursive=%s",
            path_obj,
            patterns or ["*"],
            recursive,
        )

        return str(path_obj)

    def unwatch(self, path: str):
        """
        Deja de vigilar una carpeta concreta.
        """

        path_obj = str(Path(path).expanduser().resolve())

        with self._lock:
            watch = self.watches.pop(path_obj, None)

        if watch is not None:
            self.observer.unschedule(watch)
            logger.info("Vigilancia detenida: %s", path_obj)

    def start(self):
        """
        Inicia el observer.
        """
        with self._lock:
            if self._started:
                logger.warning("File watcher ya estaba iniciado")
                return

            self.observer.start()
            self._started = True

        logger.info("File watcher iniciado")

    def stop(self):
        """
        Detiene el observer de forma segura.
        """
        with self._lock:
            if not self._started:
                return

            self.observer.stop()
            self._started = False

        self.observer.join()
        logger.info("File watcher detenido")

    def is_running(self) -> bool:
        return self._started and self.observer.is_alive()

    def list_watches(self) -> List[str]:
        with self._lock:
            return list(self.watches.keys())
