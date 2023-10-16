import pandas as pd
import re, json, argparse



parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('--outdir', help='')
parser.add_argument('--kingdom', help='', choices=["d__Bacteria", 'k__Fungi'])
parser.add_argument('--dna-sequences', help='')
parser.add_argument('--pathdb-phylo', help='')
parser.add_argument('--pathdb-taxo', help='')
parser.add_argument('--taxonomy', help='')
parser.add_argument('--table', help='')

args = parser.parse_args()

kingdom = args.kingdom
reps_seq_all = args.dna_sequences
PathDB_seqs_phylo = args.pathdb_phylo
taxo_all_tsv = args.taxonomy
table_all = args.table
output_path = args.outdir
pathdb_taxo = args.pathdb_taxo

tsep = "; "
taxo_db_name = 'Silva'

if kingdom == "k__Fungi":
    taxo_db_name = 'Unite'
    tsep = ';'

# importation des repSeqs
repSeqPathSilva = dict()
seq_id = ""
for line in open(reps_seq_all, "r"):
    line = line.strip("\n")
    if line[0] == ">":
        seq_id = line[1:]
    elif len(line) > 1: repSeqPathSilva[seq_id] = line

# Importation des taxonomies de reference
genus_taxo = ",".join(open(pathdb_taxo, "r").readlines())

def ispatho(taxo):
    if len(taxo.split(tsep)) == 7:
        if not re.search(taxo.split(tsep)[-2], genus_taxo):
            return "no"
        else: return "yes"
    elif not re.search(taxo.split(tsep)[-1], genus_taxo):
        return "no"
    else: return "yes"

def complete_taxo(taxo):
    unidentified = ['k__unidentified', 'p__unidentified', 'c__unidentified', 'o__unidentified', 'f__unidentified', 'g__unidentified', 's__unidentified']
    taxo = "; ".join(taxo.split(tsep))
    if len(taxo.split())<7:
        l = -(7-len(taxo.split()))
        taxo += "; " 
        taxo += "; ".join(unidentified[l:])
    return taxo

taxoSilva = pd.read_csv(taxo_all_tsv, sep="\t", index_col="Feature ID")
taxoSilva['isPatho'] = [ispatho(taxo) for taxo in taxoSilva['Taxon']]
taxoSilva['Taxon'] = [complete_taxo(taxo) for taxo in taxoSilva['Taxon']]

# Importation de la table de reads
readsTable = pd.read_csv(table_all, header=1, sep="\t", index_col="#OTU ID")

# Suppression des séquences hors kingdom
for row in taxoSilva.index:
    if not re.search(kingdom, taxoSilva.at[row, "Taxon"]):
        taxoSilva.drop([row], inplace=True)
        readsTable.drop([row], inplace=True)
        repSeqPathSilva.pop(row)
repSeqPathSilva = {b:a for a,b in repSeqPathSilva.items()}

# Importation de PathDB
pathDB_dict = dict()
for line in open(PathDB_seqs_phylo, "r"):
    line = line.strip("\n")
    if line[0] == ">":
        seq_id = line[1:]
    elif len(line) > 1:
        pathDB_dict[line] = seq_id

# Alignement PathDB et repSeq
taxoPathDB = dict()
for seq in repSeqPathSilva:
    if seq in pathDB_dict:
        taxoPathDB[repSeqPathSilva[seq]] = pathDB_dict[seq]

# creation de la Dataframe Pandas
data = dict()
for sample in readsTable.columns:
    data[sample] = pd.DataFrame(readsTable[sample])
    data[sample] = data[sample].rename(columns={sample: "Reads Count"})
    data[sample]["Relative Abundance"] = [i/data[sample]["Reads Count"].sum() for i in data[sample]["Reads Count"]]
    data[sample][f"{taxo_db_name} Taxonomy"] = [taxoSilva.at[i, "Taxon"] for i in data[sample].index]
    data[sample][f"{taxo_db_name} Confidence"] = [taxoSilva.at[i, "Confidence"] for i in data[sample].index]
    data[sample]["isPatho"] = [taxoSilva.at[i, "isPatho"] for i in data[sample].index]
    PathDBTaxo = list()
    for i in data[sample].index:
        if i in taxoPathDB:
            PathDBTaxo.append(taxoPathDB[i])
        else: PathDBTaxo.append("unidentified")
    data[sample]["PathDB Taxonomy"] = PathDBTaxo
    
    # Filtre des null
    for row in data[sample].index:
        if data[sample].at[row, "Reads Count"] == 0:
            data[sample].drop([row], inplace=True)

    # # Export du JSON
    # result = data[sample].to_json(orient="index")
    # parsed = json.loads(result)
    # with open(f"{output_path}/results.json", 'w') as outfile:
    #     json.dump(parsed, outfile, indent=4)

    # Export du CSV
    data[sample].to_csv(f"{output_path}/results.csv", sep=",") # ajouter avant results {sample}-
