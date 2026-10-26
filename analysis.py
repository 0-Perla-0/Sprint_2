import json, numpy as np, pandas as pd
from scipy import stats
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
import pipeline as P

import sys, os
os.makedirs('out', exist_ok=True)
raw = P.cargar(sys.argv[1:3]); h = P.horario(raw); dd = P.diario(h)
h.to_csv('out/horario.csv', index=False); dd.to_csv('out/diario.csv', index=False)
raw['anio']=raw.DATE.dt.year; raw['mes']=raw.DATE.dt.month
R = {}
CC = ['#3BA55C','#F2C94C','#F2994A','#D64545','#7B3F98']; CN = P.CATS
Y = {2023:'#E08A1E', 2024:'#1F4E79'}
MES = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.25,'figure.dpi':100})
def save(fig,n): fig.savefig(f'out/{n}.png',dpi=200,bbox_inches='tight',facecolor='white'); plt.close(fig)

# ---------- A. Inventario y cobertura ----------
meta = [('O3','O$_3$','ppm'),('PM10','PM$_{10}$','µg/m³'),('PM2.5','PM$_{2.5}$','µg/m³'),('ET','Temperatura externa (ET)','°C'),
        ('RH','Humedad relativa (RH)','%'),('WS','Velocidad del viento (WS)','m/s'),('WD','Dirección del viento (WD)','°'),
        ('CO','CO','ppm'),('NO2','NO$_2$','ppm'),('SO2','SO$_2$','ppm'),('PP','Precipitación (PP)','mm'),('IT','Temperatura interna (IT)','°C'),('ATM','Presión atmosférica (ATM)','mmHg'),('RS','Radiación solar (RS)','W/m²')]
inv=[]
for c,n,u in meta:
    row={'var':c,'nombre':n,'unidad':u}
    for y in (2023,2024):
        s=raw[raw.anio==y][c]; row[f'n{y}']=int(s.count()); row[f'pct{y}']=round(100*s.count()/len(raw[raw.anio==y]),1)
        row[f'min{y}']=None if s.count()==0 else float(s.min()); row[f'max{y}']=None if s.count()==0 else float(s.max())
    inv.append(row)
R['inv']=inv
# Viento 2024 oct-dic: mediana 0.05 m/s y 100 % de los valores < 1 m/s -> posible falla del sensor; se excluye del analisis meteorologico
mk=(raw.anio==2024)&(raw.mes>=10); R['ws_masked']=int(raw.loc[mk,'WS'].notna().sum()); R['ws_masked_med']=float(raw.loc[mk,'WS'].median())
raw.loc[mk,'WS']=np.nan; h.loc[(h.anio==2024)&(h.mes>=10),'WS']=np.nan
R['horas']={2023:int((raw.anio==2023).sum()),2024:int((raw.anio==2024).sum())}
R['dup']=int(raw.DATE.duplicated().sum()); R['gaps']=int((raw.DATE.diff().dropna()!=pd.Timedelta('1h')).sum())
cov = {c: (raw.pivot_table(index='anio',columns='mes',values=c,aggfunc='count').div(raw.pivot_table(index='anio',columns='mes',values='HOUR',aggfunc='count'))*100) for c in ['PM10','PM2.5','O3','ET','RH','WS']}
R['cov']={c:{int(y):[round(v,1) for v in cov[c].loc[y]] for y in (2023,2024)} for c in cov}
# calidad
q={}
q['pm25_gt_pm10']=int((raw['PM2.5']>raw.PM10).sum()); q['rh_gt100']=int((raw.RH>100).sum()); q['pm10_le2']=int((raw.PM10<=2).sum())
iqr=raw.PM10.quantile(.75)-raw.PM10.quantile(.25); lim=raw.PM10.quantile(.75)+3*iqr; q['pm10_ext_lim']=float(lim); q['pm10_ext_n']=int((raw.PM10>lim).sum())
ex=raw[raw.PM10>lim]; q['pm10_ext_hours']=ex.DATE.dt.hour.value_counts().sort_index().to_dict(); q['pm10_ext_nocturnas']=int(((ex.DATE.dt.hour>=19)|(ex.DATE.dt.hour<=11)).sum())
q['pm10_ext_mes']=ex.mes.value_counts().sort_index().to_dict()
# valores repetidos (posible sensor atascado) >=12 h iguales
def maxrun(s):
    m=0;c=0;prev=None
    for v in s:
        if pd.notna(v) and v==prev: c+=1
        else: c=1
        prev=v if pd.notna(v) else None; m=max(m,c)
    return m
q['maxrun']={c:{y:maxrun(raw[raw.anio==y][c]) for y in (2023,2024)} for c in ['PM10','PM2.5','O3','ET','RH','WS']}
c8=raw.CO.rolling(8,min_periods=6).mean(); q['co8_max']=float(c8.max()); q['co_max']=float(raw.CO.max())
R['q']=q

# fig 1: cobertura
fig,axs=plt.subplots(1,2,figsize=(7.4,2.9),sharey=True)
vs=['PM10','PM2.5','O3','ET','RH','WS']; lab=['PM$_{10}$','PM$_{2.5}$','O$_3$','Temp.','Hum. rel.','Viento*']
for ax,y in zip(axs,(2023,2024)):
    M=np.array([cov[v].loc[y].values for v in vs])
    im=ax.imshow(M,cmap='Blues',vmin=0,vmax=100,aspect='auto'); ax.set_xticks(range(12)); ax.set_xticklabels(MES,rotation=60,fontsize=7.5)
    ax.set_yticks(range(6)); ax.set_yticklabels(lab); ax.set_title(str(y),fontsize=10,fontweight='bold'); ax.grid(False)
    for i in range(6):
        for j in range(12): ax.text(j,i,f'{M[i,j]:.0f}',ha='center',va='center',fontsize=6.5,color='white' if M[i,j]>55 else '#222')
cb=fig.colorbar(im,ax=axs,fraction=.02,pad=.02); cb.set_label('% de horas con dato',fontsize=8)
save(fig,'fig_cobertura')

# ---------- B. Resumen anual ----------
A={}
for y in (2023,2024):
    hy=h[h.anio==y]; dy=dd[dd.anio==y]
    A[y]={'horas_cat':[int((hy.k_global==k).sum()) for k in range(5)],'horas_val':int(hy.k_global.notna().sum()),
      'dias_cat':[int((dy.k_global==k).sum()) for k in range(5)],'dias_nd':int(dy.k_global.isna().sum()),'dias':len(dy),
      'pm10_prom':round(hy.PM10.mean(),1),'pm25_prom':round(hy['PM2.5'].mean(),1),'o3_prom':round(hy.O3.mean(),4),
      'pm10_max':float(hy.PM10.max()),'pm25_max':float(hy['PM2.5'].max()),'o3_max':float(hy.O3.max()),
      'nc10_max':float(hy.NC_PM10.max()),'nc25_max':float(hy['NC_PM2.5'].max()),
      'pm10_med':float(hy.PM10.median()),'pm25_med':float(hy['PM2.5'].median()),
      'pm10_dia_prom':round(dy.ind_PM10.mean(),1),'pm25_dia_prom':round(dy['ind_PM2.5'].mean(),1),
      'dias_pm25_suf':int(dy['ind_PM2.5'].notna().sum()),'dias_pm10_suf':int(dy.ind_PM10.notna().sum()),'dias_o3_suf':int(dy.ind_O3.notna().sum()),
      'dom':dy.dominante.value_counts().to_dict(),
      'dias_mala_o_peor':int((dy.k_global>=2).sum()),'dias_muy_o_peor':int((dy.k_global>=3).sum()),
      'h_mala_o_peor':int((hy.k_global>=2).sum()),'h_muy_o_peor':int((hy.k_global>=3).sum()),'h_extrema':int((hy.k_global==4).sum())}
    # dominancia
    for p in ('PM10','PM2.5','O3'):
        A[y]['dom_'+p]=int(dy.dominante.fillna('').str.contains(p,regex=False).sum())
    A[y]['solo_pm10']=int((dy.dominante=='PM10').sum()); A[y]['solo_pm25']=int((dy.dominante=='PM2.5').sum()); A[y]['solo_o3']=int((dy.dominante=='O3').sum())
R['A']=A

# fig 2: categoria horaria y diaria por año (100 % apiladas)
fig,axs=plt.subplots(1,2,figsize=(7.2,2.6))
for ax,(ttl,key,tot) in zip(axs,[('Categoría horaria global','horas_cat','horas_val'),('Categoría diaria global','dias_cat',None)]):
    for i,y in enumerate((2023,2024)):
        v=np.array(A[y][key],float); v=100*v/v.sum(); left=0
        for k in range(5):
            ax.barh(i,v[k],left=left,color=CC[k],edgecolor='white',label=CN[k] if i==0 else None)
            if v[k]>=6: ax.text(left+v[k]/2,i,f'{v[k]:.0f}%',ha='center',va='center',fontsize=7.5,color='white' if k in(0,3,4) else '#222')
            left+=v[k]
    ax.set_yticks([0,1]); ax.set_yticklabels(['2023','2024']); ax.invert_yaxis(); ax.set_xlim(0,100); ax.set_title(ttl,fontsize=9.5,fontweight='bold'); ax.set_xlabel('% de horas' if tot else '% de días'); ax.grid(False)
axs[0].legend(ncol=5,loc='upper center',bbox_to_anchor=(1.1,-0.28),fontsize=7.5,frameon=False,columnspacing=1)
save(fig,'fig_categorias')

# ---------- C. Mensual ----------
mm=[]
for y in (2023,2024):
    for m in range(1,13):
        dy=dd[(dd.anio==y)&(dd.mes==m)]; hy=h[(h.anio==y)&(h.mes==m)]
        mm.append({'anio':y,'mes':m,'pm10':round(dy.ind_PM10.mean(),1),'pm25':None if dy['ind_PM2.5'].count()==0 else round(dy['ind_PM2.5'].mean(),1),'npm25':int(dy['ind_PM2.5'].count()),
          'o3':round(dy.ind_O3.mean(),3),'mala':int((dy.k_global>=2).sum()),'muy':int((dy.k_global>=3).sum()),'hx':int((hy.k_global==4).sum()),'dias':len(dy),
          'pm10_hor':round(hy.PM10.mean(),1),'nc10_max':float(hy.NC_PM10.max()),'cov25':float(cov['PM2.5'].loc[y,m]),
          'buena_h':round(100*(hy.k_global==0).sum()/max(1,hy.k_global.notna().sum()),1)})
mm=pd.DataFrame(mm); R['mm']=mm.to_dict('records')
fig,axs=plt.subplots(1,2,figsize=(7.4,2.9))
for y in (2023,2024):
    s=mm[mm.anio==y]
    axs[0].plot(range(12),s.pm10,marker='o',ms=3.5,color=Y[y],label=str(y))
    ok=s.npm25>=15
    axs[1].plot(np.array(range(12))[ok],s.pm25[ok],marker='o',ms=3.5,color=Y[y],label=str(y))
axs[0].set_title('PM$_{10}$: promedio mensual de los promedios diarios',fontsize=8.5,fontweight='bold'); axs[1].set_title('PM$_{2.5}$ (meses con ≥15 días suficientes)',fontsize=8.5,fontweight='bold')
for ax in axs: ax.set_xticks(range(12)); ax.set_xticklabels(MES,rotation=60,fontsize=7.5); ax.set_ylabel('µg/m³'); ax.legend(frameon=False)
save(fig,'fig_mensual')
# fig 4: dias por categoria por mes
fig,axs=plt.subplots(1,2,figsize=(7.4,2.8),sharey=True)
for ax,y in zip(axs,(2023,2024)):
    bottom=np.zeros(12)
    for k in range(5):
        v=np.array([((dd.anio==y)&(dd.mes==m)&(dd.k_global==k)).sum() for m in range(1,13)])
        ax.bar(range(12),v,bottom=bottom,color=CC[k],label=CN[k],width=.8); bottom+=v
    nd=np.array([((dd.anio==y)&(dd.mes==m)&(dd.k_global.isna())).sum() for m in range(1,13)])
    ax.bar(range(12),nd,bottom=bottom,color='#BDBDBD',label='Sin dato suficiente',width=.8)
    ax.set_xticks(range(12)); ax.set_xticklabels(MES,rotation=60,fontsize=7.5); ax.set_title(str(y),fontsize=9.5,fontweight='bold'); ax.set_ylim(0,31)
axs[0].set_ylabel('Días')
h_,l_=axs[0].get_legend_handles_labels(); fig.legend(h_,l_,ncol=6,loc='lower center',bbox_to_anchor=(.5,-0.1),fontsize=7,frameon=False,columnspacing=.8)
save(fig,'fig_dias_mes')
# fig 5: calendario diario
fig,axs=plt.subplots(2,1,figsize=(7.4,4.6))
cmap=ListedColormap(CC); norm=BoundaryNorm([-.5,.5,1.5,2.5,3.5,4.5],5)
for ax,y in zip(axs,(2023,2024)):
    M=np.full((12,31),np.nan)
    for _,r in dd[dd.anio==y].iterrows(): M[r.mes-1,r.fecha.day-1]=r.k_global
    ax.imshow(np.ma.masked_invalid(M),cmap=cmap,norm=norm,aspect='auto'); ax.set_yticks(range(12)); ax.set_yticklabels(MES,fontsize=7)
    ax.set_xticks(range(0,31,2)); ax.set_xticklabels(range(1,32,2),fontsize=7); ax.set_title(str(y),fontsize=9.5,fontweight='bold',loc='left'); ax.grid(False)
    ax.set_xticks(np.arange(-.5,31,1),minor=True); ax.set_yticks(np.arange(-.5,12,1),minor=True); ax.grid(which='minor',color='white',lw=.8); ax.tick_params(which='minor',length=0)
axs[1].set_xlabel('Día del mes'); fig.subplots_adjust(hspace=.45); axs[0].set_xticklabels([])
from matplotlib.patches import Patch
fig.legend([Patch(color=c) for c in CC]+[Patch(color='#F2F2F2',ec='#999')],CN+['Sin dato suficiente'],ncol=6,loc='lower center',bbox_to_anchor=(.5,-0.04),fontsize=7,frameon=False,columnspacing=.8)
save(fig,'fig_calendario')

# ---------- D. Perfil horario ----------
hp={}
fig,axs=plt.subplots(1,3,figsize=(7.4,2.5)); fig.subplots_adjust(wspace=.45)
for ax,(c,t,u) in zip(axs,[('PM10','PM$_{10}$','µg/m³'),('PM2.5','PM$_{2.5}$','µg/m³'),('O3','O$_3$','ppm')]):
    for y in (2023,2024):
        s=h[h.anio==y].groupby('hora')[c].mean(); hp[f'{c}_{y}']=[round(v,3) for v in s]; ax.plot(s.index,s.values,color=Y[y],label=str(y),lw=1.8)
    ax.set_title(t,fontsize=9,fontweight='bold'); ax.set_xlabel('Hora'); ax.set_ylabel(u); ax.set_xticks([0,6,12,18,23])
axs[0].legend(frameon=False,fontsize=8)
save(fig,'fig_perfil'); R['hp']=hp
# share hours >= Mala by hour & season
h['temp']=np.where(h.mes.between(6,10),'lluvias','seca')
sh={}
for t in ('seca','lluvias'):
    for y in (2023,2024):
        g=h[(h.temp==t)&(h.anio==y)&h.k_global.notna()]; sh[f'{t}_{y}']=[round(100*(g[g.hora==k].k_global>=2).mean(),1) for k in range(24)]
        sh[f'{t}_{y}_muy']=[round(100*(g[g.hora==k].k_global>=3).mean(),1) for k in range(24)]
R['sh']=sh
fig,axs=plt.subplots(1,2,figsize=(7.4,2.6),sharey=True)
for ax,t,tt in zip(axs,('seca','lluvias'),('Temporada seca (nov–may)','Temporada de lluvias (jun–oct)')):
    for y in (2023,2024): ax.plot(range(24),sh[f'{t}_{y}'],color=Y[y],label=str(y),lw=1.8)
    ax.set_title(tt,fontsize=9,fontweight='bold'); ax.set_xlabel('Hora del día'); ax.set_xticks([0,3,6,9,12,15,18,21,23])
axs[0].set_ylabel('% de horas en Mala o peor'); axs[0].legend(frameon=False)
save(fig,'fig_horas_riesgo')

# ---------- E. Episodios ----------
def runs(h,thr):
    k=(h.k_global>=thr).values; out=[]; i=0
    while i<len(h):
        if k[i]:
            j=i
            while j+1<len(h) and k[j+1]: j+=1
            g=h.iloc[i:j+1]; out.append({'ini':str(g.DATE.iloc[0]),'fin':str(g.DATE.iloc[-1]),'horas':j-i+1,'nc10':float(g.NC_PM10.max()),'nc25':None if g['NC_PM2.5'].notna().sum()==0 else float(g['NC_PM2.5'].max()),'pm10':float(g.PM10.max()),'pm25':None if g['PM2.5'].notna().sum()==0 else float(g['PM2.5'].max())}); i=j+1
        else: i+=1
    return pd.DataFrame(out)
r4=runs(h,4); r3=runs(h,3)
r4['anio']=pd.to_datetime(r4.ini).dt.year; r3['anio']=pd.to_datetime(r3.ini).dt.year
R['ep4']={int(y):{'n':int(len(g)),'horas':int(g.horas.sum()),'max':int(g.horas.max())} for y,g in r4.groupby('anio')}
R['ep3']={int(y):{'n':int(len(g)),'horas':int(g.horas.sum()),'max':int(g.horas.max())} for y,g in r3.groupby('anio')}
R['top_ep']=r4.sort_values(['horas','nc10'],ascending=False).head(8).to_dict('records')
x4=h[h.k_global==4]; R['ex_hora']={int(y):x4[x4.anio==y].hora.value_counts().sort_index().to_dict() for y in (2023,2024)}
R['ex_nocturna']={int(y):int(((x4[x4.anio==y].hora>=19)|(x4[x4.anio==y].hora<=11)).sum()) for y in (2023,2024)}
R['ex_mes']={int(y):x4[x4.anio==y].mes.value_counts().sort_index().to_dict() for y in (2023,2024)}
R['ex_dias']=x4.groupby('fecha').size().sort_values(ascending=False).head(8).rename(lambda d:str(d.date())).to_dict()
# fig episodios: NC PM10 diario max por dia (2 paneles)
fig,axs=plt.subplots(2,1,figsize=(7.4,4.2),sharey=True)
for ax,y in zip(axs,(2023,2024)):
    s=dd[dd.anio==y]; ax.fill_between(s.fecha,s['max_NC_PM10'],color=Y[y],alpha=.25); ax.plot(s.fecha,s['max_NC_PM10'],color=Y[y],lw=.8,label='PM$_{10}$ (NowCast)')
    ax.plot(s.fecha,s['max_NC_PM2.5'],color='#555',lw=.7,alpha=.8,label='PM$_{2.5}$ (NowCast)')
    for v,c,l in [(213,CC[4],'>213 Extremadamente mala (PM$_{10}$)'),(132,CC[3],'>132 Muy mala (PM$_{10}$)')]: ax.axhline(v,color=c,ls='--',lw=.9,label=l)
    ax.set_title(f'{y}',fontsize=9.5,fontweight='bold',loc='left'); ax.set_ylabel('Máx. NowCast diario (µg/m³)',fontsize=7.5)
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%b')); ax.xaxis.set_major_locator(matplotlib.dates.MonthLocator())
axs[0].legend(frameon=False,fontsize=6.5,ncol=2,loc='upper right'); fig.subplots_adjust(hspace=.4); axs[0].set_xticklabels([])
save(fig,'fig_episodios')

# ---------- F. Meteorologia ----------
d=h.groupby('fecha').agg(pm10=('PM10','mean'),npm10=('PM10','count'),pm25=('PM2.5','mean'),npm25=('PM2.5','count'),et=('ET','mean'),net=('ET','count'),rh=('RH','mean'),nrh=('RH','count'),ws=('WS','mean'),nws=('WS','count'),pp=('PP','sum'),npp=('PP','count')).reset_index()
d['anio']=d.fecha.dt.year; d['mes']=d.fecha.dt.month
corr=[]
for nm,mask in [('Todo el año',d.mes>0),('Seca (nov–may)',~d.mes.between(6,10)),('Lluvias (jun–oct)',d.mes.between(6,10))]:
    for y in (2023,2024):
        s=d[mask&(d.anio==y)]; row={'per':nm,'anio':y}
        for pol,n in (('pm10','npm10'),('pm25','npm25')):
            for v,nv in (('et','net'),('rh','nrh'),('ws','nws')):
                t=s[(s[n]>=18)&(s[nv]>=18)]
                if len(t)>=30:
                    r_,p_=stats.spearmanr(t[pol],t[v]); row[f'{pol}_{v}']=[round(float(r_),2),len(t),float(p_)]
                else: row[f'{pol}_{v}']=[None,len(t),None]
        corr.append(row)
R['corr']=corr
d['llovio']=(d.pp>0)
rain=d[d.npp>=18].groupby(['anio','llovio']).agg(pm10=('pm10','mean'),pm25=('pm25','mean'),n=('pm10','count')).round(1).reset_index()
R['rain']=rain.to_dict('records')
# comparacion en lluvias: dias de lluvia en temporada lluvias
dl=d[(d.npp>=18)&d.mes.between(6,10)].groupby(['anio','llovio']).agg(pm10=('pm10','mean'),pm25=('pm25','mean'),n=('pm10','count')).round(1).reset_index(); R['rain_season']=dl.to_dict('records')
# bins horarios (coincidentes)
def bins(col,edges,labels):
    out={}
    for y in (2023,2024):
        g=h[(h.anio==y)&h[col].notna()&h.PM10.notna()]
        b=pd.cut(g[col],edges,labels=labels,right=False); out[y]=[(l,round(g.PM10[b==l].mean(),1),int((b==l).sum())) for l in labels]
    return out
Bws=bins('WS',[0,1,2,4,6,30],['0–1','1–2','2–4','4–6','≥6']); Brh=bins('RH',[0,30,45,60,75,101],['<30','30–45','45–60','60–75','≥75']); Bet=bins('ET',[0,12,18,24,30,50],['<12','12–18','18–24','24–30','≥30'])
R['bins']={'ws':{str(k):v for k,v in Bws.items()},'rh':{str(k):v for k,v in Brh.items()},'et':{str(k):v for k,v in Bet.items()}}
fig,axs=plt.subplots(1,3,figsize=(7.4,2.5),sharey=True)
for ax,(B,t,u) in zip(axs,[(Bws,'Viento','m/s'),(Brh,'Humedad relativa','%'),(Bet,'Temperatura','°C')]):
    for y in (2023,2024):
        ax.plot([b[0] if b[2]>=100 else b[0] for b in B[y]],[b[1] if b[2]>=100 else np.nan for b in B[y]],marker='o',ms=3.5,color=Y[y],label=str(y))
    ax.set_title(t,fontsize=9,fontweight='bold'); ax.set_xlabel(u); ax.tick_params(axis='x',labelsize=7.5)
axs[0].set_ylabel('PM$_{10}$ horario medio (µg/m³)'); axs[0].legend(frameon=False)
save(fig,'fig_meteo')
# calor para transporte: horas ET>=30 por mes (de horas validas)
heat=[]
for y in (2023,2024):
    for m in range(1,13):
        g=raw[(raw.anio==y)&(raw.mes==m)]; v=g.ET.dropna(); heat.append({'anio':y,'mes':m,'n':int(len(v)),'h30':int((v>=30).sum()),'cov':round(100*len(v)/len(g),0)})
R['heat']=heat
R['heat_tot']={y:{'h30':int(sum(x['h30'] for x in heat if x['anio']==y)),'n':int(sum(x['n'] for x in heat if x['anio']==y))} for y in (2023,2024)}
# horas del dia con ET>=30
R['heat_hora']={int(y):raw[(raw.anio==y)&(raw.ET>=30)].DATE.dt.hour.value_counts().sort_index().to_dict() for y in (2023,2024)}

# ---------- G. Sensibilidad umbrales vigentes 2024 ----------
def kk(x,l): return np.nan if pd.isna(x) else next((i for i,t in enumerate(l) if x<=t),4)
sens={}
for y in (2023,2024):
    s=dd[dd.anio==y]
    k=pd.Series([max([a for a in (kk(r.ind_PM10,[45,60,132,213]),kk(r['ind_PM2.5'],[15,33,79,130]),kk(r.ind_O3,[.058,.09,.135,.175])) if not pd.isna(a)] or [np.nan]) for _,r in s.iterrows()])
    sens[y]={'mala':int((k>=2).sum()),'muy':int((k>=3).sum()),'base_mala':int((s.k_global>=2).sum()),'base_muy':int((s.k_global>=3).sum())}
R['sens']=sens
# diferencias mensuales 2024-2023 en PM10 y mejores/peores meses
for y in (2023,2024):
    s=mm[mm.anio==y]; R[f'best_{y}']=int(s.loc[s.pm10.idxmin(),'mes']); R[f'worst_{y}']=int(s.loc[s.pm10.idxmax(),'mes'])
# horas/dias por tipo semana? dia de semana
dd['dow']=dd.fecha.dt.dayofweek
R['dow']=dd.groupby('dow').ind_PM10.mean().round(1).to_dict()
# fechas especiales: 1 enero, 24-25-31 dic
sp={}
for y in (2023,2024):
    for lab,(m,dday) in {'1 ene':(1,1),'31 dic':(12,31),'25 dic':(12,25),'24 dic':(12,24)}.items():
        r=dd[(dd.anio==y)&(dd.mes==m)&(dd.fecha.dt.day==dday)]
        sp[f'{lab} {y}']=None if r.empty else {'pm10':float(r.ind_PM10.iloc[0]),'pm25':None if pd.isna(r['ind_PM2.5'].iloc[0]) else float(r['ind_PM2.5'].iloc[0]),'hx':int(r.horas_extrema.iloc[0])}
R['sp']=sp
R['pm10only']={y:{'cat':[int((dd[dd.anio==y].k_PM10==k).sum()) for k in range(5)],'n':int(dd[dd.anio==y].k_PM10.notna().sum())} for y in (2023,2024)}
mc=[2,5,7,8,9,10,11,12]; R['mc']=mc; R['comp']={}
for y in (2023,2024):
    sy=dd[(dd.anio==y)&dd.mes.isin(mc)]; hy=h[(h.anio==y)&h.mes.isin(mc)]
    R['comp'][y]={'pm25_dia':round(sy['ind_PM2.5'].mean(),1),'pm10_dia':round(sy.ind_PM10.mean(),1),'glob':[int((sy.k_global==k).sum()) for k in range(5)],'pm25_malaplus':int((sy['k_PM2.5']>=2).sum()),'pm25_n':int(sy['k_PM2.5'].notna().sum())}
for y in (2023,2024):
    sy=dd[dd.anio==y]; R[f'seca_{y}']=round(sy[~sy.mes.between(6,10)].ind_PM10.mean(),1); R[f'lluvia_{y}']=round(sy[sy.mes.between(6,10)].ind_PM10.mean(),1)
    v=(sy.k_global>=2).values; m=c=0
    for x in v:
        c=c+1 if x else 0; m=max(m,c)
    R[f'racha_{y}']=m
for y in (2023,2024):
    sy=dd[(dd.anio==y)&(dd.k_global>=2)]
    R[f'domM_{y}']={'n':len(sy),'PM10':int(sy.dominante.str.contains('PM10',regex=False).sum()),'PM2.5':int(sy.dominante.str.contains('PM2.5',regex=False).sum()),'O3':int(sy.dominante.str.contains('O3',regex=False).sum()),
      'solo_PM10':int((sy.dominante=='PM10').sum()),'solo_PM2.5':int((sy.dominante=='PM2.5').sum()),'solo_O3':int((sy.dominante=='O3').sum()),'PM10/PM2.5':int((sy.dominante=='PM10/PM2.5').sum())}
R['dow_y']={int(y):g.groupby('dow').ind_PM10.mean().round(1).to_dict() for y,g in dd.groupby('anio')}
json.dump(R,open('out/R.json','w'),default=lambda o:o.item() if hasattr(o,'item') else str(o),indent=1,ensure_ascii=False)
dd.to_csv('out/diario_dow.csv',index=False); mm.to_csv('out/mensual.csv',index=False)
print('ok')
