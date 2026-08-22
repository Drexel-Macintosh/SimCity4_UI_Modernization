import pickle,os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from imgdec import decode_entry
from PIL import Image, ImageDraw, ImageFont
HERE=os.path.dirname(os.path.abspath(__file__))
d=pickle.load(open(os.path.join(HERE,'image-index.pkl'),'rb'))
want=sorted(set([0x14315E00,0x14315E10,0x14315E20,0x14315E30,0x14315E40,0x14315E50,0x14315E51,
      0x14315E60,0x14315E61,0x14315E62,0xEA3EE100,0xEA3EE110,0xEA3EE120,0xEA3EE130,
      0xEA3EE140,0xEA3EE150,0x144161E9,0x14416316,0x11270003,0x144162AE]))
fnt=ImageFont.truetype(r'C:\Windows\Fonts\consola.ttf',13)
seen=set(); tiles=[]
for (t,g,i,p,off,sz) in d['entries']:
    if i not in want: continue
    if 'Plugins' in p: continue
    k=(t,g,i)
    if k in seen: continue
    seen.add(k)
    fh=open(p,'rb'); fh.seek(off); raw=fh.read(sz); fh.close()
    imgs,f=decode_entry(t,raw)
    if not imgs: continue
    im=Image.fromarray(imgs[0],'RGBA')
    lab='%08X T%04X %dx%d'%(i,t&0xFFFF,im.width,im.height)
    k2=max(1,min(4,192//max(im.size)))
    if k2>1: im=im.resize((im.width*k2,im.height*k2),Image.NEAREST)
    if max(im.size)>256:
        im.thumbnail((256,256),Image.NEAREST)
    tiles.append((i,lab,im))
tiles.sort(key=lambda x:x[0])
CW,CH=268,290
cols=6; rws=(len(tiles)+cols-1)//cols
sh=Image.new('RGB',(CW*cols,CH*rws),(16,16,20)); dr=ImageDraw.Draw(sh)
for n,(i,lab,im) in enumerate(tiles):
    cx=(n%cols)*CW; cy=(n//cols)*CH
    ox=cx+(CW-im.width)//2; oy=cy+8+(256-im.height)//2
    for yy in range(0,im.height,10):
        for xx in range(0,im.width,10):
            if ((xx//10)+(yy//10))%2==0: dr.rectangle([ox+xx,oy+yy,ox+xx+9,oy+yy+9],fill=(52,52,60))
    sh.paste(im,(ox,oy),im)
    dr.rectangle([cx,cy,cx+CW-1,cy+CH-1],outline=(70,70,84))
    dr.text((cx+5,cy+CH-20),lab,font=fnt,fill=(235,235,245))
sh.save(os.path.join(HERE,'lane-colour-marker-family.png'))
print('wrote lane-colour-marker-family.png',sh.size,len(tiles),'tiles')
