"""Read verified CC0 Dryad spreadsheets; never modify or publish source PDFs.

Optional acquisition step only. The atlas builder consumes the resulting CSVs
with stdlib, so clean CI does not require Excel or openpyxl.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'research/s6_3_2_1/raw'
SPECS=[
 ('N07','k98sf7m8n','Raw_data_Baumgart_et_al.xlsx','757db8909ac3ff79ff5e69a78c823b8552ce9278be3aea3e9a1c88b7002cb121','survival','N07_survival.csv',
  ['IndividualLabel','Colony','SpeciesCode','AcclimationC','TestTemperatureC','TestBatch','ObservedDeathHour','RawStatus','EarlyDeathAssumedHour1','EarlyDeathAssumedBeforeFirstObservation']),
 ('N10','931zcrk1q','data_ctmin.xlsx','4f59a5b29fd71d62f7b1482e91aed62d29ad4d2dc6c467f31c909f2c07cb4c03','CTmin','N10_ctmin.csv',
  ['Species','AcclimationC','ColonyDormancy','CTminC']),
 ('N10','931zcrk1q','data_lte50.xlsx','e5fd43bc7b2ad354c64172116e88d6da205b6df90d462ba26ea3f5b1e76e1565','Lte50','N10_lte50.csv',
  ['Species','AcclimationC','ColonyDormancy','LTe50C','Lower95CI_C','Upper95CI_C']),
 ('N10','931zcrk1q','data_smr.xlsx','08c9e92603514816575ec9a8c92058f29f39565cf8a9d393c64f8d9a62b67b2e','SMR','N10_smr.csv',
  ['Species','Replicate','ColonyDormancy','SMR_uL_CO2_per_h_per_mg']),
 ('N10','931zcrk1q','data_Condition_means_ctmin_lte50.xlsx','2ee83d07cca298e29a6c67ae09be53b585cdb5a64b5e02a6c77a9cefe87689c8','Mean CTmin and Lte50 estimates1','N10_condition_means.csv',
  ['Species','AcclimationC','ColonyDormancy','MeanCTminC','LTe50C'])]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('downloads',type=Path);args=parser.parse_args()
    import openpyxl  # read_only/data_only; no workbook authoring or recalculation
    DEST.mkdir(parents=True,exist_ok=True); manifest=[]
    for source,doi_suffix,filename,sha,sheet_name,output,headers in SPECS:
        archives=list(args.downloads.glob('*'+doi_suffix+'*.zip'))
        assert len(archives)==1,(doi_suffix,archives)
        with ZipFile(archives[0]) as archive: data=archive.read(filename)
        assert hashlib.sha256(data).hexdigest()==sha,filename
        workbook=openpyxl.load_workbook(io.BytesIO(data),read_only=True,data_only=True)
        sheet=workbook[sheet_name]; rows=list(sheet.iter_rows(values_only=True)); workbook.close()
        assert len(rows[0])==len(headers),(filename,rows[0])
        stream=io.StringIO(newline=''); writer=csv.writer(stream,lineterminator='\n')
        writer.writerow(['SourceRow',*headers])
        for i,row in enumerate(rows[1:],2):
            assert len(row)==len(headers)
            writer.writerow([i,*['NOT_RECORDED' if value is None else value for value in row]])
        text=stream.getvalue();(DEST/output).write_text(text,encoding='utf-8',newline='')
        manifest.append(dict(SourceId=source,DatasetDOI='10.5061/dryad.'+doi_suffix,SourceFile=filename,SourceSHA256=sha,SourceSheet=sheet_name,OriginalHeaders=list(rows[0]),AtlasHeaders=headers,CSV=output,CSVNormalizedSHA256=hashlib.sha256(text.encode()).hexdigest(),Rows=len(rows)-1,License='CC0-1.0',Transform='Only English column labels and explicit SourceRow added; numeric cells and source missing/status codes preserved; no fitting'))
    (DEST/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
    print('WROTE',len(manifest),'licensed factual tables;',sum(x['Rows'] for x in manifest),'rows')


if __name__=='__main__':main()
