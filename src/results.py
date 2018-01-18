""" Script for formatting results of experiments """

import config
import datasets.na
import datasets.chatino

from collections import defaultdict
import os
import utils

from distance import min_edit_distance_align
from distance import cluster_alignment_errors

def round_items(floats):
    return ["%0.3f" % fl for fl in floats]

def format(exp_paths,
                   phones=datasets.na.PHONEMES,
                   tones=datasets.na.TONES):
    """ Takes a list of experimental paths such as mam/exp/<number> and outputs
    the results. """

    valid_lers = []
    valid_pers = []
    test_lers = []
    test_pers = []
    test_ters = []

    for path in exp_paths:

        test_ler, test_per, test_ter = test_results(path, phones, tones)
        test_lers.append(test_ler)
        test_pers.append(test_per)
        test_ters.append(test_ter)

        with open(os.path.join(path, "best_scores.txt")) as best_f:
            sp = best_f.readline().replace(",", "").split()
            training_ler, valid_ler, valid_per = float(sp[4]), float(sp[7]), float(sp[10])
            valid_lers.append(valid_ler)

    print("Valid LER", round_items(valid_lers))
    print("Test LER", round_items(test_lers))
    print("Test PER", round_items(test_pers))
    print("Test TER", round_items(test_ters))

    print("PERS:")
    for item in zip([128,256,512,1024,2048], test_pers):
        print("(%d, %f)" % item)

    print("TERS:")
    for item in zip([128,256,512,1024,2048], test_ters):
        print("(%d, %f)" % item)

def filter_labels(sent, labels=None):
    """ Returns only the tokens present in the sentence that are in labels."""
    if labels:
        return [tok for tok in sent if tok in labels]
    return sent

def test_results(exp_path, phones, tones):
    """ Gets results of the model on the test set. """

    test_path = os.path.join(exp_path, "test")
    print(test_path)
    with open(os.path.join(test_path, "test_per")) as test_f:
        line = test_f.readlines()[0]
        test_ler = float(line.split()[2].strip(","))

    test_per = filtered_error_rate(os.path.join(test_path, "hyps"),
                                      os.path.join(test_path, "refs"),
                                      phones)

    test_ter = filtered_error_rate(os.path.join(test_path, "hyps"),
                                      os.path.join(test_path, "refs"),
                                      tones)

    return test_ler, test_per, test_ter

def filtered_error_rate(hyps_path, refs_path, labels):

    with open(hyps_path) as hyps_f:
        lines = hyps_f.readlines()
        hyps = [filter_labels(line.split(), labels) for line in lines]
    with open(refs_path) as refs_f:
        lines = refs_f.readlines()
        refs = [filter_labels(line.split(), labels) for line in lines]

    # For the case where there are no tokens left after filtering.
    only_empty = True
    for entry in hyps:
        if entry != []:
            only_empty = False
    if only_empty:
        return -1

    return utils.batch_per(hyps, refs)

def ed_alignments(exp_path):

    test_path = os.path.join(exp_path, "test")
    hyps_path = os.path.join(test_path, "hyps")
    refs_path = os.path.join(test_path, "refs")

    with open(hyps_path) as hyps_f:
        lines = hyps_f.readlines()
        hyps = [line.split() for line in lines]
    with open(refs_path) as refs_f:
        lines = refs_f.readlines()
        refs = [line.split() for line in lines]

    alignments = []
    for ref, hyp in zip(refs, hyps):
        alignment = min_edit_distance_align(ref, hyp)
        alignments.append(alignment)

    return alignments

def symbol_errors(exp_path, symbol):

    alignments = ed_alignments(exp_path)

    correct = 0
    del_ = 0
    ins = 0
    del_sub = 0
    ins_sub = 0
    total_hyp = 0
    total_ref = 0
    for alignment in alignments:
        for arrow in alignment:
            if arrow[0] == symbol and arrow[1] == symbol:
                correct += 1
            elif arrow[0] == symbol and arrow[1] == "":
                del_ += 1
            elif arrow[0] == "" and arrow[1] == symbol:
                ins += 1
            elif arrow[1] == symbol:
                ins_sub += 1
            elif arrow[0] == symbol:
                del_sub += 1
            if arrow[1] == symbol:
                total_hyp += 1
            if arrow[0] == symbol:
                total_ref += 1

    print(correct)
    print(del_)
    print(ins)
    print(del_sub)
    print(ins_sub)
    print(total_hyp)
    print(total_ref)

    error_rate = (del_ + ins + del_sub + ins_sub) / (correct + del_ + ins + del_sub + ins_sub)
    print(error_rate)
    del_rate = (del_ + del_sub) / (correct + del_ + del_sub)
    print(del_rate)
    ins_rate = (ins + ins_sub) / (correct + ins + ins_sub)
    print(ins_rate)

    errors = []
    for alignment in alignments:
        for arrow in alignment:
            if arrow[0] != arrow[1]:
                errors.append(arrow)

    err_hist = {}
    for error in errors:
        if error in err_hist:
            err_hist[error] += 1
        else:
            err_hist[error] = 1

def latex_output(refs_path, hyps_path, utter_ids_fn):
    """ Pretty print the hypotheses and references. """

    with open(hyps_path) as hyps_f:
        lines = hyps_f.readlines()
        hyps = [line.split() for line in lines]
    with open(refs_path) as refs_f:
        lines = refs_f.readlines()
        refs = [line.split() for line in lines]

    alignments = []
    for ref, hyp in zip(refs, hyps):
        alignment = min_edit_distance_align(ref, hyp)
        alignments.append(alignment)

    with open(utter_ids_fn) as f:
        prefixes = [line.replace("_", "\_") for line in f]
        # TODO Na-specific stuff commented out for work on Chatino
        #prefixes2 = []
        #for prefix in prefixes:
        #    sp = prefix.split(".")
        #    prefixes2.append(" ".join([sp[0], "Sent \\#" + str(int(sp[1])+1)]))
        #prefixes = prefixes2
    #print(prefixes)

    with open("hyps_refs.tex", "w") as out_f:

        print("\documentclass[10pt]{article}\n"
              "\\usepackage[a4paper,margin=0.5in,landscape]{geometry}\n"
              "\\usepackage[utf8]{inputenc}\n"
              "\\usepackage{xcolor}\n"
              "\\usepackage{polyglossia}\n"
              "\\usepackage{booktabs}\n"
              "\\usepackage{longtable}\n"
              "\setmainfont[Mapping=tex-text,Ligatures=Common,Scale=MatchLowercase]{Doulos SIL}\n"
              "\DeclareRobustCommand{\hl}[1]{{\\textcolor{red}{#1}}}\n"
              "\\begin{document}\n"
              "\\begin{longtable}{ll}", file=out_f)

        print("\\toprule", file=out_f)
        for prefix, alignment in zip(prefixes, alignments):
            ref_list = []
            hyp_list = []
            for arrow in alignment:
                if arrow[0] == arrow[1]:
                    # Then don't highlight it; it's correct.
                    ref_list.append(arrow[0])
                    hyp_list.append(arrow[1])
                else:
                    # Then highlight the errors.
                    ref_list.append("\hl{%s}" % arrow[0])
                    hyp_list.append("\hl{%s}" % arrow[1])
            print("Utterance ID: &", prefix.strip(), "\\\\", file=out_f)
            print("Ref: &", "".join(ref_list), "\\\\", file=out_f)
            print("Hyp: &", "".join(hyp_list), "\\\\", file=out_f)
            print("\\midrule", file=out_f)

        print("\end{longtable}", file=out_f)
        print("\end{document}", file=out_f)

def error_types(exp_path, labels=None):
    """ Stats about the most common types of errors in the test set."""

    test_path = os.path.join(exp_path, "test")
    hyps_path = os.path.join(test_path, "hyps")
    refs_path = os.path.join(test_path, "refs")

    with open(hyps_path) as hyps_f:
        lines = hyps_f.readlines()
        hyps = [filter_labels(line.split(), labels) for line in lines]
    with open(refs_path) as refs_f:
        lines = refs_f.readlines()
        refs = [filter_labels(line.split(), labels) for line in lines]

    alignments = []
    errors = []
    for ref, hyp in zip(refs, hyps):
        alignment = min_edit_distance_align(ref, hyp)
        alignment = cluster_alignment_errors(alignment)
        alignments.append(alignment)
        for arrow in alignment:
            if arrow[0] != arrow[1]:
                errors.append(arrow)

    err_hist = {}
    for error in errors:
        if error in err_hist:
            err_hist[error] += 1
        else:
            err_hist[error] = 1

    error_list = sorted(err_hist.items(), key=lambda x: x[1], reverse=False)
    for thing in error_list:
        print(thing)

    subs = 0
    inss = 0
    dels = 0
    for error in error_list:
        if len(error[0][1]) == 0:
            dels += 1
        if len(error[0][0]) == 0:
            inss += 1
        else:
            subs += 1
    print(subs)
    print(inss)
    print(dels)

def chatino_tone_confusion(exp_path):
    """ Outputs a confusion matrix for Chatino tones."""

    tones = list(datasets.chatino.TONES)
    alignments = ed_alignments(exp_path)

    d = defaultdict(int)
    for alignment in alignments:
        for arrow in alignment:
            if arrow[0] in tones:
                d[arrow] += 1

    import pprint; pprint.pprint(d)

    total = defaultdict(int)
    for ref in tones:
        for hyp in tones:
            total[ref] += d[(ref, hyp)]

    nonzero_tones = [item[0] for item in total.items() if item[1] > 4]
    print(sorted(total.items(), key=lambda x: x[1]))

    for hyp in nonzero_tones[:-1]:
        print(hyp + ",", end="")
    print("%s\\\\" % nonzero_tones[-1])
    for ref in nonzero_tones:
        print(ref + ",", end="")
        for hyp in nonzero_tones[:-1]:
            print("%0.3f," % (d[(ref, hyp)]*100/total[ref]), end="")
        print("%0.3f\\\\" % (d[(ref, nonzero_tones[-1])]*100/total[ref]))

