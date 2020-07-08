# Design of node local storage cache external VOL connector
Created: June 8, 2020\
Updated: June 23, 2020 (included comments from Quincey)

## Motivation - targeting workloads
Many high performance computing (HPC) systems have two types of fast storage, a global parallel file system such as Lustre or GPFS and node-local storage attached to the compute nodes. To our knowledge, the node-local storage is rarely integrated into the parallel I/O workflows of real applications. 

We would like to use the node-local storage as a cache for the parallel file system to “effectively” improve the parallel I/O efficiency. In particular, since node-local storage is attached to the compute node, writing/reading data to and from the node-local storage will scale very well. At large scales, we expect the aggregate I/O bandwidth to surpass the bandwidth of the parallel file system. Therefore, using node-local storage to cache/stage data will greatly benefit large scale I/O-heavy workloads. 

Specifically, we expect our design will benefit the following two type of workloads: 

- Intensive repetitive reading workloads, such as deep learning applications. In such workloads, the same dataset is being read again and again at each iteration, typically in a batch streaming fashion. The workloads are distributed in a data-parallel fashion. Using node-local storage to asynchronously stage the data into the node so that the application could directly read data from the node-local storage without going to the parallel file system. This will greatly improve the I/O performance and scaling efficiency. We expect various Deep learning based ECP projects, such as ExaLearn, CANDLE will benefit from this. 
- Heavy check-pointing workloads. Simulations usually write intermediate data to the file system for the purpose of restarting or post-processing. Within our framework, the application will write the data to the node-local storage first and the data migration to the parallel file system is done in an async fashion without blocking the simulation. We expect this design will benefit those heavy check-pointing simulations, such as particle based dynamic simulation. ECP applications, such as Lammps, HACC will benefit from this. 

In order to make it easy for the application to adopt our implementation without much modification of their codes, we implement everything in the HDF5 Virtual Object Layer (VOL) framework. The purpose of this document is to outline the high level design of the cache VOL connector. 


## High level API Design
### Policy of using the node local storage
* We allow each **file** or **dataset** to claim certain portion of the local storage for caching its data on the local storage. 
* We create a unique folder associated with each file on the local storage and store all the cached data inside the folder. 
* Properties of the cache
   - purpose [```READ```/```WRITE```/```RDWR```] - what is the purpose of this cache, either cache for read workloads or write workloads, or read & write. (```RDWR``` is a `placehoder. We are currently focusing on supporting ```READ``` and ```WRITE``` mode).
   - duration [permanent/temporal]
      - ```PERMANENT``` - Permanent cache will exist through out the entire simulation except being explicitly evicted. 
      - ```TEMPORAL``` - it will be released if other file use the space. By default, all the write cache will be temporal. Once the data is migrated to the parallel file system, the cache is automatically evicted, and the space is reusable by other file. 
   - growable [true/false] whether we allow the size to grow or not. 
* We take account of each access to the cache. 
   - We document the following events: creation event, write / read events
   - The data eviction for the temporal cache is based on the acess info according to certain algorithm to be specified
   - Once the data has been evicted from the node-local storage, the application has to go to the parallel file system to get the data. 


### Public APIs 
These public APIs allow the application to have fine control on the node-local caches. In principle, If the application do not call these functions, we will have a set of default options for the application. 

#### Local storage (LS) related functions
* H5LSset -- set the infomation of node local storage
 - the size
 - global path of the local storage 
 - such as /local/scratch (will interface with any system function calls)
* H5LSquery_XXX -- query the status of the local storage
 - path / namespace
 - space total
 - space left
 - list of files that are using the cache, and how much space they occupied
* H5LSregister_cache (LS, cache) -- registering a cache to the cache list in the system’s local storage.
* H5LSremove_cache(LS, cache) -- remove a cache and associated files from the system’s local storage.
* H5LSregister_access_count -- registering any access events.
* H5LSclaim_space(size, char \*path, int opt, ...) -- claim certain space, if sucessfully, return the path. 
   * Allow soft claim or hard claim (soft claim will be the default claim option)
      - ```SOFT```: check on the space currently available
      - ```HARD```: will try to evict from the temporal cache if the space left is not enough
   * The application can specify what algorithm to use for hard claim. 
* H5LSrelease_space(char \*path) -- release the space
* H5LSrelease_space_all() -- release all the space on the whole SSD.
All these functions will be defined in ```H5LS.c``` and ```H5LS.h```. 

#### File cache related functions (for read)
* H5Fcache_create -- create a cache in the system’s local storage
* H5Fcache_remove -- remove the cache associated with the file in the system's local storage (This will call H5LSremove_cache)
* H5Fset_cache_plist - set the file cache property list
  * Set the cache property (space, etc)
* H5Fget_cache_plist - get the cache property list
* H5Fquery_cache - querey information related with the cache from the property list (space, path, type of cache, purpose of cache, etc)
* H5Fclear_cache - clear all the cache on SSD, and then call H5LSrelease_space()

#### Dataset cache related functions (for read)
* H5Dcache_create -- reserve space for the data
* H5Dcache_remove -- clear the cache on the local storage related to the dataset

Besides these, we will also have the following two functions for prefetching / reading data from the cache
* H5Dprefetch -- prefetching the data from the file system and cache them to the local storage
* H5Dread_cache -- read data from the cache