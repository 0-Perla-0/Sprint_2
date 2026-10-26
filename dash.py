import json, numpy as np, pandas as pd, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
R=json.load(open('out/R.json')); A=R['A']; mm=pd.read_csv('out/mensual.csv')
CC=['#3BA55C','#F2C94C','#F2994A','#D64545','#7B3F98']; Y={2023:'#E08A1E',2024:'#1F4E79'}; NAVY='#1F4E79'
MES=['E','F','M','A','M','J','J','A','S','O','N','D']
plt.rcParams.update({'font.size':8,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.25})
fig=plt.figure(figsize=(7.6,6.2),facecolor='white')
gs=fig.add_gridspec(4,4,height_ratios=[.5,1.0,1.6,1.4],hspace=.6,wspace=.5,left=.05,right=.98,top=.98,bottom=.09)
ax=fig.add_subplot(gs[0,:]); ax.axis('off')
ax.add_patch(FancyBboxPatch((0,0),1,1,boxstyle='round,pad=0,rounding_size=.04',fc=NAVY,ec='none',transform=ax.transAxes))
ax.text(.015,.62,'Calidad del aire para transporte de pollos — Las Pintas (PIN)',color='white',fontsize=11.5,fontweight='bold',transform=ax.transAxes,va='center')
ax.text(.015,.22,'Índice AIRE Y SALUD (NOM-172-SEMARNAT-2023) · 2024 comparado con 2023 · Filtros: año, temporada, contaminante',color='#D7E3F1',fontsize=7.5,transform=ax.transAxes,va='center')
kp=[('Días Muy mala o peor',A['2024']['dias_muy_o_peor'],A['2023']['dias_muy_o_peor'],'días',False),
    ('Horas Extrem. mala',A['2024']['h_extrema'],A['2023']['h_extrema'],'horas',False),
    ('PM$_{10}$ promedio horario',A['2024']['pm10_prom'],A['2023']['pm10_prom'],'µg/m³',False),
    ('Días Buena o Aceptable',A['2024']['dias_cat'][0]+A['2024']['dias_cat'][1],A['2023']['dias_cat'][0]+A['2023']['dias_cat'][1],'días',True)]
for i,(t,a,b,u,good) in enumerate(kp):
    ax=fig.add_subplot(gs[1,i]); ax.axis('off')
    ax.add_patch(FancyBboxPatch((0,0),1,1,boxstyle='round,pad=0,rounding_size=.06',fc='#F2F7FB',ec='#C9D9EA',transform=ax.transAxes))
    ax.text(.08,.86,t,fontsize=7.2,color='#444',transform=ax.transAxes,va='center')
    ax.text(.08,.55,f'{a:g}',fontsize=20,fontweight='bold',color=NAVY,transform=ax.transAxes,va='center')
    ax.text(.08,.27,f'2023: {b:g}',fontsize=7.5,color='#555',transform=ax.transAxes,va='center')
    d=a-b; better=(d>0)==good if d!=0 else True
    ax.text(.92,.55,('▲' if d>0 else '▼')+f' {abs(d):.1f}'.rstrip('0').rstrip('.'),fontsize=9,fontweight='bold',color='#2E7D32' if better else '#C62828',ha='right',transform=ax.transAxes,va='center')
    ax.text(.92,.27,u,fontsize=6.5,color='#777',ha='right',transform=ax.transAxes,va='center')
ax=fig.add_subplot(gs[2,:2]); 
for y in (2023,2024):
    s=mm[mm.anio==y]; ax.plot(range(12),s.pm10,color=Y[y],marker='o',ms=3,label=str(y))
ax.set_xticks(range(12)); ax.set_xticklabels(MES); ax.set_title('PM$_{10}$ mensual (µg/m³)',fontsize=8.5,fontweight='bold',loc='left'); ax.legend(frameon=False,fontsize=7)
ax=fig.add_subplot(gs[2,2:]); 
bottom=np.zeros(12)
for k in range(5):
    v=np.array([r['mala'] for r in []]) if False else None
dd=pd.read_csv('out/diario_dow.csv',parse_dates=['fecha'])
for k in range(5):
    v=np.array([((dd.anio==2024)&(dd.mes==m)&(dd.k_global==k)).sum() for m in range(1,13)]); ax.bar(range(12),v,bottom=bottom,color=CC[k],width=.8); bottom+=v
ax.set_xticks(range(12)); ax.set_xticklabels(MES); ax.set_title('Días por categoría, 2024',fontsize=8.5,fontweight='bold',loc='left')
ax=fig.add_subplot(gs[3,:2]); sh=R['sh']
ax.plot(range(24),sh['seca_2024'],color=Y[2024],label='Seca 2024'); ax.plot(range(24),sh['seca_2023'],color=Y[2023],label='Seca 2023'); ax.plot(range(24),sh['lluvias_2024'],color=Y[2024],ls='--',label='Lluvias 2024')
ax.axvspan(12,17,color='#3BA55C',alpha=.12); ax.set_xticks([0,6,12,18,23]); ax.set_title('% de horas en Mala o peor, por hora',fontsize=8.5,fontweight='bold',loc='left'); ax.legend(frameon=False,fontsize=6.3,loc='lower center',ncol=3,bbox_to_anchor=(.5,-.5))
ax=fig.add_subplot(gs[3,2:]); ax.axis('off'); ax.set_title('Alertas y ventana operativa',fontsize=8.5,fontweight='bold',loc='left')
txt=['● Peores meses: dic–ene (PM$_{10}$ 157 y 126 µg/m³ en 2024)','● Episodios críticos: 19:00–11:00 h (100 % de las horas extremas)','● Menor frecuencia de Mala o peor: 12:00–17:00 h','● Jul–sep: temporada con más días Buena/Aceptable']
for i,t in enumerate(txt): ax.text(0,.82-i*.23,t,fontsize=7,transform=ax.transAxes,va='center',color='#222')
fig.savefig('out/fig_dashboard.png',dpi=200,facecolor='white')
