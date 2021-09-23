Best Practices
===================================
The HDF5 Cache I/O VOL connector (Cache VOL) allows applications to partially hide the I/O time from the computation. Here we provide more information on how applications can take advantage of it.

-----------------------
Write workloads
-----------------------

1) MPI Thread multiple should be enabled for optimal performance;
2) There should be enough compute work after the H5Dwrite calls to overlap with the data migration from the fast storage layer to the parallel file system;
3) The compute work should be inserted in between H5Dwrite and H5Dclose. For iterative checkpointing workloads, one can postpone the dataset close and group close calls after next iteration of compute. 
4) If there are multiple H5Dwrite calls issued consecutatively, one should pause the async excution first and then restart the async execution after all the H5Dwrite calls were issued.
5) For check pointing workloads, it is better to open / close the file only once to avoid unnecessary overhead on setting and removing file caches. 

An application may have the following HDF5 operations to write check point data:

.. code-block::

    // Synchronous file create at the beginning 
    fid = H5Fcreate(...);
    for (int iter=0; iter<niter; iter++) {
        // compute work
	...
        // Synchronous group create
        gid = H5Gcreate(fid, ...);
	// Synchronous dataset create
	did1 = H5Dcreate(gid, ..);
	did2 = H5Dcreate(gid, ..);
        // Synchronous dataset write
        status = H5Dwrite(did1, ..);
        // Synchronous dataset write again
        status = H5Dwrite(did2, ..);
        // close dataset
        err = H5Dclose(did1, ..);
        err = H5Dclose(did2, ..);
        // close group
        err = H5Gclose(gid, ..)
    }

    H5Fclose(fid);
    // Continue to computation

which can be converted to use async VOL as the following:

.. code-block::

       // Synchronous file create at the beginning 
    fid = H5Fcreate(...);
    for (int iter=0; iter<niter; iter++) {
        // compute work
	...
	// close the datasets & group after the next round of compute 
	if (iter > 0) {
	   H5Dclose(did1);
	   H5Dclose(did2);
	   H5Gclose(gid);
        }
        // Synchronous group create
        gid = H5Gcreate(fid, ...);
	// Synchronous dataset create
	did1 = H5Dcreate(gid, ..);
	did2 = H5Dcreate(gid, ..);
        // Synchronous dataset write
	// Pause data migration before issuing H5Dwrite calls
	H5Fcache_async_op_pause(fid);
        status = H5Dwrite(did1, ..);
        // Synchronous dataset write again
        status = H5Dwrite(did2, ..);
	// Start the data migration
	H5Fcache_async_op_start(fid);
        // close dataset
	if (iter==niter-1) {
	   err = H5Dclose(did1, ..);
           err = H5Dclose(did2, ..);
           // close group
           err = H5Gclose(gid, ..)
	}
    }

    H5Fclose(fid);


-------------------
Read workloads
-------------------
Currently, Cache VOL works best for repeatedly read workloads.

1) The dataset can be one or multiple dimensional arrays. However, for multiple dimensional arrays, each read must select complete sampoles, i.e., the hyperslab selection must be of the shape: [i:j, :, :, : ..., :]. The sample list does not have to be contiguous.
2) If the dataset is relatively small, one could call H5Dprefetch to prefetch the entire dataset to the fast storage. H5Dprefetch will be asynchronously. H5Dread will then wait until the asynchronous prefetch is done.
3) If the dataset is large, one could just call H5Dread as usually, the library will then cache the data to the fast storage layer on the fly.
4) During the whole period of read, one should avoid opening and closing the dataset multiple times. For h5py workloads, one should avoid referencing datasets multiple times. 