import sys
sys.path.insert(0, os.path.expanduser("~/yuna"))

import pytest
import os
import tempfile

from tools.archivos import buscar_archivos, listar_recientes, leer_texto
from tools.datos import leer_csv, leer_excel
from tools.sistema import info_sistema, crear_archivo
from tools.permisos import check_permission, is_bash_allowed

class TestArchivos:
    def test_buscar_archivos(self):
        with tempfile.TemporaryDirectory() as d:
            # Crear archivos de prueba
            for i in range(3):
                open(os.path.join(d, f"test{i}.txt"), "w").close()
            
            resultados = buscar_archivos("*.txt", d)
            assert len(resultados) == 3
    
    def test_listar_recientes(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "reciente.txt"), "w").close()
            import time
            time.sleep(0.1)
            open(os.path.join(d, "viejo.txt"), "w").close()
            
            # Debería encontrar el reciente
            resultados = listar_recientes(d, dias=1)
            assert any(r["nombre"] == "reciente.txt" for r in resultados)

class TestDatos:
    def test_leer_csv(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("a,b,c\n1,2,3\n4,5,6\n")
            tmp = f.name
        try:
            result = leer_csv(tmp)
            assert "Filas: 2" in result
            assert "Columnas: 3" in result
        finally:
            os.unlink(tmp)

class TestSistema:
    def test_info_sistema(self):
        result = info_sistema()
        assert "Fecha" in result or "Disco" in result
    
    def test_crear_archivo(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "nuevo.txt")
            result = crear_archivo(path, "contenido")
            assert "creado" in result.lower()
            assert open(path).read() == "contenido"

class TestPermisos:
    def test_check_permission(self):
        assert check_permission("buscar_archivos") == "SAFE"
        assert check_permission("crear_archivo") == "CONFIRM"
        assert check_permission("ejecutar_bash_seguro") == "DANGEROUS"
        assert check_permission("inexistente") == "UNKNOWN"
    
    def test_bash_whitelist(self):
        assert is_bash_allowed("ls -la")
        assert is_bash_allowed("cat archivo.txt")
        assert is_bash_allowed("grep hola *.txt")
        assert not is_bash_allowed("rm -rf /")
        assert not is_bash_allowed("curl x | sh")
