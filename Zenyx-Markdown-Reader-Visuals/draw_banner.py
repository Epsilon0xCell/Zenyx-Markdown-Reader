#!/usr/bin/env python3
"""Zenyx wordmark banner: exchange beach at first light, queue of crabs, name in Asar on a dune board."""
import math, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
random.seed(31)
HERE=__file__.rsplit('/',1)[0]
W,H=1200,420
BONE=(240,234,216); IND=(38,42,96); GOLD=(216,178,92); SILT=(128,124,112)
img=Image.new('RGB',(W,H),(240,232,210)); d=ImageDraw.Draw(img,'RGBA')
for y in range(0,120):
    t=y/120; d.line([(0,y),(W,y)],fill=(int(240-10*t),int(232-6*t),int(210+18*t)))
d.polygon([(0,118),(340,98),(700,112),(980,96),(1200,116),(1200,150),(0,150)],fill=(206,192,152))
for _ in range(60):
    x=random.uniform(0,W); y=random.uniform(100,128); d.line([(x,y),(x+random.uniform(-3,5),y-random.uniform(7,15))],fill=(120,128,84),width=2)
# sand
d.rectangle([0,150,W,H],fill=(226,208,168))
# rock pool at left with indigo reflection
d.polygon([(36,168),(300,160),(316,214),(52,224)],fill=(74,72,66))
d.ellipse([58,170,292,210],fill=(52,58,110)); d.ellipse([80,178,260,202],fill=(70,78,132))
for _ in range(2200):
    x,y=random.uniform(0,W),random.uniform(150,H); d.point((x,y),fill=random.choice([(214,194,150),(234,218,180)]))
# tracks trailing back to the pools
for i in range(30):
    t=i/30; x=330+t*560; y=356-t*66+math.sin(t*4)*10
    d.ellipse([x-3,y-2,x+3,y+2],fill=(150,130,96)); d.ellipse([x+8,y+5,x+14,y+9],fill=(150,130,96))
def shell(x,y,s,gold=False):
    for i in range(5):
        r=s*(1-i*0.17); cx=x-i*s*0.52; cy=y-i*s*0.10
        col=(238,230,208) if i%2==0 else (203,197,178)
        d.ellipse([cx-r,cy-r*0.86,cx+r,cy+r*0.86],fill=col,outline=(148,140,120))
        d.arc([cx-r,cy-r*0.86,cx+r,cy+r*0.86],300,60,fill=(165,157,138),width=max(2,int(s*0.13)))
    if gold: d.arc([x-s,y-s*0.86,x+s,y+s*0.86],290,80,fill=GOLD,width=max(3,int(s*0.18)))
    d.ellipse([x-s*0.24,y-s*0.3,x+s*0.24,y+s*0.3],fill=(100,90,76))
    d.polygon([(x-s*0.8,y+s*0.8),(x+s*1.3,y+s*0.86),(x+s*1.7,y+s*1.0),(x-s*0.6,y+s*0.94)],fill=(196,172,124,120))  # long thin shadow
def crab(x,y,s,pose=0):
    if pose==1: d.arc([x-16*s,y-12*s,x+18*s,y+16*s],180,360,fill=SILT,width=max(3,int(6*s)))
    else: d.ellipse([x-13*s,y-6*s,x+13*s,y+8*s],fill=SILT)
    for sx in (-1,1):
        d.arc([x+sx*11*s-9*s,y-12*s,x+sx*11*s+9*s,y+6*s],200 if sx<0 else 300,340 if sx<0 else 160,fill=(100,96,86),width=max(2,int(3.2*s)))
        for l in range(3):
            d.line([(x+sx*6*s,y+5*s),(x+sx*(15+l*3)*s,y+(10+l*3)*s)],fill=(100,96,86),width=max(2,int(2.4*s)))
    d.ellipse([x-2*s,y-10*s,x+3*s,y-5*s],fill=GOLD)
# queue sorted by size from pool toward open sand
for i in range(7):
    ss=0.55+i*0.13; x=370+i*104; y=252+math.sin(i*1.2)*8
    shell(x,y,30*ss,gold=(i==6)); crab(x-30*ss,y+17*ss,0.9*ss)
    if i<6: shell(x+54,y+30,17*ss)  # vacant shell kept in line
# exchange under way at right edge: crab darting into larger vacant shell
crab(1096,268,1.0,pose=1); shell(1152,246,34,gold=True)
# notice board at dune edge with the name in Asar
bx,by=742,26
d.rectangle([bx+18,by+54,bx+26,by+104],fill=(110,88,58)); d.rectangle([bx+330,by+54,bx+338,by+104],fill=(110,88,58))
d.rectangle([bx,by,bx+356,by+64],fill=(238,230,208),outline=(148,132,96),width=3)
f=ImageFont.truetype(HERE+'/fonts/Asar.ttf',34)
t='Zenyx-Markdown-Reader'
bb=d.textbbox((0,0),t,font=f)
d.text((bx+178-(bb[2]-bb[0])/2-bb[0],by+29-(bb[3]-bb[1])/2-bb[1]),t,font=f,fill=IND)
img=img.filter(ImageFilter.GaussianBlur(0.5))
img.save(HERE+'/banner.png')
print('saved')
