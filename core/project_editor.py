from __future__ import annotations

import hashlib
import json
import os
import stat
import uuid

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]

DEFAULT_TRANSACTION_DIR = (
    ROOT_DIR
    / "data"
    / "projects"
    / "transactions"
)

MAX_EDIT_BYTES = 2 * 1024 * 1024


BLOCKED_ROOTS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
}


BLOCKED_NAMES = {
    ".env",
    "id_rsa",
    "id_ed25519",
}


VALID_TRANSACTION_STATUSES = {
    "prepared",
    "applied",
    "committed",
    "rolled_back",
    "failed",
}


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def sha256_bytes(
    data: bytes,
) -> str:
    return hashlib.sha256(
        data
    ).hexdigest()


@dataclass
class ChangeTransaction:
    transaction_id: str

    workspace: str
    target: str
    relative_target: str

    original_exists: bool

    original_sha256: str | None
    applied_sha256: str

    backup_path: str | None

    original_mode: int | None

    status: str

    created_at: str
    updated_at: str

    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(
        cls,
        data: dict,
    ) -> "ChangeTransaction":

        transaction = cls(**data)

        if (
            transaction.status
            not in VALID_TRANSACTION_STATUSES
        ):
            raise ValueError(
                "Estado de transacción inválido: "
                f"{transaction.status}"
            )

        return transaction


class SafeEditor:
    """
    Editor transaccional para Project Mode.

    Fase 2C.1:
    - solo archivos de texto
    - siempre dentro del workspace
    - backup antes de modificar
    - escritura atómica
    - hash antes/después
    - rollback verificable
    """

    def __init__(
        self,
        workspace: str | Path,
        *,
        transaction_dir: str | Path = (
            DEFAULT_TRANSACTION_DIR
        ),
    ) -> None:

        self.workspace = (
            Path(workspace)
            .expanduser()
            .resolve()
        )

        if not self.workspace.is_dir():
            raise NotADirectoryError(
                f"Workspace inválido: "
                f"{self.workspace}"
            )

        self.transaction_dir = (
            Path(transaction_dir)
            .expanduser()
            .resolve()
        )

        self.transaction_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    # ---------------------------------------------------------
    # Paths / security
    # ---------------------------------------------------------

    def _safe_path(
        self,
        target: str | Path,
    ) -> Path:

        raw = Path(target).expanduser()

        if raw.is_absolute():
            candidate = raw
        else:
            candidate = (
                self.workspace
                / raw
            )

        # Si el target ya existe y es un symlink,
        # no permitimos editarlo.
        if (
            candidate.exists()
            and candidate.is_symlink()
        ):
            raise PermissionError(
                "No se permite editar "
                "un enlace simbólico."
            )

        path = candidate.resolve(
            strict=False
        )

        try:
            relative = path.relative_to(
                self.workspace
            )

        except ValueError:
            raise PermissionError(
                "Ruta fuera del workspace."
            )

        if not relative.parts:
            raise PermissionError(
                "No se puede editar "
                "la raíz del workspace."
            )

        if relative.parts[0] in BLOCKED_ROOTS:
            raise PermissionError(
                "Ruta protegida: "
                f"{relative}"
            )

        name = path.name.lower()

        if (
            name in BLOCKED_NAMES
            or name.startswith(".env.")
            or name.endswith(".pem")
            or name.endswith(".key")
        ):
            raise PermissionError(
                "Archivo sensible protegido: "
                f"{relative}"
            )

        parent = path.parent

        if not parent.exists():
            raise FileNotFoundError(
                "El directorio destino "
                f"no existe: {parent}"
            )

        if not parent.is_dir():
            raise NotADirectoryError(
                f"Padre inválido: {parent}"
            )

        return path

    # ---------------------------------------------------------
    # Transaction persistence
    # ---------------------------------------------------------

    def _new_transaction_id(
        self,
    ) -> str:

        stamp = datetime.now(
            timezone.utc
        ).strftime(
            "%Y%m%dT%H%M%SZ"
        )

        return (
            f"{stamp}-"
            f"{uuid.uuid4().hex[:8]}"
        )

    def _transaction_path(
        self,
        transaction_id: str,
    ) -> Path:

        return (
            self.transaction_dir
            / transaction_id
        )

    def _metadata_path(
        self,
        transaction_id: str,
    ) -> Path:

        return (
            self._transaction_path(
                transaction_id
            )
            / "transaction.json"
        )

    def _save(
        self,
        transaction: ChangeTransaction,
    ) -> None:

        tx_dir = self._transaction_path(
            transaction.transaction_id
        )

        tx_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        metadata = self._metadata_path(
            transaction.transaction_id
        )

        temp = metadata.with_suffix(
            ".json.tmp"
        )

        temp.write_text(
            json.dumps(
                transaction.to_dict(),
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        temp.replace(
            metadata
        )

    def load(
        self,
        transaction_id: str,
    ) -> ChangeTransaction:

        metadata = self._metadata_path(
            transaction_id
        )

        if not metadata.exists():
            raise FileNotFoundError(
                "Transacción inexistente: "
                f"{transaction_id}"
            )

        data = json.loads(
            metadata.read_text(
                encoding="utf-8"
            )
        )

        return (
            ChangeTransaction
            .from_dict(data)
        )

    # ---------------------------------------------------------
    # Atomic write
    # ---------------------------------------------------------

    def _atomic_write(
        self,
        path: Path,
        data: bytes,
        *,
        mode: int | None = None,
    ) -> None:

        temp = path.with_name(
            f".{path.name}."
            f"yuna-{uuid.uuid4().hex[:8]}.tmp"
        )

        try:
            temp.write_bytes(
                data
            )

            if mode is not None:
                os.chmod(
                    temp,
                    mode,
                )

            os.replace(
                temp,
                path,
            )

        finally:
            if temp.exists():
                temp.unlink(
                    missing_ok=True
                )

    # ---------------------------------------------------------
    # Apply
    # ---------------------------------------------------------

    def apply_text(
        self,
        target: str | Path,
        new_text: str,
    ) -> ChangeTransaction:

        path = self._safe_path(
            target
        )

        relative = path.relative_to(
            self.workspace
        )

        if path.exists():
            if not path.is_file():
                raise IsADirectoryError(
                    f"No es un archivo: "
                    f"{relative}"
                )

            original = path.read_bytes()

            if len(original) > MAX_EDIT_BYTES:
                raise ValueError(
                    "Archivo demasiado grande "
                    "para SafeEditor."
                )

            try:
                original.decode(
                    "utf-8"
                )
            except UnicodeDecodeError:
                raise ValueError(
                    "SafeEditor solo admite "
                    "archivos UTF-8."
                )

            original_exists = True

            original_sha = sha256_bytes(
                original
            )

            original_mode = stat.S_IMODE(
                path.stat().st_mode
            )

        else:
            original = b""
            original_exists = False
            original_sha = None
            original_mode = None

        new_data = new_text.encode(
            "utf-8"
        )

        if len(new_data) > MAX_EDIT_BYTES:
            raise ValueError(
                "El nuevo contenido supera "
                "el límite de SafeEditor."
            )

        if (
            original_exists
            and new_data == original
        ):
            raise ValueError(
                "La modificación no produce cambios."
            )

        transaction_id = (
            self._new_transaction_id()
        )

        tx_dir = self._transaction_path(
            transaction_id
        )

        tx_dir.mkdir(
            parents=True,
            exist_ok=False,
        )

        backup_path: Path | None = None

        if original_exists:
            backup_path = (
                tx_dir
                / "original.bin"
            )

            backup_path.write_bytes(
                original
            )

        transaction = ChangeTransaction(
            transaction_id=transaction_id,
            workspace=str(
                self.workspace
            ),
            target=str(path),
            relative_target=str(
                relative
            ),
            original_exists=original_exists,
            original_sha256=original_sha,
            applied_sha256=sha256_bytes(
                new_data
            ),
            backup_path=(
                str(backup_path)
                if backup_path
                else None
            ),
            original_mode=original_mode,
            status="prepared",
            created_at=utc_now(),
            updated_at=utc_now(),
        )

        self._save(
            transaction
        )

        try:
            self._atomic_write(
                path,
                new_data,
                mode=(
                    original_mode
                    if original_mode
                    is not None
                    else 0o644
                ),
            )

            current = path.read_bytes()

            current_sha = sha256_bytes(
                current
            )

            if (
                current_sha
                != transaction.applied_sha256
            ):
                raise RuntimeError(
                    "Hash posterior a escritura "
                    "no coincide."
                )

            transaction.status = "applied"
            transaction.updated_at = utc_now()

            self._save(
                transaction
            )

            return transaction

        except Exception as exc:

            transaction.status = "failed"
            transaction.error = str(exc)
            transaction.updated_at = utc_now()

            self._save(
                transaction
            )

            raise

    # ---------------------------------------------------------
    # Commit
    # ---------------------------------------------------------

    def commit(
        self,
        transaction_id: str,
    ) -> ChangeTransaction:

        transaction = self.load(
            transaction_id
        )

        if transaction.status != "applied":
            raise RuntimeError(
                "Solo una transacción aplicada "
                "puede confirmarse."
            )

        path = Path(
            transaction.target
        )

        if not path.exists():
            raise RuntimeError(
                "El archivo modificado "
                "ya no existe."
            )

        current_sha = sha256_bytes(
            path.read_bytes()
        )

        if (
            current_sha
            != transaction.applied_sha256
        ):
            raise RuntimeError(
                "El archivo cambió después "
                "de la transacción. "
                "Commit rechazado."
            )

        transaction.status = "committed"
        transaction.updated_at = utc_now()

        self._save(
            transaction
        )

        return transaction

    # ---------------------------------------------------------
    # Rollback
    # ---------------------------------------------------------

    def rollback(
        self,
        transaction_id: str,
    ) -> ChangeTransaction:

        transaction = self.load(
            transaction_id
        )

        if transaction.status != "applied":
            raise RuntimeError(
                "Solo una transacción aplicada "
                "puede revertirse."
            )

        path = Path(
            transaction.target
        )

        if not path.exists():
            raise RuntimeError(
                "El target cambió después "
                "de aplicar la transacción."
            )

        current_sha = sha256_bytes(
            path.read_bytes()
        )

        if (
            current_sha
            != transaction.applied_sha256
        ):
            raise RuntimeError(
                "El archivo fue modificado "
                "después de la transacción. "
                "Rollback automático rechazado "
                "para evitar perder cambios."
            )

        if transaction.original_exists:

            if not transaction.backup_path:
                raise RuntimeError(
                    "Backup inexistente."
                )

            backup = Path(
                transaction.backup_path
            )

            if not backup.exists():
                raise RuntimeError(
                    "Archivo de backup "
                    "no encontrado."
                )

            original = (
                backup.read_bytes()
            )

            if (
                sha256_bytes(original)
                != transaction.original_sha256
            ):
                raise RuntimeError(
                    "El backup no supera "
                    "la verificación SHA256."
                )

            self._atomic_write(
                path,
                original,
                mode=transaction.original_mode,
            )

        else:
            path.unlink()

        transaction.status = "rolled_back"
        transaction.updated_at = utc_now()

        self._save(
            transaction
        )

        return transaction
