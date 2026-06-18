#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reparer_videos.py

Repare les videos AVI corrompues (trail cam) en les faisant remuxer par VLC,
exactement comme le "Fixing avi index..." que VLC fait a l'ouverture.
On conserve les dates (creation/modification) du fichier original.

----------------------------------------------------------------------------
Ligne manuelle equivalente (ce que le script lance pour toi) :

  vlc -I dummy "DSCF0630.avi" --sout="#standard{access=file,mux=avi,dst=DSCF0630-fixed.avi}" vlc://quit

Version transcode (H.264 / MP4) si tu utilises --transcode :

  vlc -I dummy "DSCF0630.avi" --sout="#transcode{vcodec=h264,vb=8000,acodec=none}:standard{access=file,mux=mp4,dst=DSCF0630-fixed.mp4}" vlc://quit
----------------------------------------------------------------------------

Exemples d'utilisation :

  # Un seul fichier, sortie dans ./fixed/DSCF0630-fixed.avi
  python reparer_videos.py DSCF0630.avi

  # Tout un dossier, sortie dans un autre dossier
  python reparer_videos.py D:\trail_cam\101MEDIA D:\trail_cam\repare

  # Suffixe personnalise
  python reparer_videos.py 101MEDIA --suffix _ok

  # Recompression MP4 au lieu du remux sans perte
  python reparer_videos.py 101MEDIA --transcode

  # Aucun argument : un petit menu interactif s'ouvre
  python reparer_videos.py
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Extensions video qu'on cherche dans un dossier
VIDEO_EXTS = {".avi", ".mp4", ".mov", ".mkv", ".m4v", ".mpg", ".mpeg", ".wmv"}

# Correspondance extension -> muxer VLC (pour le mode sans transcode)
MUX_BY_EXT = {
    ".avi": "avi",
    ".mp4": "mp4",
    ".m4v": "mp4",
    ".mov": "mp4",
    ".mkv": "matroska",
    ".mpg": "mpeg1",
    ".mpeg": "mpeg1",
    ".wmv": "asf",
}


# --------------------------------------------------------------------------
# Localisation de VLC
# --------------------------------------------------------------------------
def find_vlc(user_path=None):
    if user_path:
        return user_path

    candidates = []
    if os.name == "nt":
        candidates += [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
        ]
    elif sys.platform == "darwin":
        candidates += ["/Applications/VLC.app/Contents/MacOS/VLC"]

    found_in_path = shutil.which("vlc")
    if found_in_path:
        candidates.insert(0, found_in_path)

    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


# --------------------------------------------------------------------------
# Conservation des dates (creation incluse sur Windows)
# --------------------------------------------------------------------------
def _set_times_windows(path, atime, mtime, ctime):
    """Recopie la date de creation Windows via l'API SetFileTime (sans dependance)."""
    import ctypes
    from ctypes import wintypes

    FILE_WRITE_ATTRIBUTES = 0x100
    OPEN_EXISTING = 3
    FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    INVALID = ctypes.c_void_p(-1).value
    EPOCH_OFFSET = 116444736000000000  # intervalles de 100 ns entre 1601 et 1970

    def to_filetime(ts):
        ft = int(ts * 10_000_000) + EPOCH_OFFSET
        return wintypes.FILETIME(ft & 0xFFFFFFFF, ft >> 32)

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
        wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]

    handle = k32.CreateFileW(
        str(path), FILE_WRITE_ATTRIBUTES, 0, None,
        OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS, None,
    )
    if handle == INVALID or not handle:
        raise ctypes.WinError(ctypes.get_last_error())

    try:
        k32.SetFileTime.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
        ]
        c, a, m = to_filetime(ctime), to_filetime(atime), to_filetime(mtime)
        ok = k32.SetFileTime(handle, ctypes.byref(c), ctypes.byref(a), ctypes.byref(m))
        if not ok:
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        k32.CloseHandle(handle)


def copy_timestamps(src, dst):
    st = os.stat(src)
    # mtime + atime partout
    os.utime(dst, (st.st_atime, st.st_mtime))
    # date de creation : Windows seulement (st_ctime = creation sous Windows)
    if os.name == "nt":
        try:
            _set_times_windows(dst, st.st_atime, st.st_mtime, st.st_ctime)
        except OSError as e:
            print(f"   (date de creation non recopiee : {e})")


# --------------------------------------------------------------------------
# Construction de la commande VLC et reparation d'un fichier
# --------------------------------------------------------------------------
def build_sout(dst, transcode):
    # VLC accepte les slashs avant sur Windows, ce qui evite les soucis
    # de parsing avec ':' (lettre de lecteur) et '\' dans le --sout.
    dst_str = str(dst).replace("\\", "/")
    ext = dst.suffix.lower()
    mux = MUX_BY_EXT.get(ext, "avi")

    if transcode:
        # acodec=none : on jette le flux audio bidon de la cam (sample rate 0)
        return (f"#transcode{{vcodec=h264,vb=8000,acodec=none}}:"
                f"standard{{access=file,mux={mux},dst={dst_str}}}")
    return f"#standard{{access=file,mux={mux},dst={dst_str}}}"


def repair_one(vlc, src, dst, transcode):
    dst.parent.mkdir(parents=True, exist_ok=True)
    sout = build_sout(dst, transcode)
    cmd = [vlc, "-I", "dummy", "--quiet", str(src), f"--sout={sout}", "vlc://quit"]

    result = subprocess.run(cmd, capture_output=True, text=True)

    # VLC renvoie souvent 0 meme en cas de souci : on valide le fichier de sortie.
    if not dst.exists() or dst.stat().st_size == 0:
        err = (result.stderr or "").strip().splitlines()
        detail = err[-1] if err else f"code de sortie {result.returncode}"
        raise RuntimeError(f"VLC n'a pas produit de fichier valide ({detail})")

    copy_timestamps(src, dst)


# --------------------------------------------------------------------------
# Resolution des chemins (input/output, fichier ou dossier)
# --------------------------------------------------------------------------
def output_is_dir(out_p):
    if out_p.exists():
        return out_p.is_dir()
    # N'existe pas encore : pas d'extension -> on suppose un dossier
    return out_p.suffix == ""


def target_ext(default_transcode):
    return ".mp4" if default_transcode else ".avi"


def build_jobs(input_path, output, suffix, transcode, recursive):
    in_p = Path(input_path).expanduser()
    if not in_p.exists():
        raise FileNotFoundError(f"Introuvable : {in_p}")

    # Liste des fichiers source
    if in_p.is_file():
        sources = [in_p]
    else:
        if recursive:
            sources = sorted(p for p in in_p.rglob("*")
                             if p.is_file() and p.suffix.lower() in VIDEO_EXTS)
        else:
            sources = sorted(p for p in in_p.iterdir()
                             if p.is_file() and p.suffix.lower() in VIDEO_EXTS)

    if not sources:
        raise FileNotFoundError("Aucune video trouvee a reparer.")

    out_p = Path(output).expanduser() if output else None
    ext = target_ext(transcode)

    # input = dossier mais output pointe vers un fichier -> impossible
    if in_p.is_dir() and out_p is not None and not output_is_dir(out_p):
        raise ValueError("L'entree est un dossier : la sortie doit etre un dossier, pas un fichier.")

    jobs = []
    for src in sources:
        if out_p is None:
            # Sous-dossier "fixed" a cote de l'original
            dst = src.parent / "fixed" / f"{src.stem}{suffix}{ext}"
        elif output_is_dir(out_p):
            dst = out_p / f"{src.stem}{suffix}{ext}"
        else:
            # Sortie = fichier explicite (cas un seul fichier en entree)
            dst = out_p

        if dst.resolve() == src.resolve():
            raise ValueError(f"La sortie ecraserait l'original : {src}")
        jobs.append((src, dst))

    return jobs


# --------------------------------------------------------------------------
# Menu interactif (si aucun argument)
# --------------------------------------------------------------------------
def clean(s):
    return s.strip().strip('"').strip("'")


def interactive_menu(default_suffix):
    print("=" * 60)
    print("  Reparation de videos (trail cam) via VLC")
    print("=" * 60)

    input_path = clean(input("Fichier ou dossier a reparer : "))
    while not input_path or not Path(input_path).expanduser().exists():
        input_path = clean(input("  Chemin invalide. Reessaie : "))

    output = clean(input("Sortie (vide = sous-dossier fixed/) : ")) or None

    suffix = clean(input(f"Suffixe [{default_suffix}] : ")) or default_suffix

    transcode = clean(input("Recompresser en MP4 H.264 ? (o/N) : ")).lower() in ("o", "oui", "y", "yes")

    recursive = False
    if Path(input_path).expanduser().is_dir():
        recursive = clean(input("Inclure les sous-dossiers ? (o/N) : ")).lower() in ("o", "oui", "y", "yes")

    print()
    return input_path, output, suffix, transcode, recursive


# --------------------------------------------------------------------------
# Programme principal
# --------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Repare des videos corrompues (trail cam) via VLC en conservant les dates.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", nargs="?", help="Fichier ou dossier a reparer")
    parser.add_argument("output", nargs="?", help="Fichier ou dossier de sortie (optionnel)")
    parser.add_argument("--suffix", default="-fixed", help='Suffixe ajoute au nom (defaut : "-fixed")')
    parser.add_argument("--transcode", action="store_true",
                        help="Recompresser en H.264/MP4 au lieu du remux sans perte")
    parser.add_argument("-r", "--recursive", action="store_true",
                        help="Parcourir aussi les sous-dossiers")
    parser.add_argument("--vlc", help="Chemin vers l'executable VLC (sinon detection auto)")
    args = parser.parse_args()

    # Pas d'argument d'entree -> menu
    if args.input is None:
        args.input, args.output, args.suffix, args.transcode, args.recursive = \
            interactive_menu(args.suffix)

    vlc = find_vlc(args.vlc)
    if not vlc:
        print("VLC introuvable. Installe-le ou passe --vlc \"chemin\\vers\\vlc.exe\".")
        sys.exit(1)

    try:
        jobs = build_jobs(args.input, args.output, args.suffix, args.transcode, args.recursive)
    except (FileNotFoundError, ValueError) as e:
        print(f"Erreur : {e}")
        sys.exit(1)

    print(f"VLC : {vlc}")
    print(f"{len(jobs)} fichier(s) a traiter.\n")

    ok, fail = 0, 0
    for i, (src, dst) in enumerate(jobs, 1):
        print(f"[{i}/{len(jobs)}] {src.name} -> {dst.name}")
        try:
            repair_one(vlc, src, dst, args.transcode)
            print("   OK")
            ok += 1
        except (RuntimeError, OSError) as e:
            print(f"   ECHEC : {e}")
            fail += 1

    print(f"\nTermine : {ok} reparee(s), {fail} en echec.")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()