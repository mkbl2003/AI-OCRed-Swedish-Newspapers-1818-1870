import glob
import re
from collections import defaultdict
from collections import Counter
import ast
def total_results():
    filenames = glob.glob('final_*_ocr.txt') # change the path accordingly
    total_dict = defaultdict(float)
    counter_dict = defaultdict(Counter)
    with open('totals_ocr2.txt', 'w', newline='', encoding='utf-8') as fout: # change the pathname as you wish
        for filename in filenames:
            print(filename)
            linelist = []
            found = False
            with open(filename, 'r', newline='', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if 'Hallucination' in line:
                        break
                    # i > 15:
                    # if not found:
                    #    if 'Hallucination' in line:
                    #        found = True
                    #    continue
                    if i < 15:
                        line = line.strip('\n')
                        line = re.sub(r'^ ', '', line)
                        line = re.sub(r' $', '', line)
                        line = re.sub(r' \r', '', line)
                        line = re.sub(r'unaligned gt whitespaces', 'unaligned_gt_whitespaces', line)
                        line = re.sub(r'unaligned ocr whitespaces', 'unaligned_ocr_whitespaces', line)
                        line = re.sub(r'aligned whitespaces', 'aligned_whitespaces', line)
                        linelist.append(line)
            # fout.write(f'{filename}\n')
            for l in linelist:
                # print(l)
                # fout.write(f'{l}\n')
                ll = re.search(r'^(\w+) (.*)$', l)
                if ll == None:
                    continue
                else:
                   if ll.group(1) not in ('wer', 'cer'):
                    total_dict[ll.group(1)] += float(ll.group(2))

        total_dict['cer'] = total_dict['total_chrerrs'] / total_dict['total_chrs']
        total_dict['wer'] = total_dict['total_wrderrs'] / total_dict['total_wrds']
        for k,v in total_dict.items():
            fout.write(f'{k} {v}\n')
        return total_dict

def total_results_counter():
     filenames = glob.glob('final_*_ocr.txt')   # adjust as needed
 
     counter_dict = defaultdict(Counter)
 
     with open('totals_ocr2_counter_test.txt', 'w', newline='', encoding='utf-8') as fout: # change filename as needed
 
         for filename in filenames:
             print(filename)
             linelist = []
 
             with open(filename, 'r', newline='', encoding='utf-8') as f:
                 for i, line in enumerate(f):
 
                     # stop early if marker is found
                     if 'Hallucination' in line:
                         break
 
                     # process ONLY lines AFTER line 15
                     if i <= 15:
                         continue
 
                     line = line.strip()
                     line = re.sub(r'unaligned gt whitespaces', 'unaligned_gt_whitespaces', line)
                     line = re.sub(r'unaligned ocr whitespaces', 'unaligned_ocr_whitespaces', line)
                     line = re.sub(r'aligned whitespaces', 'aligned_whitespaces', line)
 
                     linelist.append(line)
 
             # parse lines
             for l in linelist:
                 ll = re.search(r'^(\S+)\s+(.*)$', l)
                 if not ll:
                     continue
 
                 key = ll.group(1)
                 val = ll.group(2)
 
                 # Properly extract content inside Counter(...)
                 m = re.match(r'Counter\((.*)\)$', val)
                 if not m:
                     continue  # malformed Counter line
 
                 try:
                     inner_dict = ast.literal_eval(m.group(1))
                 except Exception as e:
                     print(f"WARNING: failed to parse Counter in line: '{l}'")
                     continue
 
                 counter_dict[key] += Counter(inner_dict)
 
         # write final totals to output file
         for k, v in counter_dict.items():
             fout.write(f'{k} {v}\n')
 
     return counter_dict
    
def total_results_hallucinations():
    filenames = glob.glob('final_*_ocr.txt') # change as needed
    total_dict = defaultdict(float)
    counter_dict = defaultdict(Counter)
    n = 0
    
    with open('totals_ocr2_hallucinations_test.txt', 'w', encoding='utf-8') as fout: # adjust as needed
        for filename in filenames:
            print(filename)
            linelist = []
            found = False
    
            with open(filename, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
    
                    if i > 15:
                        if not found:
                            if 'Hallucination' in line:
                                found = True
                            continue
    
                        line = line.strip('\n')
                        line = re.sub(r'^ ', '', line)
                        line = re.sub(r' $', '', line)
                        line = re.sub(r' \r', '', line)
                        line = re.sub(r'unaligned gt whitespaces', 'unaligned_gt_whitespaces', line)
                        line = re.sub(r'unaligned ocr whitespaces', 'unaligned_ocr_whitespaces', line)
                        line = re.sub(r'aligned whitespaces', 'aligned_whitespaces', line)
                        linelist.append(line)
    
            fout.write(f'{filename}\n')
            for l in linelist:
                fout.write(f'{l}\n')
                if 'bib' in l:
                    print(l)
                    n += 1
    
    return n
            
