import pickle,os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from imgdec import decode_entry
from PIL import Image, ImageDraw, ImageFont
HERE=os.path.dirname(os.path.abspath(__file__))
rows=[]
for line in open(os.path.join(HERE,'rows.tsv'),encoding='utf-8').readlines()[1:]:
    f=line.rstrip('\n').split('\t')
    if len(f)<14: continue
    if f[0]!='856DDBAC': continue
    if f[1] not in ('1ABE787D','46A006B0','00000001'): continue
    if 'Plugins' in f[13]: continue
    t=float(f[9])
    if t<0.45: continue
    rows.append((t,int(f[1],16),int(f[2],16),int(f[4]),int(f[5])))
rows.sort(key=lambda r:-r[0])
seen=set(); pick=[]
for r in rows:
    if r[2] in seen: continue
    seen.add(r[2]); pick.append(r)
    if len(pick)>=48: break
print('distinct Maxis-UI PNG tint candidates:',len(seen),'rendering',len(pick))
d=pickle.load(open(os.path.join(HERE,'image-index.pkl'),'rb'))
off={}
for (t,g,i,p,o,s) in d['entries']: off.setdefault((t,g,i),(p,o,s))
fnt=ImageFont.truetype(r'C:\Windows\Fonts\consola.ttf',12)
CW,CH=300,196
cols=4; rws=(len(pick)+cols-1)//cols
sh=Image.new('RGB',(CW*cols,CH*rws),(16,16,20)); dr=ImageDraw.Draw(sh)
for n,(sc,g,i,w,h) in enumerate(pick):
    p,o,s=off[(0x856DDBAC,g,i)]
    fh=open(p,'rb'); fh.seek(o); raw=fh.read(s); fh.close()
    imgs,_=decode_entry(0x856DDBAC,raw)
    if not imgs: continue
    im=Image.fromarray(imgs[0],'RGBA')
    k=max(1,min(6,(CW-12)//max(1,im.width), (CH-30)//max(1,im.height)))
    if k>1: im=im.resize((im.width*k,im.height*k),Image.NEAREST)
    if im.width>CW-12 or im.height>CH-30:
        im.thumbnail((CW-12,CH-30),Image.NEAREST)
    cx=(n%cols)*CW; cy=(n//cols)*CH
    ox=cx+(CW-im.width)//2; oy=cy+6+((CH-30)-im.height)//2
    for yy in range(0,im.height,8):
        for xx in range(0,im.width,8):
            if ((xx//8)+(yy//8))%2==0: dr.rectangle([ox+xx,oy+yy,ox+xx+7,oy+yy+7],fill=(54,54,62))
    sh.paste(im,(ox,oy),im)
    dr.rectangle([cx,cy,cx+CW-1,cy+CH-1],outline=(70,70,84))
    dr.text((cx+5,cy+CH-18),'%08X G%08X %dx%d s=%.2f'%(i,g,w,h,sc),font=fnt,fill=(235,235,245))
sh.save(os.path.join(HERE,'lane-colour-tint-maxis-ui.png'))
print('wrote lane-colour-tint-maxis-ui.png',sh.size)
