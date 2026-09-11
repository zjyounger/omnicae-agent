import json,math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Circle,Rectangle
ROOT=Path(__file__).resolve().parent
d=json.loads((ROOT/'design_parameters.json').read_text());R=d['radius_mm']
t=np.linspace(math.pi,0,100)
upper=np.column_stack((27*np.cos(t),43+27*np.sin(t))).tolist()
t=np.linspace(0,-math.pi,180)
lower=np.column_stack((R*np.cos(t),R*np.sin(t))).tolist()
outline=upper+[[27.5,0]]+lower+[[-27.5,0]]
fig,ax=plt.subplots(figsize=(10,9),facecolor='#f8fafc')
ax.set_facecolor('#f8fafc')
ax.add_patch(Polygon(outline,facecolor='#6d8897',edgecolor='#233847',linewidth=1.6))
ax.add_patch(Polygon([[0,0]]+lower,facecolor='#d69c36',edgecolor='none'))
ax.add_patch(Polygon(outline,fill=False,edgecolor='#233847',linewidth=1.6))
t=np.linspace(0,-math.pi,120)
old=upper+[[35,10],[46,-26]]+np.column_stack((46*np.cos(t),-26+46*np.sin(t))).tolist()+[[-35,10]]
ax.plot(*np.array(old+[old[0]]).T,color='#9b4759',ls='--',lw=1.3,label='Previous concept outline')
for z,r in [(0,27.5),(43,24)]:
    ax.add_patch(Circle((0,z),r,fill=False,edgecolor='#233847',ls=':',linewidth=1.2))
    ax.plot([-4,4],[z,z],color='#233847',lw=.8);ax.plot([0,0],[z-4,z+4],color='#233847',lw=.8)
ax.annotate('',xy=(0,0),xytext=(-R/math.sqrt(2),-R/math.sqrt(2)),arrowprops=dict(arrowstyle='<->',color='#182f40',lw=1.2))
ax.text(-43,-25,f'R {R:.2f}',rotation=45,ha='center',fontsize=12,color='#182f40',weight='bold')
ax.annotate('',xy=(87,0),xytext=(87,43),arrowprops=dict(arrowstyle='<->',color='#233847'))
ax.plot([29,90],[43,43],color='#597481',lw=.7);ax.plot([R,90],[0,0],color='#597481',lw=.7)
ax.text(91,21.5,'43 mm throw',rotation=90,va='center',fontsize=11)
ax.annotate('',xy=(-R,-83),xytext=(R,-83),arrowprops=dict(arrowstyle='<->',color='#233847'))
for x in (-R,R):ax.plot([x,x],[-3,-86],lw=.7,color='#597481')
ax.text(0,-91,f'{2*R:.2f} mm lower contour width',ha='center',fontsize=11)
ax.text(-95,88,'EIGHT COUNTERWEIGHTS',fontsize=18,weight='bold',color='#182f40')
ax.text(-95,80,'One web shown in its local Y–Z plane  /  dimensions in mm',fontsize=10,color='#526878')
ax.text(-95,-105,'42CrMo4 +QT  •  7,800 kg/m³  •  web thickness 20 mm',fontsize=11,color='#182f40')
ax.text(-95,-113,'Gold = lower counterweight region; dotted circles = journal references.',fontsize=9,color='#526878')
ax.text(-95,-120,'Mass-moment design only. Fillets, oil drillings and fatigue remain to be developed.',fontsize=9,color='#526878')
ax.legend(loc='upper right',bbox_to_anchor=(.97,.95),frameon=False,fontsize=9,labelcolor='#526878')
ax.set_xlim(-100,110);ax.set_ylim(-126,97);ax.set_aspect('equal');ax.axis('off')
fig.tight_layout()
fig.savefig(ROOT/'counterweight_profile.png',dpi=180)
fig.savefig(ROOT/'counterweight_profile.svg')
