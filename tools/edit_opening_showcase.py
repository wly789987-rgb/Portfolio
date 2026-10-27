"""Shorten the silent single-candle wait using original Play Mode frames and timestamps."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('capture', type=Path)
    args = parser.parse_args()
    try:
        import imageio_ffmpeg
    except ImportError:
        sys.path.insert(0, str(Path(os.environ['TEMP']) / 'portfolio-media-deps'))
        import imageio_ffmpeg
    report = json.loads((args.capture / 'capture.json').read_text(encoding='utf-8'))
    # Preserve the exterior and entry; skip the long, silent rules narration wait.
    segments = [(0.0, 20.8), (50.2, report['duration'])]
    output = ROOT / 'output/turtle-soup'
    working = output / 'runtime-opening'
    working.mkdir(parents=True, exist_ok=True)
    lines = ['ffconcat version 1.0']
    count = 0
    for start, end in segments:
        selected = [f for f in report['frames'] if start <= f['time'] < end]
        for i, frame in enumerate(selected):
            following = selected[i + 1]['time'] if i + 1 < len(selected) else end
            timestamp = frame['time'] if i else start
            lines.extend(["file '" + (args.capture / frame['file']).as_posix() + "'",
                          'duration ' + str(max(.01, following - timestamp))])
            count += 1
        final = args.capture / selected[-1]['file']
    lines.append("file '" + final.as_posix() + "'")
    concat = working / 'showcase.ffconcat'
    concat.write_text('\n'.join(lines), encoding='utf-8')
    results = []
    for width, name in [(960, '01-opening-showcase.gif'), (640, '01-opening-showcase-web.gif')]:
        target = output / name
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-y', '-threads', '2',
                        '-f', 'concat', '-safe', '0', '-i', str(concat), '-filter_complex',
                        f'scale={width}:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=256:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3',
                        '-fps_mode', 'vfr', '-loop', '0', str(target)], check=True, timeout=240)
        with Image.open(target) as image:
            seconds = sum((image.seek(i) or image.info.get('duration', 0)) for i in range(image.n_frames)) / 1000
            results.append({'file': name, 'bytes': target.stat().st_size, 'seconds': seconds,
                            'frames': image.n_frames, 'width': image.width, 'height': image.height})
        print(json.dumps(results[-1]), flush=True)
    (working / 'showcase-edit.json').write_text(json.dumps({'source': args.capture.as_posix(),
        'source_duration': report['duration'], 'kept_intervals': segments,
        'sampled_frames': count, 'results': results}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
