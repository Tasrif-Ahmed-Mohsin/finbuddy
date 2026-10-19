import sys, glob
from PIL import Image, ImageDraw
d, out, cols = sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 3
fs = sorted(glob.glob(d + '/*.png'))
w, h = 640, 360
rows = (len(fs) + cols - 1) // cols
sh = Image.new('RGB', (cols * (w + 8), rows * (h + 8)), 'white')
dr = ImageDraw.Draw(sh)
for i, f in enumerate(fs):
    im = Image.open(f).convert('RGB').resize((w, h))
    x, y = (i % cols) * (w + 8), (i // cols) * (h + 8)
    sh.paste(im, (x, y)); dr.text((x + 6, y + 4), __import__('os').path.basename(f), fill='yellow')
sh.save(out, quality=88)
print(sh.size)
