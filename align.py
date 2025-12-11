#!/usr/bin/env python
# encoding: utf8

# Aligns OCR output with a gold standard text, inserting linebreaks
# and hyphenatation into the gold standard if needed.
#
# The switches
#   -sb (strip beginning) and
#   -se (strip end),
# allow stripping lines at the beginning resp the end of the OCR
# text. NB! The amount of stripped material may vary with the quality
# of the alignment, so use with some care.
#
# A mismatching aligned character counts as a character error (with
# exceptions for newlines and hyphens), a word containing a character
# error -- including a misaligned whitespace marking the end of the
# word -- counts as a word error. Total character and word counts are
# based on the manual string. This means that if the ocr string
# contains many characters without counterparts in the manual string,
# the error rates may be more than 100%.
#


punct = ('.',',','!','?',':',';','\'','"','-','/')

from collections import defaultdict, Counter
import sys
import codecs
import csv
import re
import os

def remove_tags(word):
  cleanr = re.compile('<.*?>')
  cleantext = re.sub(cleanr, '', word)
  return cleantext

def worderrors(ocrdrec,mandrec):

#    print ocrdrec
#    print mandrec

    def ocrdwordgenerator(ocrd):
        ocrdlines = ocrd.split('\n')
        halfword = ''
        for l in ocrdlines:
            l = l.strip()
            if not l:
                continue

            words = l.replace('\t',' ').split(' ')
            words[0] = halfword+'\n'+words[0]
            if (words[-1].endswith('-') or words[-1].endswith('\xad')) and len(words[-1])>1:
                halfword = words[-1]
                del words[-1]
            else:
                halfword = ''

            for w in words:
                yield w

    mandwords = [w for w in ''.join(mandrec).replace('\t',' ').replace('\n',' ').replace('\u00ad','-').split() if w]
    ocrdwords = [w for w in ocrdwordgenerator(''.join(ocrdrec))]

    x = len(ocrdwords)+1
    y = len(mandwords)+1
    Tot = [0 for _ in range(x*y)]
    Noo = [0 for _ in range(x*y)]
    Sub = [0 for _ in range(x*y)]
    Ins = [0 for _ in range(x*y)]
    Del = [0 for _ in range(x*y)]

#    print ocrdwords
#    print mandwords

    for i in range(1,x):
        Del[i] = Del[i-1]+1
        Tot[i] = Tot[i-1]+1

    for j in range(1,y):
        Ins[x*j] = Ins[x*(j-1)]+1
        Tot[x*j] = Tot[x*(j-1)]+1

    for j in range(1,y):
        for i in range(1,x):
            mandword = mandwords[j-1]
            ocrdword = ocrdwords[i-1]

            if mandword == ocrdword or mandword == ocrdword.replace('-\n','') or mandword == ocrdword.replace('\xad\n','') or mandword == ocrdword.replace('\n',''):
                ntot = Tot[(i-1)+x*(j-1)]
                nnoo = Noo[(i-1)+x*(j-1)]+1
                nsub = Sub[(i-1)+x*(j-1)]
                nins = Ins[(i-1)+x*(j-1)]
                ndel = Del[(i-1)+x*(j-1)]
            else:
                ntot = Tot[(i-1)+x*(j-1)]+1
                nnoo = Noo[(i-1)+x*(j-1)]
                nsub = Sub[(i-1)+x*(j-1)]+1
                nins = Ins[(i-1)+x*(j-1)]
                ndel = Del[(i-1)+x*(j-1)]

            # inserts
            down = Tot[i+x*(j-1)]+1
            if down < ntot:
                ntot = down
                nnoo = Noo[i+x*(j-1)]
                nsub = Sub[i+x*(j-1)]
                nins = Ins[i+x*(j-1)]
                ndel = Del[i+x*(j-1)]+1

            # deletes
            rght = Tot[(i-1)+x*j]+1
            if rght < ntot:
                ntot = rght
                nnoo = Noo[(i-1)+x*j]
                nsub = Sub[(i-1)+x*j]
                nins = Ins[(i-1)+x*j]+1
                ndel = Del[(i-1)+x*j]

            Tot[i+x*j] = ntot
            Noo[i+x*j] = nnoo
            Sub[i+x*j] = nsub
            Del[i+x*j] = ndel
            Ins[i+x*j] = nins

    return Tot[-1],Noo[-1],Sub[-1],Del[-1],Ins[-1], len(mandwords)

def charalign(ocrd,mand):
    # Align an ocr string and a manual (gold standard) string

    # First fill in the edit distance matrix
    # Operations, each may be associated with special costs/circumstances
    #
    # z: potential alternative startpoint for the alignment (directly
    #    after a newline in the ocr string at the start of the manual
    #    string)
    # d: delete
    # i: insert
    # n: no operation (direct match)
    # w: matching whitespace
    # h: matching hyphens
    # t: substitute
    # -: delete a hyphen at the end of the line
    # r: deleta a return

    x = len(ocrd)+1
    y = len(mand)+1
    M = [0 for _ in range(x*y)]         # matrix (as list) holding scores
    O = ['' for _ in range(x*y)]        # matrix (as list) holding operations/backpointers

    M[0] = 0
    for i in range(1,x):
        # fill in the X-margin, mark positions after a newline
        if i > 1 and ocrd[i-1]=='\n':
            M[i] = 0
            O[i] = 'z'
        else:
            M[i] = M[i-1]+1
            O[i] = 'd'

    for j in range(1,y):
        # fill in the Y-margin
        M[x*j] = M[x*(j-1)] + 1
        O[x*j] = 'i'

    for j in range(1,y):
        for i in range(1,x):
            # Fill in the rest of the matrix
            # NOTE: the matrix indices i,j correspond to string indices i-1, j-1, because of the added initial row/column

            # substitutions
            mandchar = mand[j-1]
            ocrdchar = ocrd[i-1]
            if mandchar == ocrdchar:
                diag = M[(i-1)+x*(j-1)]
                ops = 'n' # no-op
            elif mandchar in ' \t\n' and ocrdchar in ' \t\n':
                diag = M[(i-1)+x*(j-1)]
                ops = 'w' # match whitespace
            elif mandchar in '-\u2014\u00ad' and ocrdchar in '-\u2014\xad':
                diag = M[(i-1)+x*(j-1)]
                ops = 'h' # match hyphens
            elif mandchar not in '\t \n' and ocrdchar not in ' \t\n':
                if mandchar in punct and ocrdchar in punct:
                    diag = M[(i-1)+x*(j-1)]+0.999 # if it's all the same, prefer to substitute punktuation for punktuation
                elif mandchar not in punct and ocrdchar not in punct:
                    diag = M[(i-1)+x*(j-1)]+0.999 #                       or substitute nonpunktuation for nonpunktuation
                else:
                    diag = M[(i-1)+x*(j-1)]+1
                ops = 't' # substitute, only non-whitespace
            else:
                ops = 'x'
                diag = M[(i-1)+x*(j-1)]+100000
            bst = diag

            # inserts
            down = M[i+x*(j-1)]+1
            if down < bst:
                ops = 'i' # insert
                bst = down
            elif down == bst:
                ops += 'i'

            # deletes
            if ocrd[i-1] in ('-','\xad') and (i==x-1 or (i < x-1 and ocrd[i]=='\n')):
                rght = M[(i-1)+x*j]
                dops = '-' # delete a hyphen at the end of the line = free
            elif ocrd[i-1] == '\n':
                rght = M[(i-1)+x*j]
                dops = 'r' # delete a newline ('r'eturn) = free
            else:
                rght = M[(i-1)+x*j]+1
                dops = 'd' # delete

            if rght < bst:
                ops = dops
                bst = rght
            elif rght == bst:
                ops += dops

            # enter the best score and operations/backpointers in the matrices
            M[i+x*j] = bst
            O[i+x*j] = ops



    # Reconstruct one of the optimal alignments. There is no explicit
    # control over which alignment is chosen in case of multiple
    # alignments with the same, optimatal score.

    # Alignment endpoint logic, depends on -se switch (=OPTstripend)
    j = y-1
    if OPTstripend and '\n' in ocrd:
        # endpoint is cheapest cell on bottom row that corresponds to a newline in the ocr string
        i = -min((M[(i+1)+x*j],-(i+1)) for i,ch in enumerate(ocrd) if ch=='\n' or i==x-2)[1]
    else:
        i = x-1

    ocrdrec = []
    mandrec = []

    while i or j:
        op = O[i+x*j][-1]
        if OPTstripbeg and op == 'z': # ztartpoint of the alignment, see also endpoint logic
                                      # depends on -sb switch (=OPTstripbeg)
            break
        elif op in 'ntwh':
            ocrdrec.append(ocrd[i-1])
            mandrec.append(mand[j-1])
            i -= 1
            j -= 1
        elif op in 'dz': # case for z when stripping of initial lines is not allowed
            ocrdrec.append(ocrd[i-1])
            mandrec.append('') # u'\u03F5')
            i -= 1
        elif op=='e':
            i -= 1
        elif op in 'r-':
            ocrdrec.append(ocrd[i-1])
            mandrec.append('') # %
            i -= 1
        elif op == 'i':
            ocrdrec.append('') # u'\u03F5')
            mandrec.append(mand[j-1])
            j -= 1

#    for p in zip(reversed(mandrec),reversed(ocrdrec)):
#        print "[%s]\t[%s]" % p

    return list(reversed(ocrdrec)),list(reversed(mandrec))


def markerror(listofstrings,index):
    # Mark the character(s) at location index as an error, to give some visual feedback
    # '\x1b[44;1m' and '\x1b[0m' are ANSI escape codes that change the color and fontstyle
    # See e.g. https://en.wikipedia.org/wiki/ANSI_escape_code
    listofstrings[index] = '°°'+listofstrings[index]+'°°'





def score_and_print(ocrdrec,mandrec):
    # With the alignment, go through line by line, character by character to count errors, characters, words, etc.
    # Also marks the errors in a printable way and prints the alignment and scores to the screen
    output=[]
    output_mand = []
    if ocrdrec == []:
        return 0, 0, 0, 0, 0, 0, 0, [], defaultdict(Counter)
#        return charactererrors, characters, worderrors, words, unaligned_ocr_whitespaces, unaligned_man_whitespaces, aligned_whitespaces

    newlines = [i for i,char in enumerate(ocrdrec) if char=='\n']
#    if not newlines or not newlines[-1] == len(ocrdrec)-1:
 #       newlines.append(len(ocrdrec)-1)
    i0 = 0
    charactererrors = 0
    characters = 0
    worderrors = 0 # number of words containing
    words = 0
    unaligned_ocr_whitespaces = 0
    unaligned_man_whitespaces = 0
    aligned_whitespaces = 0
    mismatch_counter = defaultdict(Counter)


    errors_in_current_word = False
    characters_in_mandword = False

    for i in newlines:
        ocrdline = ocrdrec[i0:i+1]
        mandline = mandrec[i0:i+1]
        i0 = i+1

        try:
            ignorable_prefix = next(i for i,(o,m) in enumerate(zip(ocrdline,mandline))
                                    if o not in ('','\n','\t',' ') or m not in ('','\n','\t',' '))
        except StopIteration:
            ignorable_prefix = len(ocrdline)

        try:
            ignorable_suffix = len(ocrdline)-next(i for i,(o,m) in enumerate(reversed(list(zip(ocrdline,mandline))))
                                                  if o not in ('','\n','\t',' ','-','\xad') or m not in ('','\n','\t',' '))
        #                                                                       ^^^^ End of line hyphens are ignorable in the OCR.
        #                                                                            BUG! may ignore several line-final hyphens in a row
        except StopIteration:
            ignorable_suffix = 0

        # for i,o in enumerate(ocrdline):
        #     if o == '\n':
        #         ocrdline[i] = '\u2424' # unicode ␤  (newline)
        #     elif o == '\t':
        #         ocrdline[i] = '\u2409' # unicode ␉  ([horizontal] tab)
        #
        # for i,m in enumerate(mandline):
        #     if m == '\n':
        #         mandline[i] = '\u2424'
        #     elif m == '\t':
        #         mandline[i] = '\u2409'

        # compare line on character basis
        for i,(o,m) in enumerate(zip(ocrdline,mandline)):

            # All the `pass' cases are considered correct
            if ignorable_suffix <= i or i < ignorable_prefix:
                # if not o:
                #     ocrdline[i] = '\u03F5' # unicode epsilon
                if not m:
                    mandline[i] = '\u03F5'
                pass
            elif o and o in '-\u2014\xad' and m and m in '-\u2014\xad': # (soft-)hyphen and m-dash considered equal
                pass
            elif o in ('\u2424','\u2409',' ') and m in ('\u2409',' '):
                aligned_whitespaces += 1
                pass
            elif OPTnewlines_in_man and m=='\u2424' and o in ('\u2424','\u2409',' '):
                aligned_whitespaces += 1
                pass
            elif o == '-' and m == '\u00ad': # hyphen and soft hyphen considered equal
                pass
# Special cases if certain characters are to be ignored in the total count
#            elif o == '*':
#                characters -= 1
#            elif m and m in u'åöäÅÖÄëË':
#                characters -= 1
            elif o==m:
                pass

            # The rest constitutes an error case
            else:
                print(o, m)
                mismatch_counter[m][o] += 1
                charactererrors += 1

                # if not o:
                #     ocrdline[i] = '\u03F5' # unicode epsilon
                if not m:
                    mandline[i] = '\u03F5'


                markerror(ocrdline,i)
                markerror(mandline,i)

                if o in (' ','\u2424','\u2409'):
                    unaligned_ocr_whitespaces += 1

                if m in (' ','\u2424','\u2409'):
                    unaligned_man_whitespaces += 1
                else:
                    errors_in_current_word = True


            if m:
                characters +=1

            # rather rudimentary word counting, only segments at ' ' (space).
            if m in ('\u2424','\u2409',' '):
                if characters_in_mandword:
                    words += 1
                    if errors_in_current_word:
                        worderrors += 1
                characters_in_mandword = False
                errors_in_current_word = False
            elif m:
                characters_in_mandword = True

        # print the alignment with markup to the screen, with a running score counter for this page
        #print(( ''.join(char for char in ocrdline), '\tce: %s, #c: %s, we: %s, #w: %s' % (charactererrors, characters, worderrors, words)))
        # f= open("demofile.txt", "a")
        # f.write(''.join(char for char in ocrdline))
        #print(( ''.join(char for char in mandline)))
        #print()
        output.append(''.join(char for char in ocrdline)+'\n')
        output_mand.append(''.join(char for char in mandline)+'\n')

    if characters_in_mandword:
        words += 1
    if errors_in_current_word:
        worderrors += 1

    return charactererrors, characters, worderrors, words, unaligned_ocr_whitespaces, unaligned_man_whitespaces, aligned_whitespaces, output, mismatch_counter



# Options to control the stripping of lines at the beginning resp end
OPTstripbeg = False
OPTstripend = False
OPTnewlines_in_man = False
def main(ocr_paths, truth_paths, output_filename, mode=None):
    output = []
    print(zip(ocr_paths,truth_paths))
    if mode == '-sb':
        OPTstripbeg = True
    elif mode == '-se':
        OPTstripend = True
    elif mode == '-nm':
        OPTnewlines_in_man = True


    totalchrs = totalchrerrs = totalwrds = totalwrderrs = totalua_m_wh = totalua_o_wh = totala_wh = 0
    tWErrors = tWNoos = tWSubs = tWDels = tWIns = tWCount = 0
    total_mismatch_counter = defaultdict(Counter)
    mismatch_counter = defaultdict(Counter)
    count=1
    hallucinations = []
    for ocrdfile, mandfile in zip(os.listdir(ocr_paths),os.listdir(truth_paths)):
        print(ocrdfile, mandfile)
        if len(os.listdir(ocr_paths)) != len(os.listdir(truth_paths)):
            continue
        else:
            with codecs.open(os.path.join(ocr_paths, ocrdfile),'r','utf8') as f:
                # codecs.open('utf8') no gusto universal newlines???
                ocrd = f.read().replace('\r\n','\n').replace('\r','\n').strip()
            with codecs.open(os.path.join(truth_paths, mandfile),'r','utf8') as f:
                mand = f.read().replace('\r\n','\n').replace('\r','\n').replace('\ufeff', '').strip()

            
            if len(ocrd) > len(mand) + 100 or len(ocrd) < len(mand) - 100:
                print(f'{ocrdfile} is hallucinations!')
                hallucination = ocrdfile
                hallucinations.append(hallucination)
                continue
            ocr_words = [word for line in ocrd for word in line.split()]
            mandwords = [word for line in mand for word in line.split()]
            for word in ocr_words:
                word = remove_tags(word)
            ocrdrec,mandrec = charalign(ocrd,mand)
            chrerrs, chrs, wrderrs, wrds, ua_o_wh, ua_m_wh, a_wh, ocrdlines, mismatch_counter = score_and_print(ocrdrec,mandrec)
            WErrors, WNoos, WSubs, WDels, WIns, WCount = worderrors(ocrdrec,mandrec)

            # merge mismatch_counter into total_mismatch_counter
            for m_char, inner_counter in mismatch_counter.items():
                for o_char, dict_count in inner_counter.items():
                    total_mismatch_counter[m_char][o_char] += dict_count
            

            totalchrerrs += chrerrs
            totalchrs += chrs
            totalwrderrs += wrderrs
            totalwrds += wrds
            totalua_m_wh += ua_m_wh
            totalua_o_wh += ua_o_wh
            totala_wh += a_wh

            tWErrors += WErrors
            tWNoos += WNoos
            tWSubs += WSubs
            tWDels += WDels
            tWIns += WIns
            tWCount += WCount

            if totalchrs == 0:
                continue
                
            results = {
                'total_chrerrs' : totalchrerrs,
                'total_chrs' : totalchrs,
                'cer': totalchrerrs/totalchrs,
                'total_wrderrs' : totalwrderrs,
                'total_wrds' : totalwrds,
                'wer' : totalwrderrs/totalwrds,
                'unaligned gt whitespaces' : totalua_m_wh,
                'unaligned ocr whitespaces' : totalua_o_wh,
                'aligned whitespaces' : totala_wh,
                'tWErrors' : tWErrors,
                'tWNoos' : tWNoos,
                'tWSubs' : tWSubs,
                'tWDels' : tWDels,
                'tWIns' : tWIns,
                'tWCount' : tWCount
                }
            words = [word for line in ocrdlines for word in line.split()]
            for word in words:
                if('°°'in word):
                    word = word.replace('°','')
                    output.append(word)
            print("Progress: ("+str(count)+'/'+str(len(os.listdir(ocr_paths)))+")")
            count+=1

        f = open('final_' + output_filename, 'w', encoding='utf-8')
        for k, v in results.items():
            f.write(f'{k} {v} \n')
        for k, v in total_mismatch_counter.items():
            f.write(f'{k} {v} \n')
        f.write('Hallucination files \n')
        for h in hallucinations:
            f.write(f'{h} \n')

        wrong_words = Counter(output)

        f2 = open('wrong_words_' + output_filename, 'w', encoding='utf-8')
        f2.write(f'{wrong_words}')

    return results, total_mismatch_counter, hallucinations

#main("-sb", ["/Users/simonpersson/Github/MasterThesis/Evaluation-script/OCROutput/Ocropus/Argus/ed_pg_a0002_ocropus_twomodel.txt"], ["/Users/simonpersson/Github/MasterThesis/Evaluation-script/ManuelTranscript/Argus/ed_pg_a0002.txt"], "test.txt")
