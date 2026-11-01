#!/usr/bin/env python3
"""Zenyx intro banner: hermit crab vacancy chain beach at dawn, scenery only, no text."""
import math, random
from PIL import Image, ImageDraw, ImageFilter
random.seed(53)
W,H=1200,520
BONE=(240,234,216); IND=(38,42,96); GOLD=(216,178,92); SILT=(128,124,112)
img=Image.new('RGB',(W,H),(238,230,208)); d=ImageDraw.Draw(img,'RGBA')
# sky top third, dawn pale
for y in range(0,170):
    t=y/170; d.line([(0,y),(W,y)],fill=(int(238-14*t),int(230-10*t),int(208+16*t)))
# dune ridge with sparse grass
d.polygon([(0,168),(300,146),(640,160),(940,142),(1200,164),(1200,196),(0,196)],fill=(206,192,152))
for _ in range(90):
    x=random.uniform(0,W); y=random.uniform(148,172); d.line([(x,y),(x+random.uniform(-4,6),y-random.uniform(8,18))],fill=(120,128,84),width=2)
# rock pools in steps
for (x,y,w,h) in [(60,196,300,44),(420,208,340,40),(820,198,320,46)]:
    d.polygon([(x,y+6),(x+40,y),(x+w-30,y+3),(x+w,y+12),(x+w-16,y+h),(x+50,y+h-4),(x+8,y+h-10)],fill=(74,72,66))
    d.ellipse([x+14,y+6,x+w-16,y+h-6],fill=(52,58,110))
    d.ellipse([x+30,y+12,x+w-60,y+h-14],fill=(70,78,132))
# wet sand foreground
d.rectangle([0,246,W,H],fill=(226,208,168))
for _ in range(3200):
    x,y=random.uniform(0,W),random.uniform(246,H); d.point((x,y),fill=random.choice([(214,194,150),(234,218,180),(200,180,134)]))
for _ in range(120):  # shell fragments
    x,y=random.uniform(0,W),random.uniform(400,512); d.point((x,y),fill=(246,242,230)); d.point((x+2,y+1),fill=(210,200,170))
# tide line sheet of water mirroring crabs in broken indigo
d.polygon([(0,300),(1200,286),(1200,318),(0,336)],fill=(86,96,150,170))
# crab tracks entering lower left, curving out
for i in range(26):
    t=i/26; x=30+t*430; y=492-t*120+math.sin(t*5)*16
    d.ellipse([x-3,y-2,x+3,y+2],fill=(150,130,96)); d.ellipse([x+8,y+5,x+14,y+9],fill=(150,130,96))
# spiral shell drawer
def shell(x,y,s,band=True,gold=False):
    for i in range(5):
        r=s*(1-i*0.17); cx=x-i*s*0.52; cy=y-i*s*0.10
        col=(238,230,208) if i%2==0 else (206,200,182)
        d.ellipse([cx-r,cy-r*0.86,cx+r,cy+r*0.86],fill=col,outline=(150,142,124))
        if band: d.arc([cx-r,cy-r*0.86,cx+r,cy+r*0.86],300,60,fill=(168,160,142),width=max(2,int(s*0.14)))
    if gold: d.arc([x-s,y-s*0.86,x+s,y+s*0.86],290,80,fill=GOLD,width=max(3,int(s*0.2)))
    d.ellipse([x-s*0.24,y-s*0.3,x+s*0.24,y+s*0.3],fill=(104,94,80))  # opening shadow
def crab(x,y,s):
    d.ellipse([x-12*s,y-6*s,x+12*s,y+7*s],fill=SILT)
    for sx in (-1,1):
        d.arc([x+sx*10*s-8*s,y-10*s,x+sx*10*s+8*s,y+6*s],200 if sx<0 else 300,340 if sx<0 else 160,fill=(104,100,90),width=max(2,int(3*s)))
        for l in range(3):
            d.line([(x+sx*6*s,y+4*s),(x+sx*(14+l*3)*s,y+(9+l*3)*s)],fill=(104,100,90),width=max(2,int(2.4*s)))
    d.ellipse([x-3*s,y-9*s,x+1*s,y-5*s],fill=GOLD); d.ellipse([x+3*s,y-9*s,x+7*s,y-5*s],fill=GOLD)
# queue at rest along tide edge: crabs in shells of graded size
sizes=[0.62,0.7,0.78,0.86,0.94,1.02,1.1,1.18,1.26]
for i,ss in enumerate(sizes):
    x=110+i*104; y=330+math.sin(i*1.3)*7
    shell(x,y,26*ss,band=True,gold=(i==len(sizes)-1))
    crab(x-26*ss,y+16*ss,0.95*ss)
    # broken indigo reflection
    d.ellipse([x-24*ss,y+34*ss,x+24*ss,y+40*ss],fill=(70,78,132,110))
# foreground empty spiral shell, larger than anything near it, lower right
shell(1052,448,58,band=True,gold=True)
d.ellipse([1028,432,1076,466],fill=(88,78,66))
img=img.filter(ImageFilter.GaussianBlur(0.5))
img.save(__file__.rsplit('/',1)[0]+'/intro-banner.png')
print('saved')
