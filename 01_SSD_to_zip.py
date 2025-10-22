# -*- coding: utf-8 -*-
r"""
Copia de Seguridad Eficiente (ZIP preferente con 7-Zip; fallback 7z/zip nativo)

Arquitectura: Facade + Strategy + Observer + Singleton + Pipeline (streaming O(1) RAM)
- Vía A (recomendada): 7-Zip CLI -> ZIP Deflate multihilo (muy rápido) o 7z (LZMA2).
- Vía B (fallback): zipfile nativo de Python (Deflate, streaming, sin dependencias).

Incluye:
- Exclusión de subdirectorios
- Progreso en consola
- Manifest JSON con metadatos
- Chequeo de espacio antes de comprimir
- Nombres Windows-safe (YYYY-MM-DDTHH-MM-SS, sin ':')
"""

import json
import logging
import math
import os
import shutil
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Generator, List, Optional, Tuple

# ========================= Logging =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ========================= Utilidades ======================
def bytes2human(n: int) -> str:
    if n <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = min(int(math.log(n, 1024)), len(units) - 1)
    return f"{round(n / (1024 ** i), 2)} {units[i]}"

def safe_timestamp() -> str:
    # Evita ":" en Windows
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S")

def ensure_space(out_dir: Path, needed_bytes: int, safety_factor: float = 1.05) -> bool:
    total, used, free = shutil.disk_usage(out_dir)
    need = int(needed_bytes * safety_factor)
    logging.info(f"[ESPACIO] Necesario (peor caso): {bytes2human(need)} | Libre: {bytes2human(free)}")
    return free >= need

@lru_cache(maxsize=4096)
def normalized(p: str) -> str:
    return os.path.normcase(os.path.normpath(p))

def is_under(child: str, parent: str) -> bool:
    try:
        return os.path.commonpath([normalized(child), normalized(parent)]) == normalized(parent)
    except Exception:
        return False

def write_listfile_atomic(out_path: Path, paths_iter: Generator[Path, None, None], prefer_utf8: bool = True) -> Tuple[Path, str]:
    """
    Escribe un listfile para 7-Zip y devuelve (ruta_listfile, scs_flag).
    - prefer_utf8=True -> UTF-8 con -scsUTF-8
    - prefer_utf8=False -> UTF-16LE con -scsUTF-16LE (máxima compatibilidad)
    """
    listfile = out_path.with_suffix(out_path.suffix + ".list.txt")
    if prefer_utf8:
        encoding = "utf-8"
        scs_flag = "-scsUTF-8"
    else:
        encoding = "utf-16-le"
        scs_flag = "-scsUTF-16LE"

    with open(listfile, "w", encoding=encoding, newline="\n") as lf:
        for p in paths_iter:
            lf.write(str(p) + "\n")
    return listfile, scs_flag

# ========================= Singleton Config =================
class ConfigManager:
    _instance: Optional["ConfigManager"] = None
    def __new__(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(
        self,
        sources: List[str],
        output_dir: str,
        excluded_dirs: List[str],
        preferred_format: str = "zip",   # "zip" (preferente) | "7z"
        zip_level: int = 6,              # 0..9 (Deflate). 6≈equilibrio
        seven_z_level: int = 7,          # 0..9 (LZMA2). 7≈rápido/compacto
    ):
        self.sources = [Path(s) for s in sources]
        self.output_dir = Path(output_dir)
        self.excluded_dirs = [Path(e).resolve() for e in excluded_dirs]
        self.preferred_format = preferred_format.lower()
        self.zip_level = min(max(zip_level, 0), 9)
        self.seven_z_level = min(max(seven_z_level, 0), 9)
        self.threads = max(1, (os.cpu_count() or 4) - 1)  # deja 1 libre

        for p in self.sources:
            if not p.exists():
                raise FileNotFoundError(f"Ruta de origen no existe: {p}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

# ========================= Observer =========================
class IObserver(ABC):
    @abstractmethod
    def update(self, message: str) -> None: ...

class ConsoleProgressObserver(IObserver):
    def update(self, message: str) -> None:
        logging.info(message)

# ========================= Walker (Pipeline) =================
class FileSystemWalker:
    def __init__(self, observers: Optional[List[IObserver]] = None):
        self._obs = observers or []

    def scan_totals(self, roots: List[Path], excluded_dirs: List[Path]) -> Tuple[int, int]:
        total_files, total_bytes = 0, 0
        for root in roots:
            for dirpath, dirnames, filenames in os.walk(root, topdown=True):
                # prune exclusiones
                dirnames[:] = [d for d in dirnames
                               if not any(is_under(os.path.join(dirpath, d), str(ex)) for ex in excluded_dirs)]
                for fn in filenames:
                    f = os.path.join(dirpath, fn)
                    try:
                        st = os.stat(f, follow_symlinks=False)
                    except Exception:
                        continue
                    total_files += 1
                    total_bytes += st.st_size
        return total_files, total_bytes

    def walk(self, roots: List[Path], excluded_dirs: List[Path]) -> Generator[Path, None, None]:
        count = 0
        for root in roots:
            yield root  # preserva dir raíz en ZIP
            for dirpath, dirnames, filenames in os.walk(root, topdown=True):
                dirnames[:] = [d for d in dirnames
                               if not any(is_under(os.path.join(dirpath, d), str(ex)) for ex in excluded_dirs)]
                for d in dirnames:
                    yield Path(os.path.join(dirpath, d))
                for fn in filenames:
                    count += 1
                    if count % 1000 == 0:
                        for o in self._obs:
                            o.update(f"{count} ficheros en cola...")
                    yield Path(os.path.join(dirpath, fn))

# ========================= Strategy =========================
class IArchiveStrategy(ABC):
    @abstractmethod
    def create(self, walker: FileSystemWalker, cfg: ConfigManager, out_path: Path) -> None: ...

def find_7z_exe() -> Optional[str]:
    candidates = [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
        r"C:\Windows\7z.exe",
        "7z.exe",
    ]
    for c in candidates:
        try:
            path = shutil.which(c) if os.path.basename(c) == c else (c if Path(c).exists() else None)
            if path:
                return path
        except Exception:
            continue
    return None

class SevenZipCliZipStrategy(IArchiveStrategy):
    """
    Usa 7-Zip CLI para crear ZIP Deflate multihilo.
    Pros: muy rápido, sólido, maneja caminos largos (-spf2) y exclusiones.
    """
    def create(self, walker: FileSystemWalker, cfg: ConfigManager, out_path: Path) -> None:
        sevenz = find_7z_exe()
        if not sevenz:
            raise RuntimeError("7z.exe no encontrado para estrategia CLI ZIP.")

        # 1) Escribimos listfile (UTF-8) y flag -scs
        listfile, scs_flag = write_listfile_atomic(out_path, walker.walk(cfg.sources, cfg.excluded_dirs), prefer_utf8=True)

        # 2) Exclusiones: absoluta + patrón por nombre (extra robustez)
        exclude_args = []
        for ex in cfg.excluded_dirs:
            exclude_args += [
                "-xr!" + str(ex),               # absoluto (con -spf2)
                "-xr!*" + ex.name + "*",        # patrón por nombre
            ]

        def build_cmd(listfile_path: Path, scs: str) -> List[str]:
            return [
                sevenz, "a",
                "-tzip",
                f"-mx={cfg.zip_level}",
                "-mm=Deflate",
                "-mmt=on",
                scs,                 # charset del listfile
                "-spf2",             # full paths unicode
                str(out_path),
                f"@{listfile_path}",
                *exclude_args,
            ]

        cmd = build_cmd(listfile, scs_flag)
        logging.info(f"[7z ZIP] Ejecutando: {' '.join(cmd)}")
        start = time.time()
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            if proc.returncode != 0:
                logging.error(proc.stdout)
                logging.error(proc.stderr)
                if "Incorrect item in listfile" in (proc.stdout + proc.stderr):
                    logging.warning("[7z ZIP] Reintentando con listfile UTF-16LE...")
                    # Reescribir listfile en UTF-16LE y rehacer comando
                    listfile2, scs_flag2 = write_listfile_atomic(out_path, walker.walk(cfg.sources, cfg.excluded_dirs), prefer_utf8=False)
                    cmd2 = build_cmd(listfile2, scs_flag2)
                    proc2 = subprocess.run(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
                    # Limpieza del segundo listfile
                    try:
                        listfile2.unlink(missing_ok=True)
                    except Exception:
                        pass
                    if proc2.returncode != 0:
                        logging.error(proc2.stdout)
                        logging.error(proc2.stderr)
                        raise RuntimeError(f"7-Zip devolvió código {proc2.returncode}")
                else:
                    raise RuntimeError(f"7-Zip devolvió código {proc.returncode}")
        finally:
            try:
                listfile.unlink(missing_ok=True)
            except Exception:
                pass
        logging.info(f"[7z ZIP] OK en {round(time.time()-start,1)}s")

class SevenZipCli7zStrategy(IArchiveStrategy):
    """7-Zip CLI para .7z (LZMA2 multihilo)."""
    def create(self, walker: FileSystemWalker, cfg: ConfigManager, out_path: Path) -> None:
        sevenz = find_7z_exe()
        if not sevenz:
            raise RuntimeError("7z.exe no encontrado para estrategia CLI 7z.")

        listfile, scs_flag = write_listfile_atomic(out_path, walker.walk(cfg.sources, cfg.excluded_dirs), prefer_utf8=True)

        exclude_args = []
        for ex in cfg.excluded_dirs:
            exclude_args += [
                "-xr!" + str(ex),
                "-xr!*" + ex.name + "*",
            ]

        def build_cmd(listfile_path: Path, scs: str) -> List[str]:
            return [
                sevenz, "a",
                "-t7z",
                "-m0=LZMA2",
                f"-mx={cfg.seven_z_level}",
                "-mmt=on",
                "-ms=on",           # solid on para mejor ratio
                scs,
                "-spf2",
                str(out_path),
                f"@{listfile_path}",
                *exclude_args,
            ]

        cmd = build_cmd(listfile, scs_flag)
        logging.info(f"[7z 7z] Ejecutando: {' '.join(cmd)}")
        start = time.time()
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            if proc.returncode != 0:
                logging.error(proc.stdout)
                logging.error(proc.stderr)
                if "Incorrect item in listfile" in (proc.stdout + proc.stderr):
                    logging.warning("[7z 7z] Reintentando con listfile UTF-16LE...")
                    listfile2, scs_flag2 = write_listfile_atomic(out_path, walker.walk(cfg.sources, cfg.excluded_dirs), prefer_utf8=False)
                    cmd2 = build_cmd(listfile2, scs_flag2)
                    proc2 = subprocess.run(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
                    try:
                        listfile2.unlink(missing_ok=True)
                    except Exception:
                        pass
                    if proc2.returncode != 0:
                        logging.error(proc2.stdout)
                        logging.error(proc2.stderr)
                        raise RuntimeError(f"7-Zip devolvió código {proc2.returncode}")
                else:
                    raise RuntimeError(f"7-Zip devolvió código {proc.returncode}")
        finally:
            try:
                listfile.unlink(missing_ok=True)
            except Exception:
                pass
        logging.info(f"[7z 7z] OK en {round(time.time()-start,1)}s")

class PythonZipStrategy(IArchiveStrategy):
    """
    Fallback puro-Python: zipfile con Deflate (streamed).
    Sin dependencias, muy estable. No es multihilo, pero es O(1) RAM.
    """
    def create(self, walker: FileSystemWalker, cfg: ConfigManager, out_path: Path) -> None:
        import zipfile
        compress_type = zipfile.ZIP_DEFLATED
        start = time.time()
        with zipfile.ZipFile(out_path, mode="w", compression=compress_type, compresslevel=cfg.zip_level, allowZip64=True) as zf:
            for p in walker.walk(cfg.sources, cfg.excluded_dirs):
                try:
                    if p.is_dir():
                        # Añade entrada de directorio para preservar estructura
                        zi = zipfile.ZipInfo(str(_arcname(p)))
                        zi.external_attr = 0o40775 << 16  # tipo dir
                        zf.writestr(zi, b"")
                    else:
                        zf.write(p, arcname=str(_arcname(p)))
                except FileNotFoundError:
                    continue
                except PermissionError as e:
                    logging.warning(f"Permiso denegado: {p} ({e})")
        logging.info(f"[zipfile] OK en {round(time.time()-start,1)}s")

def _arcname(path: Path) -> Path:
    """
    Construye arcname preservando el directorio raíz de cada fuente.
    Ej.: C:\...\Pictures\foo.jpg -> Pictures/foo.jpg
    """
    path = path.resolve()
    cfg = ConfigManager()
    candidates = sorted(cfg.sources, key=lambda r: len(str(r.resolve())), reverse=True)
    for root in candidates:
        r = root.resolve()
        if is_under(str(path), str(r)):
            rel = path.relative_to(r.parent)
            return Path(*rel.parts)
    return Path(path.name)

# ========================= Facade ===========================
class BackupFacade:
    def __init__(self, cfg: ConfigManager, observers: List[IObserver]):
        self.cfg = cfg
        self.obs = observers
        self.walker = FileSystemWalker(observers)

    def _pick_strategy(self) -> Tuple[IArchiveStrategy, str]:
        has_7z = find_7z_exe() is not None
        if self.cfg.preferred_format == "zip":
            if has_7z:
                return SevenZipCliZipStrategy(), "zip"
            return PythonZipStrategy(), "zip"
        # preferred 7z
        if has_7z:
            return SevenZipCli7zStrategy(), "7z"
        return PythonZipStrategy(), "zip"

    def execute(self) -> None:
        for o in self.obs:
            o.update("Iniciando copia de seguridad (híbrido ZIP/7z)...")

        # Escaneo para totales y espacio
        total_files, total_bytes = self.walker.scan_totals(self.cfg.sources, self.cfg.excluded_dirs)
        if total_files == 0 or total_bytes == 0:
            raise RuntimeError("No hay ficheros que respaldar; revisa rutas.")

        if not ensure_space(self.cfg.output_dir, total_bytes):
            raise RuntimeError("Espacio insuficiente en el destino.")

        ts = safe_timestamp()
        strategy, ext = self._pick_strategy()
        out_name = f"Copia_Seguridad_{ts}.{ext}"
        out_path = self.cfg.output_dir / out_name

        self._write_manifest_begin(out_path, total_files, total_bytes, ext)

        start = time.time()
        try:
            strategy.create(self.walker, self.cfg, out_path)
        except Exception:
            # Limpieza de parcial
            if out_path.exists():
                try:
                    out_path.unlink()
                except Exception:
                    pass
            raise
        elapsed = time.time() - start

        for o in self.obs:
            o.update("=" * 60)
            o.update(f"Archivo: {out_path}")
            try:
                size = out_path.stat().st_size
                o.update(f"Tamaño final: {bytes2human(size)} (fuente ~{bytes2human(total_bytes)})")
            except Exception:
                pass
        for o in self.obs:
            o.update(f"Duración: {int(elapsed//60)}m {elapsed%60:.1f}s")
            o.update("=" * 60)

        self._write_manifest_end(out_path, elapsed)

    def _write_manifest_begin(self, out_path: Path, total_files: int, total_bytes: int, ext: str) -> None:
        manifest = {
            "output": str(out_path),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "preferred_format": self.cfg.preferred_format,
            "used_format": ext,
            "sources": [str(s) for s in self.cfg.sources],
            "excluded": [str(e) for e in self.cfg.excluded_dirs],
            "totals": {"files": total_files, "bytes": total_bytes},
            "zip": {"level": self.cfg.zip_level},
            "7z": {"level": self.cfg.seven_z_level},
            "threads_hint": self.cfg.threads,
            "status": "running",
        }
        with open(str(out_path) + ".manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

    def _write_manifest_end(self, out_path: Path, elapsed: float) -> None:
        mpath = str(out_path) + ".manifest.json"
        try:
            with open(mpath, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            manifest = {}
        manifest.update({"status": "ok", "elapsed_seconds": round(elapsed, 2)})
        try:
            size = out_path.stat().st_size
            manifest["output_size_bytes"] = size
        except Exception:
            pass
        with open(mpath, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

# ========================= main =============================
def main():
    # --- Config por defecto (tus rutas) ---
    SOURCES = [
        r"C:\Users\PC\Documents",
        r"C:\Users\PC\Pictures"
    ]
    EXCLUDE_DIRS = [
        r"C:\Users\PC\Documents\example"
    ]
    OUTPUT_DIR = r"C:\Users\PC\Downloads"

    # Preferencia global: "zip" (recomendada) o "7z"
    PREFERRED_FORMAT = "zip"
    ZIP_LEVEL = 6       # 0..9 (6≈equilibrio). Más velocidad: 3–5; más compresión: 7–9.
    SEVEN_Z_LEVEL = 7   # 0..9

    cfg = ConfigManager()
    cfg.load(
        sources=SOURCES,
        output_dir=OUTPUT_DIR,
        excluded_dirs=EXCLUDE_DIRS,
        preferred_format=PREFERRED_FORMAT,
        zip_level=ZIP_LEVEL,
        seven_z_level=SEVEN_Z_LEVEL,
    )

    observer = ConsoleProgressObserver()
    facade = BackupFacade(cfg, [observer])

    try:
        facade.execute()
    except Exception as e:
        logging.error(f"Fallo crítico: {e}", exc_info=True)
        sys.exit(2)

if __name__ == "__main__":
    main()
