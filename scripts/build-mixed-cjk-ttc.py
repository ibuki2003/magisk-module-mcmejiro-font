#!/usr/bin/env python3
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

try:
  from fontTools.ttLib import TTCollection, TTFont
except ImportError as exc:
  raise SystemExit(
    "fontTools is required. Install it or run with a nix shell that provides "
    "python3Packages.fonttools."
  ) from exc


FONT_NAMES = (
  "NotoSansCJK-Regular.ttc",
  "NotoSerifCJK-Regular.ttc",
)


def repo_root() -> Path:
  return Path(__file__).resolve().parents[1]


def run_adb_pull(stock_dir: Path) -> None:
  adb = shutil.which("adb")
  if adb is None:
    raise SystemExit("adb was not found in PATH.")

  stock_dir.mkdir(parents=True, exist_ok=True)
  root_device = subprocess.check_output(
    [
      adb,
      "shell",
      "su",
      "-c",
      "mount | awk '$3 == \"/\" {print $1; exit}'",
    ],
    text=True,
  ).strip()
  if not root_device:
    raise SystemExit("Failed to find root block device from adb shell.")

  mountpoint = "/data/local/tmp/mcmejiro_orig_system"
  subprocess.run(
    [
      adb,
      "shell",
      "su",
      "-c",
      (
        f"umount {mountpoint} 2>/dev/null; "
        f"mkdir -p {mountpoint} && "
        f"mount -t ext4 -o ro {root_device} {mountpoint}"
      ),
    ],
    check=True,
  )
  try:
    for name in FONT_NAMES:
      destination = stock_dir / name
      command = [
        adb,
        "pull",
        f"{mountpoint}/system/fonts/{name}",
        str(destination),
      ]
      subprocess.run(command, check=True)
  finally:
    subprocess.run(
      [
        adb,
        "shell",
        "su",
        "-c",
        f"umount {mountpoint}; rmdir {mountpoint}",
      ],
      check=False,
    )


def name_records(font: TTFont) -> set[str]:
  names = set()
  for record in font["name"].names:
    if record.nameID in {1, 4, 6}:
      try:
        names.add(record.toUnicode())
      except UnicodeDecodeError:
        pass
  return names


def looks_like_mcmejiro_collection(path: Path) -> bool:
  collection = TTCollection(str(path))
  try:
    if not collection.fonts:
      return False
    return all(
      any("McMejiro" in name for name in name_records(font))
      for font in collection.fonts
    )
  finally:
    for font in collection.fonts:
      font.close()


def build_mixed_ttc(
  stock_path: Path,
  mcmejiro_path: Path,
  output_path: Path,
  replace_index: int,
) -> None:
  if not stock_path.exists():
    raise SystemExit(f"Stock TTC not found: {stock_path}")
  if not mcmejiro_path.exists():
    raise SystemExit(f"McMejiro font not found: {mcmejiro_path}")
  if stock_path.resolve() == output_path.resolve():
    raise SystemExit("Refusing to overwrite the stock input TTC in place.")
  if looks_like_mcmejiro_collection(stock_path):
    raise SystemExit(
      f"{stock_path} looks like the old all-McMejiro alias TTC, not a stock TTC."
    )

  stock = TTCollection(str(stock_path))
  try:
    font_count = len(stock.fonts)
    if replace_index < 0 or replace_index >= font_count:
      raise SystemExit(
        f"replace index {replace_index} is out of range for {stock_path} "
        f"({font_count} fonts)."
      )

    mixed_fonts = []
    for index, font in enumerate(stock.fonts):
      if index == replace_index:
        mixed_fonts.append(TTFont(str(mcmejiro_path)))
      else:
        mixed_fonts.append(font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    mixed = TTCollection()
    mixed.fonts = mixed_fonts
    mixed.save(str(output_path))
  finally:
    for font in stock.fonts:
      font.close()


def describe_ttc(path: Path) -> str:
  collection = TTCollection(str(path))
  try:
    parts = []
    for index, font in enumerate(collection.fonts):
      names = sorted(name_records(font))
      display_name = names[0] if names else "(unknown)"
      parts.append(f"index {index}: {display_name}")
    return "\n".join(parts)
  finally:
    for font in collection.fonts:
      font.close()


def main() -> int:
  root = repo_root()
  parser = argparse.ArgumentParser(
    description="Build mixed CJK TTC aliases for the Magisk module.",
  )
  parser.add_argument(
    "--stock-dir",
    type=Path,
    default=root / "build" / "stock-fonts",
    help="Directory containing stock NotoSansCJK/NotoSerifCJK TTC files.",
  )
  parser.add_argument(
    "--stock-sans",
    type=Path,
    help="Stock sans CJK TTC path. Overrides --stock-dir for sans.",
  )
  parser.add_argument(
    "--stock-serif",
    type=Path,
    help="Stock serif CJK TTC path. Overrides --stock-dir for serif.",
  )
  parser.add_argument(
    "--output-dir",
    type=Path,
    default=root / "system" / "fonts",
    help="Directory where mixed TTC files are written.",
  )
  parser.add_argument(
    "--mcmejiro",
    type=Path,
    default=root / "system" / "fonts" / "McMejiro-Regular.ttf",
    help="McMejiro TTF used for the Japanese index.",
  )
  parser.add_argument(
    "--replace-index",
    type=int,
    default=0,
    help="TTC index to replace with McMejiro. Pixel A17 stock ja is index 0.",
  )
  parser.add_argument(
    "--pull-adb",
    action="store_true",
    help="Pull stock TTC files from the connected device's lower system image first.",
  )
  args = parser.parse_args()

  stock_dir = args.stock_dir.resolve()
  output_dir = args.output_dir.resolve()

  if args.pull_adb:
    run_adb_pull(stock_dir)

  stock_paths = {
    "NotoSansCJK-Regular.ttc": (
      args.stock_sans.resolve() if args.stock_sans else stock_dir / "NotoSansCJK-Regular.ttc"
    ),
    "NotoSerifCJK-Regular.ttc": (
      args.stock_serif.resolve() if args.stock_serif else stock_dir / "NotoSerifCJK-Regular.ttc"
    ),
  }

  for name in FONT_NAMES:
    stock_path = stock_paths[name]
    output_path = output_dir / name
    build_mixed_ttc(
      stock_path=stock_path,
      mcmejiro_path=args.mcmejiro.resolve(),
      output_path=output_path,
      replace_index=args.replace_index,
    )
    print(f"Wrote {output_path}")
    print(describe_ttc(output_path))

  return 0


if __name__ == "__main__":
  raise SystemExit(main())
