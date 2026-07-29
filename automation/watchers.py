from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Callable, Dict, Any
import logging
import threading

logger = logging.getLogger(__name__)

class YunaFileHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable[[str, str], None], patterns: list = None):
        self.callback = callback
        self.patterns = patterns or ["*.xlsx", "*.csv", "*.pdf", "*.txt"]
    
    def on_created(self, event):
        if not event.is_directory:
            for pattern in self.patterns:
                if self._match(event.src_path, pattern):
                    self.callback("created", event.src_path)
                    break
    
    def on_modified(self, event):
        if not event.is_directory:
            for pattern in self.patterns:
                if self._match(event.src_path, pattern):
                    self.callback("modified", event.src_path)
                    break
    
    def _match(self, path: str, pattern: str) -> bool:
        import fnmatch
        return fnmatch.fnmatch(path, pattern)

class FileWatcher:
    def __init__(self):
        self.observer = Observer()
        self.watches: Dict[str, Any] = {}
    
    def watch(self, path: str, callback: Callable[[str, str], None], patterns: list = None, recursive: bool = True):
        """Vigila una carpeta y ejecuta callback(event_type, file_path)"""
        path = path.expanduser()
        handler = YunaFileHandler(callback, patterns)
        watch = self.observer.schedule(handler, path, recursive=recursive)
        self.watches[path] = watch
        logger.info(f"Vigilando: {path} (patrones: {patterns})")
    
    def start(self):
        self.observer.start()
        logger.info("File watcher iniciado")
    
    def stop(self):
        self.observer.stop()
        self.observer.join()
        logger.info("File watcher detenido")
