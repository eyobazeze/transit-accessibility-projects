import sys, numpy as np, itertools
sys.path.insert(0,"src")
import transit_access_analysis as t
from scipy.spatial import cKDTree
from pathlib import Path
root=Path(".")
db,dp,do,_=t.default_paths(root)
_,b=t.load_boundary(db)
x,y,pop,(gx,gy),_,_=t.load_population(dp,b)
pts,_,_=t.load_osm_points(do,b)
d=cKDTree(np.c_[pts.geometry.x,pts.geometry.y]).query(np.c_[x,y],k=1)[0]
print("shift_x shift_y ncells cutoff n_priority pop beyond500 clusters")
res=[]
for sx,sy in itertools.product([0,-125,-250,-375],[0,125,250,375]):
    c=t.build_cells(x,y,pop,d,b,(gx+sx,gy+sy))
    cut=c.population_density.quantile(.75)
    p=c[(c.population_density>=cut)&(c.underserved_share_500m>=.5)]
    k=len(t.connected_clusters(p)[1]) if isinstance(t.connected_clusters(p),tuple) else None
    res.append((len(p),p.population.sum(),p.underserved_pop_500m.sum()))
    print(sx,sy,len(c),round(cut),len(p),round(p.population.sum()),round(p.underserved_pop_500m.sum()),k)
a=np.array(res);print("range n",a[:,0].min(),a[:,0].max(),"pop",a[:,1].min().round(),a[:,1].max().round(),"beyond",a[:,2].min().round(),a[:,2].max().round())
