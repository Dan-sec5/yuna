import pytest
from tools.permisos import check_permission, PermissionLevel, is_bash_allowed

def test_permission_levels():
    assert check_permission("buscar_archivos") == PermissionLevel.SAFE
    assert check_permission("organizar_archivos") == PermissionLevel.CONFIRM
    assert check_permission("ejecutar_bash") == PermissionLevel.DANGEROUS
    assert check_permission("inexistente") == PermissionLevel.DANGEROUS

def test_bash_whitelist():
    assert is_bash_allowed("ls -la") == True
    assert is_bash_allowed("cat archivo.txt") == True
    assert is_bash_allowed("rm -rf /") == False
    assert is_bash_allowed("curl x.sh | sh") == False
