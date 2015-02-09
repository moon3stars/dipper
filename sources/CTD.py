import csv
import re
import gzip
from sources.Source import Source
from models.Dataset import Dataset
from models.Chem2DiseaseAssoc import Chem2DiseaseAssoc


class CTD(Source):

    files = {
        'interactions': {'file': 'CTD_chemicals_diseases.tsv.gz',
                         'url': 'http://ctdbase.org/reports/CTD_chemicals_diseases.tsv.gz'}
    }
    static_files = {
        'publications': {'file': 'CTD_curated_references.tsv.gz'}
    }

    def __init__(self):
        Source.__init__(self, 'ctd')
        self.load_bindings()
        self.dataset = Dataset('ctd', 'CTD', 'http://ctdbase.org')

    def fetch(self, is_dl_forced):
        """
        :return: None
        """
        self.get_files(is_dl_forced)
        return

    def parse(self, limit=None):
        """
        Parses version and interaction information from CTD
        :param limit limit the number of rows processed
        :return:None
        """
        if limit is not None:
            print("Only parsing first", limit, "rows")

        print("Parsing files...")
        pub_map = self._parse_publication_file(
            limit, self.static_files['publications']['file']
        )
        self._parse_interactions_file(limit, self.files['interactions']['file'],
                                      pub_map)
        #TODO return md5sum of files?
        print("Done parsing files.")

        return

    def _parse_interactions_file(self, limit, file, pub_map):
        row_count = 0
        version_pattern = re.compile('^# Report created: (.+)$')
        is_versioned = False
        file_path = '/'.join((self.rawdir, file))
        with gzip.open(file_path, 'rt') as tsvfile:
            reader = csv.reader(tsvfile, delimiter="\t")
            for row in reader:
                # Scan the header lines until we get the version
                # There is no official version sp we are using
                # the upload timestamp instead
                if is_versioned is False:
                    match = re.match(version_pattern, ' '.join(row))
                    if match:
                        version = re.sub(r'\s|:', '-', match.group(1))
                        self.dataset.setVersion(version)
                        is_versioned = True
                elif re.match('^#', ' '.join(row)):
                    next
                else:
                    # only get direct associations
                    if row[5] != '':
                        # Process data here
                        self._process_interactions(row, pub_map)
                    row_count += 1
                    if limit is not None and row_count >= limit:
                        break
        return

    def _process_interactions(self, row, pub_map):
        """
        :param row
        :param pub_map
        :return:None
        """
        self._check_list_len(row, 10)
        (chem_name, chem_id, cas_rn, disease_name, disease_id, direct_evidence,
         inferred_gene_symbol, inference_score, omim_ids, pubmed_ids) = row
        evidence_pattern = re.compile('^therapeutic|marker\/mechanism$')
        dual_evidence = re.compile('^marker\/mechanism\|therapeutic$')

        if re.match(evidence_pattern, direct_evidence):
            reference_list = self._process_pubmed_ids(pubmed_ids)
            self._make_association(chem_id, disease_id, direct_evidence, reference_list)
        elif re.match(dual_evidence, direct_evidence):
            reference_list = self._process_pubmed_ids(pubmed_ids)
            pub_evidence_map = \
                self._split_pub_ids_by_evidence(
                    reference_list, disease_id, chem_id, pub_map
                )
            for val in direct_evidence.split('|'):
                self._make_association(chem_id, disease_id, val, pub_evidence_map[val])

        return

    def _make_association(self, chem_id, disease_id, direct_evidence, pubmed_ids):
        """
        :param chem_id
        :param disease_id
        :param direct_evidence
        :param pubmed_ids
        :return:None
        """
        assoc_id = self.make_id('ctd' + chem_id + disease_id + direct_evidence)
        evidence_code = self._set_evidence_code(direct_evidence)
        chem_mesh_id = 'MESH:'+chem_id

        assoc = Chem2DiseaseAssoc(assoc_id, chem_mesh_id, disease_id,
                                  pubmed_ids, evidence_code)
        assoc.loadObjectProperties(self.graph)
        assoc.addAssociationNodeToGraph(self.graph)
        return

    def _process_pubmed_ids(self, pubmed_ids):
        """
        :param pubmed_ids -  string representing publication
                           ids seperated by a | symbol
        :return: list of ids with the PUBMED prefix
        """
        id_list = pubmed_ids.split('|')
        for (i, val) in enumerate(id_list):
            id_list[i] = 'PMID:'+val
        return id_list

    def _set_evidence_code(self, evidence):
        """
        :param evidence
        :return: ECO evidence code
        """
        ECO_MAP = {
            'therapeutic': 'ECO:0000269',
            'marker/mechanism': 'ECO:0000306'
        }
        return ECO_MAP[evidence]

    def _split_pub_ids_by_evidence(self, pub_ids, disease_id, chem_id, pub_map):
        """
        :param pub_ids:
        :param disease_id:
        :param chem_id:
        :param pub_map:
        :return: dict
        """
        publication = {'therapeutic':[], 'marker/mechanism': []}
        for val in pub_ids:
            key = disease_id+'-'+chem_id+'-'+val
            if pub_map.get(key):
                publication[pub_map[key]].append(val)
            else:
                raise Exception("Could not disambiguate publication "
                                "for disease id: " + disease_id +
                                "\nchemical id: " + chem_id +
                                "\npublication id: " + val)

        return publication

    def _parse_publication_file(self, limit, file):
        """
        :param limit:
        :param file:
        :return: dict
        """
        row_count = 0
        pub_map = dict()
        file_path = '/'.join((self.rawdir, file))
        with gzip.open(file_path, 'rt') as tsvfile:
            reader = csv.reader(tsvfile, delimiter="\t")
            for row in reader:
                self._check_list_len(row, 10)
                # catch comment lines
                if re.match('^#', ' '.join(row)):
                    next
                else:
                    (pub_id, disease_label, disease_id, disease_cat, evidence,
                     chem_label, chem_id, cas_rn, gene_symbol, gene_acc) = row
                    key = disease_id+'-'+chem_id+'-PMID:'+pub_id
                    if chem_id is '' or disease_id is '':
                        next
                    elif pub_map.get(key) is not None:
                        raise Exception("Ambiguous publication mapping for"
                                        " key: "+key+"\n"
                                        "This is not yet handled by Dipper")
                    else:
                        pub_map[key] = evidence
                    row_count += 1
                    if limit is not None and row_count >= limit:
                        break

        return pub_map