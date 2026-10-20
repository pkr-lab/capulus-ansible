#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from urllib.parse import quote

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
RESIZABLE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
PARTIAL_DIR = ".partial"
TARGET_MARKER = ".target"
MIN_SCREEN = (640, 480)


def log(message):
    print(message, flush=True)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--media", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--max-width", type=int, default=1920)
    parser.add_argument("--max-height", type=int, default=1080)
    parser.add_argument("--jpeg-quality", type=int, default=85)
    parser.add_argument("--screen-file")
    parser.add_argument("--settle-seconds", type=int, default=5)
    parser.add_argument("--mount-timeout", type=int, default=30)
    return parser.parse_args()


def ensure_mounted(path, timeout):
    if os.path.ismount(path):
        return True
    try:
        subprocess.run(["mount", path], check=True, timeout=timeout, capture_output=True)
    except (subprocess.SubprocessError, OSError) as error:
        log("mount fehlgeschlagen: %s" % error)
        return False
    return os.path.ismount(path)


def imagemagick(tool):
    if shutil.which(tool):
        return [tool]
    if shutil.which("magick"):
        return ["magick", tool]
    return None


def fsync_path(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def list_source(path):
    entries = {}
    with os.scandir(path) as iterator:
        for entry in iterator:
            if entry.name.startswith("."):
                continue
            if os.path.splitext(entry.name)[1].lower() not in IMAGE_EXTENSIONS:
                continue
            if not entry.is_file():
                continue
            entries[entry.name] = entry.stat()
    return entries


def list_cache(path):
    names = set()
    with os.scandir(path) as iterator:
        for entry in iterator:
            if entry.name.startswith(".") or not entry.is_file():
                continue
            names.add(entry.name)
    return names


def is_current(destination, source_stat):
    try:
        cached = os.stat(destination)
    except FileNotFoundError:
        return False
    return int(cached.st_mtime) == int(source_stat.st_mtime)


def exceeds_limits(source, args):
    identify = imagemagick("identify")
    if identify is None:
        return False
    try:
        result = subprocess.run(
            identify + ["-ping", "-format", "%w %h", source + "[0]"],
            check=True, capture_output=True, text=True, timeout=60,
        )
        width, height = (int(value) for value in result.stdout.split()[:2])
    except (subprocess.SubprocessError, OSError, ValueError):
        return False
    return width > args.max_width or height > args.max_height


def resize(source, target, args):
    convert = imagemagick("convert")
    if convert is None:
        return False
    command = ["nice", "-n", "19"] + convert + [
        "-limit", "memory", "256MiB", "-limit", "map", "512MiB",
        source + "[0]",
        "-auto-orient",
        "-resize", "%dx%d>" % (args.max_width, args.max_height),
        "-strip",
        "-quality", str(args.jpeg_quality),
        target,
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, timeout=300)
    except (subprocess.SubprocessError, OSError) as error:
        log("skalieren fehlgeschlagen fuer %s: %s" % (source, error))
        return False
    return os.path.getsize(target) > 0


def produce(source, target, extension, args):
    if extension in RESIZABLE_EXTENSIONS and exceeds_limits(source, args):
        if resize(source, target, args):
            return "skaliert"
    shutil.copyfile(source, target)
    return "kopiert"


def sync_file(name, source_dir, media_dir, source_stat, args):
    source = os.path.join(source_dir, name)
    destination = os.path.join(media_dir, name)
    target = os.path.join(media_dir, PARTIAL_DIR, name)
    extension = os.path.splitext(name)[1].lower()
    try:
        mode = produce(source, target, extension, args)
        after = os.stat(source)
        if after.st_size != source_stat.st_size or after.st_mtime_ns != source_stat.st_mtime_ns:
            raise RuntimeError("Quelle waehrend des Kopierens veraendert")
        if os.path.getsize(target) == 0:
            raise RuntimeError("Zieldatei leer")
        fsync_path(target)
        os.utime(target, (source_stat.st_atime, source_stat.st_mtime))
        os.chmod(target, 0o644)
        os.replace(target, destination)
    except (OSError, RuntimeError) as error:
        log("uebersprungen %s: %s" % (name, error))
        try:
            os.unlink(target)
        except FileNotFoundError:
            pass
        return False
    log("%s: %s" % (mode, name))
    return True


def write_manifest(media_dir, manifest_path):
    items = []
    for name in sorted(list_cache(media_dir)):
        items.append({
            "src": "media/" + quote(name),
            "v": int(os.stat(os.path.join(media_dir, name)).st_mtime),
        })
    content = "window.XIBO_MANIFEST=" + json.dumps(items, separators=(",", ":")) + ";\n"
    try:
        with open(manifest_path, "r", encoding="utf-8") as handle:
            if handle.read() == content:
                return False
    except FileNotFoundError:
        pass
    temporary = manifest_path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temporary, 0o644)
    os.replace(temporary, manifest_path)
    log("manifest aktualisiert: %d Bilder" % len(items))
    return True


def resolve_target(args):
    width, height = args.max_width, args.max_height
    if args.screen_file:
        try:
            with open(args.screen_file, "r", encoding="utf-8") as handle:
                screen_width, screen_height = (int(value) for value in handle.read().split()[:2])
        except (OSError, ValueError):
            return width, height
        if screen_width >= MIN_SCREEN[0] and screen_height >= MIN_SCREEN[1]:
            width, height = min(width, screen_width), min(height, screen_height)
    return width, height


def read_marker(media_dir):
    try:
        with open(os.path.join(media_dir, TARGET_MARKER), "r", encoding="utf-8") as handle:
            return handle.read().strip()
    except OSError:
        return ""


def write_marker(media_dir, value):
    path = os.path.join(media_dir, TARGET_MARKER)
    with open(path + ".tmp", "w", encoding="utf-8") as handle:
        handle.write(value + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(path + ".tmp", path)


def prepare_media_dir(media_dir):
    os.makedirs(media_dir, exist_ok=True)
    partial = os.path.join(media_dir, PARTIAL_DIR)
    shutil.rmtree(partial, ignore_errors=True)
    os.makedirs(partial, exist_ok=True)


def main():
    args = parse_args()
    prepare_media_dir(args.media)
    args.max_width, args.max_height = resolve_target(args)
    target = "%dx%d" % (args.max_width, args.max_height)
    force = read_marker(args.media) != target
    if force:
        log("Zielaufloesung %s, Bilder werden neu verarbeitet" % target)
    failed = False

    exit_code = 0
    if not ensure_mounted(args.source, args.mount_timeout):
        log("Quelle nicht erreichbar, behalte Cache")
        exit_code = 1
    else:
        try:
            source_entries = list_source(args.source)
        except OSError as error:
            log("Quelle nicht lesbar: %s" % error)
            source_entries = None
            exit_code = 1

        if source_entries is not None:
            now = time.time()
            for name in sorted(source_entries):
                stat = source_entries[name]
                if now - stat.st_mtime < args.settle_seconds:
                    failed = True
                    continue
                if not force and is_current(os.path.join(args.media, name), stat):
                    continue
                if not sync_file(name, args.source, args.media, stat, args):
                    failed = True

            if source_entries and not failed:
                try:
                    write_marker(args.media, target)
                except OSError as error:
                    log("marker schreiben fehlgeschlagen: %s" % error)

            if source_entries:
                for name in list_cache(args.media) - set(source_entries):
                    try:
                        os.unlink(os.path.join(args.media, name))
                        log("entfernt: %s" % name)
                    except OSError as error:
                        log("entfernen fehlgeschlagen %s: %s" % (name, error))
            else:
                log("Quelle ohne Bilder, behalte Cache")

    try:
        write_manifest(args.media, args.manifest)
        fsync_path(args.media)
    except OSError as error:
        log("manifest schreiben fehlgeschlagen: %s" % error)
        exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
