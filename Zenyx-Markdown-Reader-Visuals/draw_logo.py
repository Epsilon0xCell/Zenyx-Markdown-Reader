#!/usr/bin/env python3
"""Zenyx logo: vacancy chain of three crabs and three shells in a line, Asar wordmark."""
from PIL import Image, ImageDraw, ImageFont
HERE=__file__.rsplit('/',1)[0]
W,H=900,520
BONE=(240,234,216); IND=(38,42,96); GOLD=(216,178,92); SILT=(128,124,112)
img=Image.new('RGB',(W,H),BONE); d=ImageDraw.Draw(img)
def shell(x,y,s,gold=False):
    for i in range(5):
        r=s*(1-i*0.17); cx=x-i*s*0.52; cy=y-i*s*0.10
        col=(238,230,208) if i%2==0 else (203,197,178)
        d.ellipse([cx-r,cy-r*0.86,cx+r,cy+r*0.86],fill=col,outline=(148,140,120),width=2)
        d.arc([cx-r,cy-r*0.86,cx+r,cy+r*0.86],300,60,fill=(165,157,138),width=max(2,int(s*0.13)))
    if gold: d.arc([x-s,y-s*0.86,x+s,y+s*0.86],290,80,fill=GOLD,width=max(3,int(s*0.18)))
    d.ellipse([x-s*0.24,y-s*0.3,x+s*0.24,y+s*0.3],fill=(100,90,76))
def crab(x,y,s,pose=0):
    if pose==1:  # mid move, soft body curved
        d.arc([x-16*s,y-12*s,x+18*s,y+16*s],180,360,fill=SILT,width=max(3,int(6*s)))
    else:
        d.ellipse([x-13*s,y-6*s,x+13*s,y+8*s],fill=SILT)
    for sx in (-1,1):
        d.arc([x+sx*11*s-9*s,y-12*s,x+sx*11*s+9*s,y+6*s],200 if sx<0 else 300,340 if sx<0 else 160,fill=(100,96,86),width=max(2,int(3.4*s)))
        for l in range(3):
            d.line([(x+sx*6*s,y+5*s),(x+sx*(15+l*3)*s,y+(10+l*3)*s)],fill=(100,96,86),width=max(2,int(2.6*s)))
    d.ellipse([x-2*s,y-10*s,x+3*s,y-5*s],fill=GOLD)
# wet sand line
d.rectangle([0,330,W,336],fill=(196,178,138))
# left: large crab half out of tall spiral, testing empty shell beside it
shell(140,205,58,gold=True); crab(232,258,1.3)
shell(330,228,46)
# middle: smaller crab mid move between old shell and larger one
shell(452,242,36); crab(528,252,1.05,pose=1); shell(622,232,46)
# right: small empty shell waiting alone, opening toward viewer
shell(762,242,34)
d.ellipse([748,228,776,256],fill=(88,78,66))
f=ImageFont.truetype(HERE+'/fonts/Asar.ttf',46)
t='Zenyx-Markdown-Reader'
bb=d.textbbox((0,0),t,font=f)
d.text(((W-(bb[2]-bb[0]))/2-bb[0],404),t,font=f,fill=IND)
img.save(HERE+'/logo.png')
img.resize((64,64)).save(HERE+'/scratch/logo64-ship.png')
print('saved')
