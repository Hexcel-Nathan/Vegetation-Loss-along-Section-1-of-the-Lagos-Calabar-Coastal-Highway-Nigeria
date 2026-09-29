"""01 - Build the control units (Section 3.4).

Takes the two digitised control centrelines (western and eastern stretches), cuts each into
1 km segments, gives them a 69.4 m pseudo-footprint (the mean width of the Section 1 footprint)
and the same three distance bands (0-500 m, 500 m-1 km, 1-5 km), and splits the bands between
neighbouring segments with Voronoi cells so each unit belongs to exactly one segment.
Then merges them with the Section 1 units into segment_zones_all (628 units).

Inputs : data/vectors/C_linesWest.shp, ClinesEast.shp  (NB: the two file names are swapped -
         C_linesWest holds the EASTERN line and ClinesEast the WESTERN line; handled below)
         data/vectors/S1_segment_zones.shp, S1_footprint_diss.shp
Outputs: results/vectors/C_segment_zones.shp, C_segments.shp, C_footprint.shp, segment_zones_all.shp
"""
import sys; sys.path.insert(0, __import__('os').path.dirname(__file__))
from paths import VEC, RES
import shapefile, shutil, os
from shapely.geometry import shape, LineString, MultiPoint, Point, box, mapping
from shapely.ops import substring, voronoi_diagram, unary_union
from shapely import set_precision
PRJ=str(VEC/'C_linesWest.prj')
OUT=RES/'vectors'
HALF=69.4/2
def load(n):
    return shape(shapefile.Reader(str(VEC/n)).shape(0).__geo_interface__)
lines={'W':load('ClinesEast'),'E':load('C_linesWest')}   # file names were swapped
out_units=[]; out_segs=[]; out_fp=[]
for side,ln in lines.items():
    if ln.coords[0][0]>ln.coords[-1][0]: ln=LineString(ln.coords[::-1])
    L=ln.length; n=int(L//1000)
    cuts=[i*1000 for i in range(n)]+[L]      # last piece = 1000 + remainder
    segs=[substring(ln,cuts[i],cuts[i+1]) for i in range(n)]
    ids=[f'C{side}{i+1:02d}' for i in range(n)]
    fp=ln.buffer(HALF)
    outer=fp.buffer(5000)
    if side=='W':   # do not extend into Benin beyond the line start
        x0=ln.coords[0][0]; outer=outer.intersection(box(x0,outer.bounds[1]-1,outer.bounds[2]+1,outer.bounds[3]+1))
    # dense labelled points -> Voronoi -> dissolve per segment
    pts=[];lab=[]
    for sid,s in zip(ids,segs):
        k=max(2,int(s.length//25)+1)
        for j in range(k):
            pts.append(s.interpolate(j/(k-1),normalized=True)); lab.append(sid)
    env=outer.buffer(2000).envelope
    vor=voronoi_diagram(MultiPoint(pts),envelope=env)
    from shapely.strtree import STRtree
    tree=STRtree(pts)
    groups={sid:[] for sid in ids}
    for cell in vor.geoms:
        idx=tree.query(cell,predicate='contains')
        if len(idx): groups[lab[idx[0]]].append(cell)
    cells={sid:unary_union(groups[sid]).intersection(outer) for sid in ids}
    rings=[(0,'F',fp)]
    prev=fp
    for d,z in [(500,'B1'),(1000,'B2'),(5000,'B3')]:
        b=fp.buffer(d).difference(prev.buffer(0)); rings.append((d,z,b.intersection(outer))); prev=fp.buffer(d)
    for sid,s in zip(ids,segs):
        out_segs.append((sid,side,s))
        for d,z,rg in rings:
            g=cells[sid].intersection(rg)
            if not g.is_empty and g.area>1: out_units.append((sid,z,side,g.buffer(0)))
    out_fp.append((side,fp))
    print(side,'segments',n,'line km %.1f'%(L/1000),'last seg m %.0f'%segs[-1].length,'outer ha %.0f'%(outer.area/1e4),
          'units',sum(1 for u in out_units if u[2]==side))
def polyw(name,rows,fields):
    w=shapefile.Writer(name,shapeType=shapefile.POLYGON)
    for f in fields: w.field(*f)
    for rec,g in rows:
        w.shape(mapping(g)); w.record(*rec)
    w.close(); shutil.copy(PRJ,name+'.prj'); open(name+'.cpg','w').write('UTF-8')
polyw(str(OUT)+'/C_segment_zones',[((s,z,0,f'{s}_{z}',side),g) for s,z,side,g in out_units],
      [('seg_id','C',6),('zone','C',3),('treated','N',2,0),('unit_id','C',10),('side','C',3)])
w=shapefile.Writer(str(OUT)+'/C_segments',shapeType=shapefile.POLYLINE); w.field('seg_id','C',6); w.field('side','C',3); w.field('length_m','N',10,1)
for sid,side,s in out_segs: w.line([list(s.coords)]); w.record(sid,side,round(s.length,1))
w.close(); shutil.copy(PRJ,str(OUT)+'/C_segments.prj')
polyw(str(OUT)+'/C_footprint',[((side,),g) for side,g in out_fp],[('side','C',3)])
# merge with S1 units
s1=shapefile.Reader(str(VEC/'S1_segment_zones'))
allrows=[((r.record['seg_id'],r.record['zone'],1,r.record['unit_id'],'S1'),shape(r.shape.__geo_interface__)) for r in s1.iterShapeRecords()]
allrows+=[((s,z,0,f'{s}_{z}',side),g) for s,z,side,g in out_units]
polyw(str(OUT)+'/segment_zones_all',allrows,[('seg_id','C',6),('zone','C',3),('treated','N',2,0),('unit_id','C',10),('side','C',3)])
# checks
import collections
ids=[r[0][3] for r in allrows]; print('all units',len(allrows),'unique',len(set(ids)))
print('by side/zone',collections.Counter((r[0][4],r[0][1]) for r in allrows))
print('invalid',sum(1 for _,g in allrows if not g.is_valid))
fpS=shape(shapefile.Reader(str(VEC/'S1_footprint_diss')).shape(0).__geo_interface__)
cu=unary_union([g for (rec,g) in allrows if rec[2]==0]); print('min dist controls->S1 footprint km %.1f'%(cu.distance(fpS)/1000))
s1u=unary_union([g for (rec,g) in allrows if rec[2]==1]); print('overlap S1 vs controls ha %.2f'%(cu.intersection(s1u).area/1e4))
