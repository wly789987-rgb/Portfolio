"""Create portfolio GIFs from existing Unity capture sequences, without changing the project."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('project', type=Path)
    args = parser.parse_args()
    try:
        import imageio_ffmpeg
    except ImportError:
        sys.path.insert(0, str(Path(os.environ['TEMP']) / 'portfolio-media-deps'))
        import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    captures = args.project / 'Captures'
    output = ROOT / 'assets/previews'
    output.mkdir(parents=True, exist_ok=True)
    catalog_file = output / 'catalog.json'
    catalog = json.loads(catalog_file.read_text(encoding='utf-8'))
    catalog = [r for r in catalog if not r['name'].startswith('turtle-') or r['name'] == 'turtle-opening']
    # The complete opening is recorded from Play Mode, never rebuilt from historical stills.
    jobs = []
    jobs += [('turtle-' + theme.lower(), title, 'ThemeAtmosphereV4/' + theme, 5, 32, 16)
             for theme, title in [('Standard', '常规 · 暖色烛光'), ('MildHorror', '微恐 · 青色薄雾'),
                                  ('Horror', '恐怖 · 冷色与红光'), ('Entertainment', '娱乐 · 彩色氛围')]]
    for name, title, folder, fps, count, poster_frame in jobs:
        source = captures / folder
        temporary = output / (name + '.gif')
        command = [ffmpeg, '-v', 'error', '-y', '-framerate', str(fps), '-i', str(source / '%03d.png'),
                   '-frames:v', str(count), '-filter_complex',
                   'scale=640:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4',
                   '-loop', '0', str(temporary)]
        subprocess.run(command, check=True, timeout=120)
        if temporary.stat().st_size > 1_200_000:
            command[command.index('-filter_complex') + 1] = command[command.index('-filter_complex') + 1].replace('scale=640', 'scale=480').replace('max_colors=96', 'max_colors=64')
            subprocess.run(command, check=True, timeout=120)
        data = temporary.read_bytes()
        digest = hashlib.sha256(data).hexdigest()[:20]
        gif = output / (digest + '.gif')
        temporary.replace(gif)
        image = Image.open(source / f'{poster_frame:03d}.png').convert('RGB')
        image.thumbnail((960, 540))
        poster_temporary = output / (name + '.webp')
        image.save(poster_temporary, 'WEBP', quality=80, method=0)
        poster_digest = hashlib.sha256(poster_temporary.read_bytes()).hexdigest()[:20]
        poster = output / (poster_digest + '.webp')
        poster_temporary.replace(poster)
        with Image.open(gif) as animation:
            assert animation.n_frames > 1
            seconds = sum((animation.seek(i) or animation.info.get('duration', 0)) for i in range(animation.n_frames)) / 1000
            record = {'name': name, 'title': title, 'src': gif.relative_to(ROOT).as_posix(),
                      'poster': poster.relative_to(ROOT).as_posix(), 'bytes': len(data),
                      'frames': animation.n_frames, 'source': 'Turtle Soup / Captures/' + folder,
                      'start': 7.5 if name == 'turtle-opening' else 12,
                      'seconds': seconds, 'fps': fps}
        catalog.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
    catalog_file.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
