#!/usr/bin/env python3
"""Erstellt Muster-Designs und Artikelbilder fuer Tests"""
from PIL import Image, ImageDraw, ImageFont
import os, math

# Verzeichnisse
os.makedirs('static/uploads/designs', exist_ok=True)
os.makedirs('static/uploads/articles', exist_ok=True)
os.makedirs('static/uploads/articles/thumbs', exist_ok=True)
os.makedirs('static/thumbnails/designs', exist_ok=True)

# Font-Helper
def get_font(size, bold=False):
    paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        'C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf',
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except:
            continue
    return ImageFont.load_default()

# ============================================================
# 1. STICKLOGO: Firmenlogo Brust
# ============================================================
img = Image.new('RGBA', (800, 600), (255, 255, 255, 0))
draw = ImageDraw.Draw(img)
draw.ellipse([200, 50, 600, 450], outline='#1a6b5a', width=8)
draw.ellipse([220, 70, 580, 430], outline='#228a73', width=3)
cx, cy = 400, 250
points = []
for i in range(5):
    angle = math.radians(-90 + i * 72)
    points.append((cx + 80 * math.cos(angle), cy + 80 * math.sin(angle)))
    angle2 = math.radians(-90 + i * 72 + 36)
    points.append((cx + 35 * math.cos(angle2), cy + 35 * math.sin(angle2)))
draw.polygon(points, fill='#1a6b5a')
draw.text((400, 480), 'MUSTER STICKEREI', fill='#1a6b5a', font=get_font(42, True), anchor='mm')
draw.text((400, 530), 'EST. 2024 - WUPPERTAL', fill='#6c757d', font=get_font(24), anchor='mm')
img.save('static/uploads/designs/muster_sticklogo_brust.png')
thumb = img.copy(); thumb.thumbnail((200, 200))
thumb.save('static/thumbnails/designs/muster_sticklogo_brust_thumb.png')
print('1. Sticklogo Brust erstellt')

# ============================================================
# 2. DRUCKLOGO: Ruecken (gross, bunt)
# ============================================================
img2 = Image.new('RGBA', (1000, 800), (255, 255, 255, 0))
draw2 = ImageDraw.Draw(img2)
draw2.rounded_rectangle([50, 50, 950, 750], radius=40, fill='#e74c3c')
draw2.text((500, 200), 'TEAM', fill='white', font=get_font(72, True), anchor='mm')
draw2.text((500, 300), 'WUPPERTAL', fill='#ffd700', font=get_font(72, True), anchor='mm')
draw2.line([150, 380, 850, 380], fill='white', width=3)
draw2.text((500, 430), 'SPORT - STYLE - TOGETHER', fill='white', font=get_font(36, True), anchor='mm')
draw2.text((500, 550), '# 42', fill='#ffd700', font=get_font(72, True), anchor='mm')
draw2.text((500, 680), 'DTF FLEX TRANSFER', fill=(255,255,255,180), font=get_font(28), anchor='mm')
img2.save('static/uploads/designs/muster_drucklogo_ruecken.png')
thumb2 = img2.copy(); thumb2.thumbnail((200, 200))
thumb2.save('static/thumbnails/designs/muster_drucklogo_ruecken_thumb.png')
print('2. Drucklogo Ruecken erstellt')

# ============================================================
# 3. DTF-TRANSFER: Aermel (klein, rund)
# ============================================================
img3 = Image.new('RGBA', (400, 400), (255, 255, 255, 0))
draw3 = ImageDraw.Draw(img3)
draw3.ellipse([20, 20, 380, 380], fill='#2c3e50')
draw3.ellipse([35, 35, 365, 365], outline='#f39c12', width=4)
draw3.text((200, 180), 'W', fill='#f39c12', font=get_font(140, True), anchor='mm')
draw3.text((200, 310), 'WUPPERTAL', fill='white', font=get_font(20), anchor='mm')
draw3.text((200, 340), 'ATHLETICS', fill='#bdc3c7', font=get_font(20), anchor='mm')
img3.save('static/uploads/designs/muster_dtf_aermel.png')
thumb3 = img3.copy(); thumb3.thumbnail((200, 200))
thumb3.save('static/thumbnails/designs/muster_dtf_aermel_thumb.png')
print('3. DTF Aermel-Logo erstellt')

# ============================================================
# 4. T-SHIRT ARTIKELBILD (Navy)
# ============================================================
img4 = Image.new('RGB', (600, 700), (245, 245, 245))
draw4 = ImageDraw.Draw(img4)
body = [(120, 200), (120, 620), (480, 620), (480, 200), (530, 120),
        (370, 120), (340, 100), (300, 90), (260, 100), (230, 120),
        (70, 120), (120, 200)]
right_sleeve = [(480, 200), (560, 280), (560, 170), (530, 120)]
left_sleeve = [(120, 200), (40, 280), (40, 170), (70, 120)]
draw4.polygon(body, fill='#2c3e50', outline='#1a252f')
draw4.polygon(right_sleeve, fill='#2c3e50', outline='#1a252f')
draw4.polygon(left_sleeve, fill='#2c3e50', outline='#1a252f')
draw4.arc([230, 80, 370, 140], 0, 180, fill='#1a252f', width=3)
draw4.text((300, 660), 'B&C E190 - Navy - 100% Baumwolle', fill='#666', font=get_font(16), anchor='mm')
img4.save('static/uploads/articles/SA-BCTM055.png')
thumb4 = img4.copy(); thumb4.thumbnail((200, 200))
thumb4.save('static/uploads/articles/thumbs/thumb_SA-BCTM055.png')
print('4. T-Shirt Artikelbild erstellt')

# ============================================================
# 5. WAPPEN-STICKEREI (Vereinswappen)
# ============================================================
img5 = Image.new('RGBA', (600, 700), (255, 255, 255, 0))
draw5 = ImageDraw.Draw(img5)
shield = [(100, 50), (500, 50), (500, 350), (300, 650), (100, 350)]
draw5.polygon(shield, fill='#1a3a5c', outline='#c9a84c')
shield_inner = [(120, 70), (480, 70), (480, 340), (300, 620), (120, 340)]
draw5.polygon(shield_inner, outline='#c9a84c', width=3)
draw5.line([120, 250, 480, 250], fill='#c9a84c', width=2)
draw5.text((300, 160), 'FC', fill='#c9a84c', font=get_font(72, True), anchor='mm')
draw5.text((300, 320), 'WUPPERTAL', fill='white', font=get_font(28, True), anchor='mm')
draw5.text((300, 370), 'UNITED', fill='#c9a84c', font=get_font(28, True), anchor='mm')
draw5.text((300, 450), '1954', fill='white', font=get_font(24), anchor='mm')
img5.save('static/uploads/designs/muster_wappen_stickerei.png')
thumb5 = img5.copy(); thumb5.thumbnail((200, 200))
thumb5.save('static/thumbnails/designs/muster_wappen_stickerei_thumb.png')
print('5. Wappen-Sticklogo erstellt')

print('\nAlle Muster-Designs erfolgreich erstellt!')
