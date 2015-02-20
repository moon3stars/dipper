#!/usr/bin/env python3

#first-pass with dipper
#this will eventually control the processing of data sources
__author__ = 'nlw'

import argparse
import logging

from sources.HPOAnnotations import HPOAnnotations
from sources.ZFIN import ZFIN
from sources.OMIM import OMIM
from sources.BioGrid import BioGrid
from sources.MGI import MGI
from sources.IMPC import IMPC
from sources.Panther import Panther
from sources.NCBIGene import NCBIGene
from sources.UCSCBands import UCSCBands
from sources.CTD import CTD
from sources.GeneReviews import GeneReviews
from sources.EOM import EOM
from sources.Coriell import Coriell
from utils.TestUtils import TestUtils


def main():
    source_to_class_map={
        'hpoa' : HPOAnnotations, # ~3 min
        'zfin' : ZFIN,
        'omim' : OMIM,  #full file takes ~15 min, due to required throttling
        'biogrid' : BioGrid,  #interactions file takes <10 minutes
        'mgi' : MGI,
        'impc' : IMPC,  # Running time to process all three data files is ~85 minutes so far.
        'panther' : Panther,  #this takes a very long time, ~1hr to map 7 species-worth of associations
        'ncbigene' : NCBIGene,  #takes about 4 minutes to process 2 species
        'ucscbands' : UCSCBands,
        'ctd' : CTD,
        'genereviews' : GeneReviews,
        'eom' : EOM,  # Takes about 5 seconds.
        'coriell' : Coriell
    }

    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description='Dipper: Data Ingestion'
                                                 ' Pipeline for SciGraph')
    parser.add_argument('-s', '--sources', type=str, required=True,
                        help='comma separated list of sources')
    parser.add_argument('-l', '--limit', type=int, help='limit number of rows')
    parser.add_argument('--parse_only', action='store_true',
                        help='parse files without writing')
    parser.add_argument('-f', '--force', action='store_true',
                        help='force re-download of files')
    parser.add_argument('--no_verify',help='ignore the verification step',
                        action='store_true')
    parser.add_argument('--query',help='enter in a sparql query',type=str)
    parser.add_argument('-q', '--quiet',help='turn off info logging',
                        action="store_true")
    args = parser.parse_args()

    if args.quiet:
        logging.basicConfig(level=logging.WARNING)
    else:
        logging.basicConfig(level=logging.DEBUG)

    if args.query is not None:
        for source in args.sources.split(','):
            source = source.lower()
            mysource = source_to_class_map[source]()
            test_query = TestUtils(mysource)
            test_query.check_query_syntax(args.query)
            test_query.load_graph_from_turtle()
            test_query.query_graph(args.query)
            exit(0)

    #iterate through all the sources
    for source in args.sources.split(','):
        print()
        print("*******", source, "*******")
        source = source.lower()
        mysource = source_to_class_map[source]()
        if args.parse_only is False:
            mysource.fetch(args.force)
        mysource.parse(args.limit)
        mysource.write(format='turtle')
        if args.no_verify is not True:
            status = mysource.verify()
            if status is not True:
                print('ERROR: Source',source,'did not pass verification tests.')
                exit(0)  #exit with a bad code
        else:
            print('INFO: skipping verification step')
        print('***** Finished with',source,'*****')
    #load configuration parameters
    #for example, keys

    print("All done.")

if __name__ == "__main__":
    main()

###########################
