
"""Generador del informe científico IGNIS UY. No modifica datos ni la lógica de ingestión."""
import io, json, calendar
from pathlib import Path
from datetime import datetime, timezone
from xml.sax.saxutils import escape
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.path import Path as MPath
from scipy.ndimage import gaussian_filter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.units import cm
from reportlab.lib.pagesizes import A4
from PIL import Image as PILImage
from ignis_coincidencias import emparejar, resumir_pares

BASE=Path(__file__).resolve().parent
MONTHS=['January','February','March','April','May','June','July','August','September','October','November','December']
CMAP=LinearSegmentedColormap.from_list('ignis',['#42206a','#8440a9','#dc4b95','#ff975a','#ffe36c'])
BG='#081425'; PANEL='#11203b'; PANEL2='#172949'; WHITE='#eef4ff'; SOFT='#b8c9ee'; CYAN='#67d6ff'; VIOLET='#d9c7ff'


def image_asset(name,w=2.7*cm):
    p=BASE/name
    if not p.exists():
        return None
    with PILImage.open(p) as im:
        aw,ah=im.size
    return RLImage(str(p),width=w,height=w*ah/aw,kind='proportional')


def plot_buffer(fig):
    buffer=io.BytesIO()
    fig.savefig(buffer,format='png',dpi=180,bbox_inches='tight',facecolor=BG)
    plt.close(fig)
    buffer.seek(0)
    return buffer


def family_from_sensor(series):
    s=series.astype(str).str.upper()
    return np.where(s.str.startswith('VIIRS'),'VIIRS','MODIS')


def ensure_time_cols(df):
    z=df.copy()
    if 'anio' not in z.columns or 'mes' not in z.columns or 'dia' not in z.columns:
        t=pd.to_datetime(z['fecha'],errors='coerce',utc=True)
        z['anio']=t.dt.year
        z['mes']=t.dt.month
        z['dia']=t.dt.strftime('%Y-%m-%d')
    return z


def compress_periods(df):
    if df.empty:
        return []
    z=ensure_time_cols(df)
    by_year=z.groupby('anio')['instrumento'].apply(lambda s:' + '.join(sorted(set(map(str,s)))))
    periods=[]; start=prev=sig=None
    for year, signature in by_year.items():
        year=int(year)
        if start is None:
            start=prev=year; sig=signature; continue
        if year==prev+1 and signature==sig:
            prev=year; continue
        periods.append({'Periodo':f'{start}–{prev}' if start!=prev else str(start),'Configuración instrumental':sig})
        start=prev=year; sig=signature
    if start is not None:
        periods.append({'Periodo':f'{start}–{prev}' if start!=prev else str(start),'Configuración instrumental':sig})
    return periods


def resumen_armonizacion(df, ano=None, grid_deg=0.20):
    z=ensure_time_cols(df)
    if z.empty:
        return {'has_both':False,'overlap_years':[], 'overlap_months':pd.DataFrame(), 'coincident_cells':pd.DataFrame(), 'periods':[]}
    z=z.copy()
    z['familia']=family_from_sensor(z['instrumento'])
    counts=z.groupby('familia').size().to_dict()
    has_both=counts.get('MODIS',0)>0 and counts.get('VIIRS',0)>0
    annual=z.groupby(['anio','familia']).size().unstack(fill_value=0) if len(z) else pd.DataFrame()
    overlap_years=[]
    if not annual.empty:
        overlap=annual[(annual.get('MODIS',0)>0)&(annual.get('VIIRS',0)>0)]
        overlap_years=[int(y) for y in overlap.index.tolist()]
    periods=compress_periods(z)
    if not has_both:
        return {'has_both':False,'overlap_years':overlap_years,'overlap_months':pd.DataFrame(), 'coincident_cells':pd.DataFrame(), 'periods':periods}

    q=z[['anio','mes','dia','latitude','longitude','familia']].dropna().copy()
    q['latitude']=pd.to_numeric(q['latitude'],errors='coerce')
    q['longitude']=pd.to_numeric(q['longitude'],errors='coerce')
    q=q.dropna(subset=['latitude','longitude'])
    q['grid_lat']=np.round(q['latitude']/grid_deg).astype(int)
    q['grid_lon']=np.round(q['longitude']/grid_deg).astype(int)
    cells=q.groupby(['anio','mes','dia','grid_lat','grid_lon','familia']).size().reset_index(name='n')
    wide=cells.pivot_table(index=['anio','mes','dia','grid_lat','grid_lon'],columns='familia',values='n',aggfunc='sum',fill_value=0).reset_index()
    wide['coincidencia_modis_viirs']=(wide.get('MODIS',0)>0)&(wide.get('VIIRS',0)>0)
    coinc=wide[wide['coincidencia_modis_viirs']].copy()
    overlap_months=z.groupby(['anio','mes','familia']).size().unstack(fill_value=0)
    overlap_months=overlap_months[(overlap_months.get('MODIS',0)>0)&(overlap_months.get('VIIRS',0)>0)].reset_index()
    if ano is not None:
        overlap_months=overlap_months[overlap_months['anio']==int(ano)].copy()
        coinc=coinc[coinc['anio']==int(ano)].copy()
    coinc_monthly=coinc.groupby(['anio','mes']).size().reset_index(name='celdas_coincidentes') if len(coinc) else pd.DataFrame(columns=['anio','mes','celdas_coincidentes'])
    return {'has_both':True,'overlap_years':overlap_years,'overlap_months':overlap_months,'coincident_cells':coinc_monthly,'periods':periods}


def calendar_figure(df):
    counts=df.groupby(['anio','mes']).size()
    years=list(range(2000,2027)); cells=np.full((12,len(years)),np.nan)
    for (y,m),n in counts.items():
        if 2000<=int(y)<=2026 and 1<=int(m)<=12:
            cells[int(m)-1,int(y)-2000]=n
    fig,ax=plt.subplots(figsize=(10.5,3.6),facecolor=BG)
    ax.set_facecolor(BG)
    cmap=CMAP.copy(); cmap.set_bad('#122034')
    image=ax.imshow(np.ma.masked_invalid(cells),aspect='auto',cmap=cmap,interpolation='nearest')
    ax.set_xticks(range(0,27,2),years[::2],fontsize=7,color=WHITE)
    ax.set_yticks(range(12),[x[:3] for x in MONTHS],fontsize=8,color=WHITE)
    ax.tick_params(length=0,colors=WHITE)
    ax.set_title('Historical calendar of monthly records (uploaded files)',fontsize=11,pad=10,color=WHITE)
    for spine in ax.spines.values(): spine.set_color('#35527b')
    cbar=fig.colorbar(image,ax=ax,shrink=.8,label='Records')
    cbar.ax.yaxis.label.set_color(WHITE); cbar.ax.tick_params(colors=WHITE)
    fig.tight_layout()
    return plot_buffer(fig)


def daily_calendar_figure(year, ano):
    if year.empty:
        return None
    dates = pd.to_datetime(year['dia'], errors='coerce').dropna()
    if dates.empty:
        return None
    daily = dates.dt.date.value_counts().to_dict()
    months = sorted(set(dates.dt.month))
    cols = min(3, len(months))
    rows = (len(months) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(10.2, 2.35 * rows + .3), squeeze=False, facecolor=BG)
    maximum = max(daily.values()) if daily else 1
    norm = Normalize(vmin=1, vmax=max(2, maximum))
    for k, month in enumerate(months):
        ax = axes[k // cols][k % cols]
        ax.set_xlim(0, 7); ax.set_ylim(7.0, -.7); ax.axis('off')
        ax.set_facecolor(BG)
        ax.set_title(f'{MONTHS[month-1]} {ano}', loc='left', fontsize=11, fontweight='bold', color=WHITE, pad=5)
        for j, name in enumerate(['L', 'M', 'X', 'J', 'V', 'S', 'D']):
            ax.text(j+.5, .35, name, ha='center', va='center', fontsize=8, color=SOFT)
        weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(int(ano), int(month))
        for wi, week in enumerate(weeks):
            for di, day in enumerate(week):
                if day.month != month:
                    continue
                n = daily.get(day)
                face = CMAP(norm(n)) if n is not None else '#122034'
                rect = plt.Rectangle((di+.055, wi+1.05), .89, .84, facecolor=face, edgecolor='#29456d', linewidth=.6)
                ax.add_patch(rect)
                ax.text(di+.5, wi+1.33, str(day.day), ha='center', va='center', fontsize=7.3,
                        color='white' if n is not None else SOFT)
                if n is not None:
                    ax.text(di+.5, wi+1.70, str(n), ha='center', va='center', fontsize=9,
                            fontweight='bold', color='white')
    for k in range(len(months), rows*cols):
        axes[k // cols][k % cols].axis('off')
    fig.tight_layout(pad=1.3)
    return plot_buffer(fig)


def trend_figure(df):
    agg=df.groupby(['anio','instrumento']).size().unstack(fill_value=0)
    fig,ax=plt.subplots(figsize=(10,3.6),facecolor=BG)
    ax.set_facecolor(BG)
    if not agg.empty:
        agg.index=agg.index.astype(int).astype(str)
        palette=['#5d7fe6','#ff7e96','#9d74e5','#f1bf66'][:len(agg.columns)]
        agg.plot.bar(ax=ax,width=.75,rot=45,color=palette)
    ax.set_ylabel('FIRMS records',color=WHITE)
    ax.set_xlabel('Year in uploaded files',color=WHITE)
    ax.grid(axis='y',alpha=.18,color='#5677a5')
    ax.legend(fontsize=7,loc='upper left',facecolor=BG,edgecolor='#35527b',labelcolor=WHITE)
    ax.tick_params(colors=WHITE,labelsize=7)
    ax.set_title('Annual count by instrument family (not normalized)',fontsize=10,color=WHITE)
    for spine in ax.spines.values(): spine.set_color('#35527b')
    fig.tight_layout()
    return plot_buffer(fig)


def map_figure(df):
    raw=json.loads((BASE/'uruguay_contorno.geojson').read_text(encoding='utf-8'))
    geometry=raw['features'][0]['geometry']; ring=geometry['coordinates'][0] if geometry['type']=='Polygon' else geometry['coordinates'][0][0]
    border=np.asarray(ring,dtype=float)
    clean=df[['longitude','latitude']].apply(pd.to_numeric,errors='coerce').dropna()
    clean=clean[clean.longitude.between(-59,-52)&clean.latitude.between(-36,-29)]
    if clean.empty:
        return None
    xedges=np.linspace(-58.8,-52.8,125); yedges=np.linspace(-35.4,-29.8,125)
    hist,*_=np.histogram2d(clean.longitude,clean.latitude,bins=[xedges,yedges]); dense=gaussian_filter(hist.T,sigma=2.5)
    x=(xedges[1:]+xedges[:-1])/2; y=(yedges[1:]+yedges[:-1])/2
    xx,yy=np.meshgrid(x,y); mask=MPath(border).contains_points(np.c_[xx.ravel(),yy.ravel()]).reshape(xx.shape)
    dense[~mask]=np.nan; dense[dense<.06]=np.nan
    fig,ax=plt.subplots(figsize=(9.4,6.0),facecolor=BG); ax.set_facecolor('#0b1230')
    ax.fill(border[:,0],border[:,1],color='#211c4a',alpha=.9)
    img=ax.imshow(dense,extent=[xedges[0],xedges[-1],yedges[0],yedges[-1]],origin='lower',cmap=CMAP,interpolation='bilinear',alpha=.95,aspect='auto')
    plot=clean.sample(min(1800,len(clean)),random_state=42)
    ax.scatter(plot.longitude,plot.latitude,s=2.4,color='#e8eaff',alpha=.4,zorder=3)
    ax.plot(border[:,0],border[:,1],color='#a5cfff',lw=1.5,zorder=4)
    for name,lon,lat in [('Artigas',-56.0,-30.45),('Durazno',-56.52,-33.22),('Canelones',-56.28,-34.55),('Maldonado',-54.95,-34.73),('Rocha',-54.32,-34.12)]:
        ax.text(lon,lat,name,color='white',fontsize=7,bbox=dict(facecolor='#14142f',alpha=.65,edgecolor='none',pad=2))
    ax.set(xlim=(-58.85,-52.65),ylim=(-35.45,-29.75),xlabel='Longitud',ylabel='Latitud')
    ax.tick_params(colors=WHITE,labelsize=7)
    for spine in ax.spines.values(): spine.set_color('#35527b')
    cbar=fig.colorbar(img,ax=ax,shrink=.7,label='Densidad visual relativa (no calibrada)')
    cbar.ax.yaxis.label.set_color(WHITE); cbar.ax.tick_params(colors=WHITE)
    fig.tight_layout()
    return plot_buffer(fig)


def banner_table(text):
    tb=Table([[Paragraph(text, getSampleStyleSheet()['BodyText'])]], colWidths=[16.3*cm])
    tb.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#13284b')),
        ('BOX',(0,0),(-1,-1),0.6,colors.HexColor('#35527b')),
        ('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
    ]))
    return tb


def generar_informe_pdf(datos,ano,region,sensores,alertas_func=None):
    df=ensure_time_cols(datos.copy())
    year=df[df.anio==ano].copy()
    out=io.BytesIO()
    doc=SimpleDocTemplate(out,pagesize=A4,leftMargin=1.55*cm,rightMargin=1.55*cm,topMargin=1.45*cm,bottomMargin=1.55*cm,title='IGNIS UY - Scientific thermal activity report',author='Proyecto IGNIS UY')
    S=getSampleStyleSheet()
    S.add(ParagraphStyle(name='PaperT',parent=S['Title'],fontName='Helvetica-Bold',fontSize=20,leading=24,textColor=colors.HexColor(WHITE),alignment=TA_CENTER,spaceAfter=6))
    S.add(ParagraphStyle(name='PaperSub',parent=S['Normal'],alignment=TA_CENTER,fontSize=10,leading=13,textColor=colors.HexColor(SOFT),spaceAfter=8))
    S.add(ParagraphStyle(name='PaperH',parent=S['Heading2'],fontSize=13,leading=16,textColor=colors.HexColor(CYAN),spaceBefore=12,spaceAfter=6,keepWithNext=True))
    S.add(ParagraphStyle(name='PaperBody',parent=S['BodyText'],fontSize=9.1,leading=13.1,alignment=TA_JUSTIFY,spaceAfter=7,textColor=colors.HexColor(WHITE)))
    S.add(ParagraphStyle(name='PaperBodySoft',parent=S['BodyText'],fontSize=8.7,leading=12.8,alignment=TA_JUSTIFY,spaceAfter=7,textColor=colors.HexColor(SOFT)))
    S.add(ParagraphStyle(name='PaperCaption',parent=S['Normal'],fontSize=8,leading=11,textColor=colors.HexColor(SOFT),spaceAfter=9))
    S.add(ParagraphStyle(name='CallTitle',parent=S['Heading3'],fontSize=12,leading=14,textColor=colors.HexColor(WHITE),spaceAfter=4))
    P=lambda t,style='PaperBody':Paragraph(str(t),S[style])
    story=[]

    left=image_asset('logo_ignis_informe.png',2.3*cm) or image_asset('logo_ignis.png',2.3*cm)
    right=image_asset('logo_nasa_informe.png',2.1*cm) or image_asset('logo_nasa.png',2.1*cm)
    header_center=Paragraph('IGNIS UY<br/><font size="10" color="#b8c9ee">Research project · NASA Space Apps Challenge 2026</font>',S['PaperT'])
    if left and right:
        t=Table([[left,header_center,right]],colWidths=[3.2*cm,10.1*cm,2.7*cm],hAlign='CENTER')
        t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('ALIGN',(0,0),(0,0),'LEFT'),('ALIGN',(2,0),(2,0),'RIGHT'),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
        story.append(t)
    else:
        story.append(header_center)
    story.extend([
        P('Historical thermal activity analysis in Uruguay','PaperT'),
        P('NASA FIRMS · MODIS and VIIRS instruments · Exploratory technical report','PaperSub')
    ])

    hero=BASE/'hero_espacio.jpg'
    if hero.exists():
        story.extend([RLImage(str(hero), width=16.3*cm, height=3.1*cm), Spacer(1,0.15*cm)])

    meta=Table([
        [P(f'<b>Selected year:</b> {ano}'), P(f'<b>Selection:</b> {escape(region)}')],
        [P(f'<b>Active sensors:</b> {escape(", ".join(sensores))}'), P('Issued on (UTC): '+datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M'))]
    ], colWidths=[8.0*cm,8.0*cm])
    meta.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),colors.HexColor(PANEL)),
        ('BOX',(0,0),(-1,-1),0.7,colors.HexColor('#35527b')),
        ('INNERGRID',(0,0),(-1,-1),0.35,colors.HexColor('#2a4165')),
        ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
        ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
    ]))
    story.extend([meta, Spacer(1,0.12*cm)])
    story.append(P('<b>Summary.</b> This report only summarizes satellite observations imported into the IGNIS Master dataset. Detections are thermal anomalies, not confirmed wildfires; they do not represent burned area or wildfire rates. The MODIS–VIIRS comparison is exploratory and is not a calibrated series.'))

    story.append(P('1. Purpose and scope','PaperH'))
    story.append(P('Describe the temporal and geographic distribution of detections in the selected area; place the selected year in the context of uploaded historical records; identify preliminary statistical signals; explain the current status of MODIS–VIIRS harmonization; and document the system's main limitations.'))

    story.append(P('2. Results for the selected year','PaperH'))
    rows=[['Indicator','Result'],['Yearly records',str(len(year))],['Days with records',str(year.dia.nunique())],['Instrument families',', '.join(sorted(map(str,year.instrumento.unique()))) or 'No records']]
    rows.append(['Month with the most records',MONTHS[int(year.groupby('mes').size().idxmax())-1] if len(year) else 'Unavailable'])
    for k,v in sorted(year.groupby('instrumento').size().to_dict().items()):
        rows.append([f'Records {k}',str(v)])
    table=Table(rows,colWidths=[8.2*cm,8.1*cm],repeatRows=1,hAlign='LEFT')
    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#183153')),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('BACKGROUND',(0,1),(-1,-1),colors.HexColor(PANEL)),
        ('TEXTCOLOR',(0,1),(-1,-1),colors.HexColor(WHITE)),
        ('GRID',(0,0),(-1,-1),.4,colors.HexColor('#2e4d76')),
        ('FONTSIZE',(0,0),(-1,-1),8.3),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)
    ]))
    story.extend([table, Spacer(1,0.12*cm)])

    story.append(P('3. Daily calendar and seasonality','PaperH'))
    monthly=year.groupby('mes').size().to_dict()
    if monthly:
        story.append(P('<b>Months with imported observations:</b> ' + ' · '.join(f'{MONTHS[int(m)-1]}: {n}' for m,n in sorted(monthly.items()))))
    else:
        story.append(P('There are no observations for the selected year in imported files.'))
    story.append(P('Unlisted months have no observations in uploaded files. This does not prove an absence of thermal activity or complete satellite coverage.','PaperBodySoft'))
    visual=daily_calendar_figure(year,ano)
    if visual:
        rows_months=max(1,(len(set(pd.to_datetime(year["dia"],errors='coerce').dropna().dt.month))+2)//3)
        story.extend([
            RLImage(visual,width=16.0*cm,height=(2.35 * rows_months + .45)*16.0/10.2*cm),
            P('Daily calendar. The number in each colored cell indicates FIRMS observations that day. Dark cells contain no records in uploaded data and do not necessarily represent days without wildfires.','PaperCaption')
        ])
    if len(df):
        story.extend([RLImage(calendar_figure(df),width=16.0*cm,height=5.45*cm),P('Figure 1. Historical monthly distribution of uploaded observations. Empty cells do not establish an absence of activity or complete coverage.','PaperCaption')])

    story.append(P('4. Historical context and cross-sensor comparison','PaperH'))
    story.append(P(f'The uploaded historical archive contains {len(df):,} unique observations across {df.anio.nunique()} years with records. Counts are not normalized for coverage, orbital revisits, or sensor sensitivity.'))
    if len(df):
        story.extend([RLImage(trend_figure(df),width=16*cm,height=5.2*cm),P('Figure 2. Observations by year and instrument. These counts must not be interpreted as climate trends or wildfire incidence.','PaperCaption')])

    story.append(P('5. Thermal map of Uruguay — selected year','PaperH'))
    map_data=map_figure(year) if len(year) else None
    if map_data:
        story.extend([RLImage(map_data,width=15.8*cm,height=10.1*cm),P('Figure 3. Spatial distribution for the selected year only. The generalized reference outline does not represent calibrated density, confirmed wildfires, or burned area.','PaperCaption')])
    else:
        story.append(P('There are no valid coordinates for the selected year. Observations from other years are not substituted.'))

    story.append(P('6. MODIS–VIIRS harmonization and exploratory signals','PaperH'))

    armonia=resumen_armonizacion(df, ano)
    instruments=set(map(str,df.instrumento.astype(str).unique()))
    has_modis=any(k.upper().startswith('MODIS') for k in instruments)
    has_viirs=any(k.upper().startswith('VIIRS') for k in instruments)
    if has_modis and has_viirs:
        story.append(P('Both instrument families are represented in the IGNIS Master dataset. This supports richer historical analysis but <b>does not</b> justify combining raw MODIS and VIIRS counts as directly equivalent physical measurements.'))
        if armonia['overlap_years']:
            story.append(P('Years with overlapping instrument families in the selected area: ' + ', '.join(str(y) for y in armonia['overlap_years']) + '.'))
        periods=armonia.get('periods',[])
        if periods:
            per_rows=[['Period','Instrument configuration']] + [[p['Periodo'],p['Configuración instrumental']] for p in periods[:8]]
            pt=Table(per_rows,colWidths=[3.2*cm,12.6*cm],repeatRows=1)
            pt.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#183153')),('TEXTCOLOR',(0,0),(-1,0),colors.white),
                ('BACKGROUND',(0,1),(-1,-1),colors.HexColor(PANEL2)),('TEXTCOLOR',(0,1),(-1,-1),colors.HexColor(WHITE)),
                ('GRID',(0,0),(-1,-1),.35,colors.HexColor('#2e4d76')),('FONTSIZE',(0,0),(-1,-1),8),
                ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)
            ]))
            story.extend([pt, Spacer(1,0.10*cm)])
        if not armonia['coincident_cells'].empty:
            cc=armonia['coincident_cells'].copy(); cc['Mes']=cc['mes'].map(lambda m: MONTHS[int(m)-1]); cc=cc[['Mes','celdas_coincidentes']]
            story.append(P(f'Exploratory spatial-temporal matching for {ano}: {int(cc["celdas_coincidentes"].sum())} approximate geographic cells have both MODIS and VIIRS observations on the same UTC day.'))
            cc_rows=[['Month','Matching cells']] + cc.values.tolist()
            ct=Table(cc_rows,colWidths=[6.5*cm,9.0*cm],repeatRows=1)
            ct.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#183153')),('TEXTCOLOR',(0,0),(-1,0),colors.white),
                ('BACKGROUND',(0,1),(-1,-1),colors.HexColor(PANEL)),('TEXTCOLOR',(0,1),(-1,-1),colors.HexColor(WHITE)),
                ('GRID',(0,0),(-1,-1),.35,colors.HexColor('#2e4d76')),('FONTSIZE',(0,0),(-1,-1),8),
                ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)
            ]))
            story.extend([ct, Spacer(1,0.08*cm)])
        else:
            story.append(P(f'No exploratory MODIS–VIIRS matches were found in {ano} using the implemented criteria (same UTC day and approximate spatial cell). This does not establish an absence of the physical event or invalidate the series.'))
        story.append(P('Pilot harmonization method: approximate 0.20° spatial-cell and UTC-day matching (exploratory only). The purpose is to examine historical continuity, not to sum sensors or calibrate actual coverage.','PaperBodySoft'))
    else:
        story.append(P('The uploaded files do not contain both MODIS and VIIRS observations for this selection. No cross-instrument comparison is available.'))

    story.append(P('Additional cross-instrument proximity test','PaperH'))
    pares=emparejar(df,ano,radio_km=5.0,ventana_min=30)
    story.append(P('A second independent criterion matches observations on the same UTC day within 5 km and 30 minutes, using one-to-one matching by instrument pair and spherical Earth geometry. This does not establish equal radiance, resolution equivalence, or wildfire identity.'))
    story.append(P(f'In {ano}, <b>{len(pares)} candidate pairs</b> were found across <b>{pares.fecha_utc.nunique() if len(pares) else 0} days</b>. This number must not be added to observation counts or matching cells.'))
    resumen=resumir_pares(pares)
    if len(resumen):
        rows=[['Month','Instruments','Pairs','Median distance','Median Δt']]
        for _,r in resumen.head(15).iterrows():
            rows.append([str(r['Mes']),str(r['Par instrumental']),str(int(r.Pares)),f'{r["Distancia mediana (km)"]:.2f} km',f'{r["Diferencia mediana (min)"]:.1f} min'])
        t2=Table(rows,colWidths=[2.0*cm,6.3*cm,1.6*cm,3.0*cm,3.0*cm],repeatRows=1)
        t2.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#183153')),('BACKGROUND',(0,1),(-1,-1),colors.HexColor(PANEL)),('TEXTCOLOR',(0,0),(-1,-1),colors.HexColor(WHITE)),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#2e4d76')),('FONTSIZE',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        story.extend([t2,Spacer(1,0.1*cm)])
    story.append(P('Limitation: matching only establishes spatial-temporal associations. Radiometric or statistical harmonization requires cross-product calibration, bias and coverage assessments, and independent validation.','PaperBodySoft'))

    story.append(P('7. Unusual activity and documentary traceability','PaperH'))
    candidates=[]
    if alertas_func is not None:
        for sensor in sorted(df.instrumento.unique()):
            candidates.extend(alertas_func(df,sensor))
    found=[x for x in candidates if int(x['Año'])==ano]
    story.append(P(f'The complete archive contains {len(candidates)} exploratory statistical candidates, of which {len(found)} are from {ano}. These are neither operational alerts nor confirmed wildfires.'))
    story.append(P('Pilot criterion: at least five records for an instrument-month and at least twice the median of three or more other years with comparable observations. Without satellite-coverage normalization, these are only preliminary signals.','PaperBodySoft'))
    if found:
        r=[['Month','Instrument','Records','Median','Index']] + [[MONTHS[int(x['Mes'])-1][:3],str(x['Sensor']),str(x['Detecciones']),str(x['Mediana otros años']),str(x['Índice frente a mediana'])] for x in found[:16]]
        tb=Table(r,colWidths=[2.1*cm,4.8*cm,2.6*cm,3.2*cm,3.3*cm],repeatRows=1)
        tb.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#183153')),('TEXTCOLOR',(0,0),(-1,0),colors.white),
            ('BACKGROUND',(0,1),(-1,-1),colors.HexColor(PANEL2)),('TEXTCOLOR',(0,1),(-1,-1),colors.HexColor(WHITE)),
            ('GRID',(0,0),(-1,-1),.35,colors.HexColor('#2e4d76')),('FONTSIZE',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)
        ]))
        story.extend([tb, Spacer(1,0.1*cm)])
    story.append(P('The included documentary library contains 2023 case files, which are not automatically attributed to other years, locations, or FIRMS observations. Factual traceability requires independent sources, dates, and spatial matches.'))

    story.append(P('8. Provenance, reproducibility, and limitations','PaperH'))
    story.append(P('Primary source: user-provided NASA FIRMS files and normalized observations stored in the IGNIS Master dataset. Export the Master dataset manually and retain original ZIP files. The PDF is generated from the session's uploaded data and active filters.'))
    story.append(P('Main limitations: unverified temporal coverage; differing instrument resolution and sensitivity; unnormalized orbital revisits; reference-outline artifacts; and detections not verified as wildfires. Empty calendar and map areas represent missing records <i>in the uploaded files</i>.'))
    story.append(P('<b>Intended use:</b> a research report and documentary reference for Team IGNIS UY, not an operational warning product or wildfire certification.'))

    # Conclusión sustentada en todo el Maestro, separando registros de incidencias.
    total=int(len(df))
    n_years=int(df.anio.nunique()) if len(df) else 0
    n_sensors=int(df.instrumento.nunique()) if len(df) else 0
    years_sorted=sorted(int(y) for y in df.anio.dropna().unique()) if len(df) else []
    first_year=years_sorted[0] if years_sorted else ano
    last_year=years_sorted[-1] if years_sorted else ano
    n_current=len(year)
    n_candidates=len(candidates)
    story.append(P('9. Full historical archive conclusions','PaperH'))
    story.append(P(
        f'The IGNIS Master dataset contains <b>{total:,} unique satellite observations</b> across '
        f'<b>{n_years} years with records ({first_year}–{last_year})</b> and '
        f'<b>{n_sensors} instrument families</b>. This dataset can describe the '
        f'temporal and spatial distribution of submitted observations, document overlapping sensor periods, '
        f'and highlight statistically unusual months for review. '
        f'The selected year ({ano}) contains {n_current} records; it is one part of the series, '
        f'not the project's complete conclusion.'
    ))
    story.append(P(
        f'The historical archive contains <b>{n_candidates} exploratory candidates</b> '
        f'under the monthly criterion, of which <b>{len(found)}</b> belong to {ano}. '
        'Additionally, MODIS–VIIRS day-cell matches and pairs with geographic '
        'and temporal proximity are reproducible observational associations, '
        'not verified detections of the same wildfire. Observations from '
        'different instruments are not added as if they were unique events.'
    ))
    story.append(P(
        '<b>Scientific conclusion:</b> IGNIS demonstrates the feasibility of integrating, exploring, and '
        'documenting FIRMS observations from different instruments in one interface, '
        'with explicit interpretive limits. The archive alone cannot establish '
        'increases or decreases in wildfires or climate trends because '
        'temporal coverage is unverified, instruments differ, and counts are not normalized. '
        'Future development requires coverage assessments, independent-source validation, '
        'and cross-instrument calibration before drawing quantitative conclusions.'
    ))


    def draw_bg(canvas, document, first=False):
        canvas.saveState()
        w,h=A4
        canvas.setFillColor(colors.HexColor(BG))
        canvas.rect(0,0,w,h,fill=1,stroke=0)
        # El hero se inserta una sola vez en el contenido: sin segundo fondo en portada.
        canvas.setStrokeColor(colors.HexColor('#2c4770'))
        canvas.line(1.55*cm,1.15*cm,w-1.55*cm,1.15*cm)
        canvas.setFont('Helvetica',7)
        canvas.setFillColor(colors.HexColor(SOFT))
        canvas.drawString(1.55*cm,0.86*cm,'IGNIS UY | Exploratory technical report · NASA FIRMS')
        canvas.drawRightString(w-1.55*cm,0.86*cm,f'Page {document.page}')
        canvas.restoreState()

    doc.build(story,onFirstPage=lambda c,d: draw_bg(c,d,True),onLaterPages=lambda c,d: draw_bg(c,d,False))
    return out.getvalue()
