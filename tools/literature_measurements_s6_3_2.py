"""Reproduce visually checked factual measurements, not copyrighted article text."""
import argparse
from pathlib import Path
from analyze_s6_3_1 import emit

BASE=Path(__file__).resolve().parents[1]/'experiments/s6_3_2'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    # B06 Table 2, p169. Entries: actual C, mean d, reported error d, individuals.
    data={
      ('Borisovka','egg'):[(17.1,53.7,.26,31),(20.7,25.3,.24,72),(22.8,20.7,.09,86),(24.7,16.7,.07,138),(26.8,14.7,.08,115)],
      ('Borisovka','larva'):[(20.6,21.1,.50,32),(23,13.5,.13,77),(24.8,10.2,.09,127),(27,8.7,.07,133)],
      ('Borisovka','prepupa_pupa'):[(20.2,24.5,.67,32),(22,20.4,.13,66),(25.4,14.5,.08,112),(27.2,12.5,.07,104)],
      ('Borisovka','total'):[(20.5,70.5,1.76,7),(22.6,54.4,.19,57),(25,41.1,.14,110),(27,35.7,.12,99)],
      ('St_Petersburg','egg'):[(17.1,53.4,.19,43),(20.7,24.9,.13,112),(22.8,19.9,.12,96),(24.7,15.7,.08,130),(26.8,14.1,.07,136)],
      ('St_Petersburg','larva'):[(20.6,23.3,1.53,11),(22.2,15.8,.19,84),(24.8,10.6,.09,114),(27,8.4,.06,137)],
      ('St_Petersburg','prepupa_pupa'):[(20.2,26,2,2),(22.8,18.3,.17,77),(25.4,13.6,.09,109),(27.2,12.3,.06,127)],
      ('St_Petersburg','total'):[(20.5,71,1,2),(22.6,53.8,.30,59),(25,39.9,.16,104),(27,34.8,.09,113)],
    }
    rows=[]
    for (population,stage),values in data.items():
        for temperature,mean,error,n in values:
            rows.append(dict(reference='B06',doi='10.1023/B:JOEY.0000033808.45455.75',locator='Table 2 p169',species='Lasius niger',population=population,endpoint=stage,temperature_c=temperature,unit='days',mean=mean,dispersion=error,dispersion_type='reported error; not relabelled SD/SE/CI',individual_n=n,conditions='First brood; unfed queens with water; individuals nested within queens',evidence_grade='A',status='OBSERVED_MEAN'))
        if stage!='egg':
            rows.append(dict(reference='B06',doi='10.1023/B:JOEY.0000033808.45455.75',locator='Table 2 p169 and Results',species='Lasius niger',population=population,endpoint=stage,temperature_c=17,unit='days',mean='',dispersion='',dispersion_type='NOT AVAILABLE',individual_n='',conditions='Cold treatment; larval diapause; no completed worker development',evidence_grade='A',status='NO_COMPLETED_ENDPOINT; not zero'))
    emit(BASE/'literature_measurements.csv',rows,args.check)
    print(f'B06: {len(rows)} observed or explicitly unavailable endpoints; no inferred confidence intervals')
if __name__=='__main__':main()
