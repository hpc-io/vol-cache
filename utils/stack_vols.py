#!/usr/bin/env python
# ---------------------------------------------------------------------------------
# This is for creating HDF5_VOL_CONNECTOR environment variables for VOL connectors;
# python stack_vols.py cache_ext async cache_ext async
# ---------------------------------------------------------------------------------

vols={'pass_through_ext':517, "cache_ext":518, "async":707}
import sys, os
nvols = len(sys.argv[1:])
print("Number of VOLs in the stack: %d" %nvols)
for v in sys.argv[1:]:
    try:
        print("* %s - %s" %(v, vols[v]))
    except:
        print("VOL %s do not exist" %v)
        exit()

s =""
i = 1
n=1
s = "%s "%sys.argv[1]
pv=sys.argv[1]
def gen_cache_ext_config(fname):
    f = open(fname, 'w')
    f.write("HDF5_CACHE_STORAGE_TYPE SSD\n")
    f.write("HDF5_CACHE_STORAGE_PATH /local/scratch\n")
    f.write("HDF5_CACHE_STORAGE_SCOPE LOCAL\n")
    f.write("HDF5_CACHE_STORAGE_SIZE 128755813888000 \n")
    f.write("HDF5_CACHE_WRITE_BUFFER_SIZE 17179869184 \n")
    f.close()

for v in sys.argv[2:]:
    if (i < nvols):
        print(pv)
        if (pv=="cache_ext"):
            s = s+ "config=conf%s.dat;under_vol=%s;under_info={"%(n,vols[sys.argv[i+1]])
            gen_cache_ext_config("conf%s.dat"%n)
            n=n+1

        else:
            s = s+ "under_vol=%s;under_info={"%(vols[sys.argv[i+1]])
    pv = sys.argv[i+1]
    i=i+1

    
if pv=="cache_ext":
    s = s+ "config=conf%s.dat;under_vol=0;under_info={}"%n
else:
    s = s+ "under_vol=0;under_info={}"
for i in range(nvols-1):
    s=s+"}"
print("export HDF5_PLUGIN_PATH=%s"%os.environ["HDF5_VOL_DIR"]+"/lib")
print("export HDF5_VOL_CONNECTOR=\"%s\""%s)
print("export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$HDF5_PLUGIN_PATH")


