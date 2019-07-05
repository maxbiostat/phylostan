import numpy
import math


def get_peeling_order(tree):
    peeling = []
    for node in tree.postorder_node_iter():
        if not node.is_leaf():
            peeling.append(
                [x.index for x in node.child_node_iter()] + [node.index])
    return peeling


def get_preorder(tree):
    peeling = []
    peeling.append([tree.seed_node.index, 0])
    for node in tree.preorder_node_iter():
        if node.parent_node is not None:
            peeling.append([node.index, node.parent_node.index])
    return peeling


def get_lowers(tree):
    lowers = [0 for x in tree.postorder_node_iter()]
    ll = {}

    for node in tree.postorder_node_iter():
        if node.is_leaf():
            ll[node] = node.date
        else:
            ll[node] = max([ll[x] for x in node.child_node_iter()])

    for node in tree.preorder_node_iter():
        lowers[node.index-1] = ll[node]
    return lowers


def get_dna_leaves_partials(alignment):
    tipdata = numpy.zeros((len(alignment), alignment.sequence_size, 4), dtype=numpy.int)
    dna_map = {'a': [1, 0, 0, 0], 'c': [0, 1, 0, 0], 'g': [0, 0, 1, 0], 't': [0, 0, 0, 1]}

    s = 0
    for name in alignment:
        for i, c in enumerate(alignment[name].symbols_as_string()):
            tipdata[s][i][:] = dna_map.get(c.lower(), [1, 1, 1, 1])
        s += 1
    return tipdata


def get_dna_leaves_partials_compressed(alignment):
    weights = []
    keep = [True] * alignment.sequence_size

    patterns = {}
    indexes = {}
    for i in range(alignment.sequence_size):
        pat = ''
        for name in alignment:
            pat += str(alignment[name][i])

        if pat in patterns:
            keep[i] = False
            patterns[pat] += 1
        else:
            patterns[pat] = 1
            indexes[i] = pat

    for i in range(alignment.sequence_size):
        if keep[i]:
            weights.append(patterns[indexes[i]])

    tipdata = numpy.zeros((len(alignment), len(patterns.keys()), 4), dtype=numpy.int)

    dna_map = {'a': [1, 0, 0, 0], 'c': [0, 1, 0, 0], 'g': [0, 0, 1, 0], 't': [0, 0, 0, 1]}

    s = 0
    for name in alignment:
        k = 0
        for i, c in enumerate(alignment[name].symbols_as_string()):
            if keep[i]:
                tipdata[s][k][:] = dna_map.get(c.lower(), [1, 1, 1, 1])
                k += 1
        s += 1
    return tipdata, weights


def to_nexus(node, fp):
    if not node.is_leaf():
        fp.write('(')
        for i, n in enumerate(node.child_node_iter()):
            to_nexus(n, fp)
            if i == 0:
                fp.write(',')
        fp.write(')')
    else:
        fp.write(str(node.index))
    if hasattr(node, 'date'):
        fp.write('[&height={}'.format(node.date))
        if hasattr(node, 'rate'):
            fp.write(',rate={}'.format(node.rate))
        fp.write(']')
    if node.parent_node is not None:
        fp.write(':{}'.format(node.edge_length))
    else:
        fp.write(';')


def convert_samples_to_nexus(tree, input, output, rate=None):
    taxaCount = len(tree.taxon_namespace)
    outp = open(output, 'w')
    outp.write('#NEXUS\nBegin trees;\nTranslate\n')
    outp.write(',\n'.join([str(i + 1) + ' ' + x.label.replace("'", '') for i, x in enumerate(tree.taxon_namespace)]))
    outp.write('\n;\n')

    time = False
    with open(input) as fp:
        for line in fp:
            if line.startswith('lp'):
                try:
                    line.split(',').index('blens.1')
                except ValueError:
                    time = True
                break

    count = 1
    if time:
        with open(input) as fp:
            for line in fp:
                if line.startswith('lp'):
                    header = line.split(',')
                    hindex = header.index('heights.1')
                    if rate is None:
                        strict = False
                        try:
                            rindex = header.index('substrates.1')
                        except ValueError:
                            rindex = header.index('rate')
                            strict = True
                    else:
                        strict = True
                elif not line.startswith('#'):
                    l = line.split(',')
                    for n in tree.postorder_node_iter():
                        if not n.is_leaf():
                            n.date = float(l[hindex + n.index-taxaCount - 1])
                    if strict:
                        for n in tree.postorder_node_iter():
                            if n.parent_node is not None:
                                n.rate = float(l[rindex]) if rate is None else rate
                    else:
                        for n in tree.postorder_node_iter():
                            if n.parent_node is not None:
                                n.rate = float(l[rindex + n.index-1])

                    for n in tree.postorder_node_iter():
                        if n.parent_node is not None:
                            n.edge_length = n.parent_node.date - n.date
                    outp.write('tree {} = '.format(count))
                    count += 1
                    to_nexus(tree.seed_node, outp)
                    outp.write('\n')
    else:
        with open(input) as fp:
            for line in fp:
                if line.startswith('lp'):
                    header = line.split(',')
                    bindex = header.index('blens.1')
                elif not line.startswith('#'):
                    l = line.split(',')
                    for n in tree.postorder_node_iter():
                        if n.parent_node is not None:
                            if bindex + n.index - 1 < len(l):
                                n.edge_length = float(l[bindex + n.index - 1])
                            else:
                                n.edge_length = 0.0
                    outp.write('tree {} = '.format(count))
                    count += 1
                    to_nexus(tree.seed_node, outp)
                    outp.write('\n')
    outp.write('END;')
    outp.close()