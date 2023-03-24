### needs to be here otherwise the import fails
"""Modified transforms from Pangeo Forge"""

from dataclasses import dataclass, field
from typing import List, Dict, Union
from pangeo_forge_recipes.patterns import Dimension
from pangeo_forge_recipes.storage import FSSpecTarget
from pangeo_forge_recipes.transforms import DetermineSchema, XarraySchema, IndexItems, PrepareZarrTarget, StoreDatasetFragments

import apache_beam as beam
from pangeo_forge_recipes.transforms import OpenURLWithFSSpec, OpenWithXarray

def dynamic_target_chunks_from_schema(
    schema: XarraySchema, 
    target_chunk_nbytes: int = None,
    chunk_dim: str = None
) -> dict[str, int]:
    """Dynamically determine target_chunks from schema based on desired chunk size"""
    # convert schema to dataset
    from pangeo_forge_recipes.aggregation import schema_to_template_ds # weird but apparently necessary for dataflow
    ds = schema_to_template_ds(schema)
    
    # create full chunk dictionary for all other dimensions
    target_chunks = {k: len(ds[k]) for k in ds.dims if k != chunk_dim}
    
    # get size of dataset
    nbytes = ds.nbytes
    
    # get size of single chunk along `chunk_dim`
    nbytes_single = nbytes/len(ds[chunk_dim])
    
    if nbytes_single > target_chunk_nbytes:
        # if a single element chunk along `chunk_dim` is larger than the target, we have no other choice than exceeding that limit
        # Chunking along another dimension would work, but makes this way more complicated.
        # TODO: Should raise a warnign
        chunk_size = 1
        
    else:
        # determine chunksize (staying under the given limit)
        chunk_size = target_chunk_nbytes//nbytes_single
        
    target_chunks[chunk_dim] = chunk_size
    return {k:int(v) for k,v in target_chunks.items()} # make sure the values are integers, maybe this fixes the dataflow error

@dataclass
class StoreToZarr(beam.PTransform):
    """Store a PCollection of Xarray datasets to Zarr.
    :param combine_dims: The dimensions to combine
    :param target_root: Location the Zarr store will be created inside.
    :param store_name: Name for the Zarr store. It will be created with this name
                       under `target_root`.
    :param target_chunks: Dictionary mapping dimension names to chunks sizes.
        If a dimension is a not named, the chunks will be inferred from the data.
    """

    # TODO: make it so we don't have to explictly specify combine_dims
    # Could be inferred from the pattern instead
    combine_dims: List[Dimension]
    # target_root: Union[str, FSSpecTarget] # temp renamed (bug)
    target: Union[str, FSSpecTarget]
    # store_name: str
    target_chunk_nbytes : int
    chunk_dim : str
    target_chunks: Dict[str, int] = field(default_factory=dict)

    def expand(self, datasets: beam.PCollection) -> beam.PCollection:
        schema = datasets | DetermineSchema(combine_dims=self.combine_dims)
        self.target_chunks = schema | beam.Map(dynamic_target_chunks_from_schema, 
                                               target_chunk_nbytes=self.target_chunk_nbytes, 
                                               chunk_dim=self.chunk_dim)
        indexed_datasets = datasets | IndexItems(schema=schema)
        if isinstance(self.target, str):
            target = FSSpecTarget.from_url(self.target)
        else:
            target = self.target
        # full_target = target / self.store_name
        target_store = schema | PrepareZarrTarget(
            target=target, target_chunks=beam.pvalue.AsSingleton(self.target_chunks)
        )
        return indexed_datasets | StoreDatasetFragments(target_store=target_store)



# from transforms import StoreToZarrLegacyDynamic as StoreToZarr
from pangeo_forge_recipes.patterns import pattern_from_file_sequence
import apache_beam as beam
from pangeo_forge_recipes.transforms import OpenURLWithFSSpec, OpenWithXarray
from pyesgf.search import SearchConnection

iids = [
# 'CMIP6.CMIP.BCC.BCC-CSM2-MR.historical.r1i1p1f1.day.pr.gn.v20181126',
# 'CMIP6.CMIP.BCC.BCC-CSM2-MR.historical.r1i1p1f1.day.sfcWind.gn.v20181126',
'CMIP6.ScenarioMIP.MRI.MRI-ESM2-0.ssp585.r2i1p1f1.day.sfcWind.gn.v20210907',
# 'CMIP6.ScenarioMIP.MRI.MRI-ESM2-0.ssp585.r3i1p1f1.day.sfcWind.gn.v20210907',
# 'CMIP6.ScenarioMIP.MRI.MRI-ESM2-0.ssp585.r4i1p1f1.day.sfcWind.gn.v20210907',
# 'CMIP6.ScenarioMIP.MRI.MRI-ESM2-0.ssp585.r5i1p1f1.day.sfcWind.gn.v20210907',
'CMIP6.ScenarioMIP.MRI.MRI-ESM2-0.ssp585.r2i1p1f1.day.psl.gn.v20210907',
# 'CMIP6.ScenarioMIP.MRI.MRI-ESM2-0.ssp585.r3i1p1f1.day.psl.gn.v20210907',
# 'CMIP6.ScenarioMIP.MRI.MRI-ESM2-0.ssp585.r4i1p1f1.day.psl.gn.v20210907',
# 'CMIP6.ScenarioMIP.MRI.MRI-ESM2-0.ssp585.r5i1p1f1.day.psl.gn.v20210907',
# 'CMIP6.ScenarioMIP.MIROC.MIROC6.ssp585.r2i1p1f1.day.psl.gn.v20200623',
# 'CMIP6.ScenarioMIP.MIROC.MIROC6.ssp585.r3i1p1f1.day.psl.gn.v20200623', 
'CMIP6.ScenarioMIP.MIROC.MIROC6.ssp585.r4i1p1f1.day.psl.gn.v20200623', 
# 'CMIP6.ScenarioMIP.MIROC.MIROC6.ssp585.r5i1p1f1.day.psl.gn.v20200623', 
# 'CMIP6.ScenarioMIP.EC-Earth-Consortium.EC-Earth3.ssp585.r6i1p1f1.day.sfcWind.gr.v20200201', 
# 'CMIP6.ScenarioMIP.EC-Earth-Consortium.EC-Earth3.ssp585.r9i1p1f1.day.sfcWind.gr.v20200201', 
# 'CMIP6.ScenarioMIP.EC-Earth-Consortium.EC-Earth3.ssp585.r11i1p1f1.day.sfcWind.gr.v20200201', 
'CMIP6.ScenarioMIP.MOHC.HadGEM3-GC31-MM.ssp585.r2i1p1f3.day.psl.gn.v20200515',
# 'CMIP6.ScenarioMIP.MOHC.HadGEM3-GC31-MM.ssp585.r3i1p1f3.day.psl.gn.v20200507',
# try a big dataset
'CMIP6.CMIP.NOAA-GFDL.GFDL-CM4.historical.r1i1p1f1.Omon.thetao.gn.v20180701',
]


## Query ESGF for the urls
iid_schema = 'mip_era.activity_id.institution_id.source_id.experiment_id.member_id.table_id.variable_id.grid_label.version'

conn = SearchConnection(
    "https://esgf-node.llnl.gov/esg-search",
    distrib=True
)
recipe_input_dict = {}
for iid in iids:
    context_kwargs = {'replica':None,'facets':['doi']} # this assumes that I can use replicas just as master records. I think that is fine
    for label, value in zip(iid_schema.split('.'), iid.split('.')):
        context_kwargs[label] = value
        
    # is this a problem with the `v...` in version?
    context_kwargs['version'] = context_kwargs['version'].replace('v','')
        
    # testing
    # del context_kwargs['version']
    ctx = conn.new_context(**context_kwargs)
    print(f"{iid}: Found {ctx.hit_count} hits")
    
    results = ctx.search() # these might include several data nodes (curiously even if I set replica to false?)
    
    if len(results)<1:
        print(f'Nothing found for {iid}. Skipping.')
    else:
        # for now take the first one that has any urls at all
        for ri,result in enumerate(results):
            print(f"{iid}-{result.dataset_id}: Extracting URLS")
            urls = [f.download_url for f in result.file_context().search()] # this raises an annoying warning each time. FIXME
            if len(urls)>0:
                recipe_input_dict[iid] = {}
                recipe_input_dict[iid]['urls'] = urls
                # populate this to pass to the database later
                recipe_input_dict[iid]['instance_id'],recipe_input_dict[iid]['data_node'] = result.dataset_id.split('|')
                break

# create recipe dictionary
target_chunk_nbytes = int(100e6)
recipes = {}

for iid, input_dict in recipe_input_dict.items():
    input_urls = input_dict['urls']

    pattern = pattern_from_file_sequence(input_urls, concat_dim='time')
    transforms = (
        beam.Create(pattern.items())
        | OpenURLWithFSSpec()
        | OpenWithXarray() # do not specify file type to accomdate both ncdf3 and ncdf4
        | StoreToZarr(
            # store_name=f"{iid}.zarr",
            combine_dims=pattern.combine_dim_keys,
            target_chunk_nbytes=target_chunk_nbytes,
            chunk_dim=pattern.concat_dims[0] # not sure if this is better than hardcoding?
        )
    )
    recipes[iid] = transforms
