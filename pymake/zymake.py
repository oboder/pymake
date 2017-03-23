#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals


# __remove__ -> INTERNAL !
#from joblib import Parallel, delayed
import sys, multiprocessing

from pymake import GramExp


''' A Command line controler of Pymake '''


if __name__ == '__main__':

    zymake = GramExp.zymake()
    zyvar = zymake._conf

    if zyvar.get('simulate'):
        # same as show !
        zymake.simulate()

    ### Makes OUT Files
    lines = None
    if zyvar['_do'] == 'cmd':
        lines = zymake.make_commandline()
    elif zyvar['_do'] == 'path':
        lines = zymake.make_path(ftype=zyvar.get('_ftype', 'pk'), status=zyvar.get('_status'))
    elif zyvar['_do'] == 'show':
        zymake.simulate()
    elif zyvar['_do'] == 'exec':
        lines = zymake.execute()
    elif zyvar['_do'] == 'burn':
        # @todo; parallelize Pymake()
        raise NotImplementedError('What parallel strategy ?')
    else:

        if not 'do_list' in zyvar:
            raise ValueError('Unknown Options : %s' % zyvar)

        if 'atom' in zyvar.get('do_list', []):
            print (zymake.atomtable())
        elif 'atom_topos' in zyvar.get('do_list',[]):
            print (zymake.atomtable(_type='topos'))
        elif 'script' in zyvar.get('do_list', []):
            print(zymake.scripttable())
        elif 'expe' in  zyvar.get('do_list',[]):
            print (zymake.spectable())
        else:
            print(zymake.help_short())
            if zyvar['do_list']:
                print ('Unknow options %s ?' % zyvar.get('do_list'))
        exit()

    if lines is None:
        # catch signal ?
        exit()

    if 'script' in zyvar:
        script = './zymake.py exec'
        lines = [' '.join((script, l)) for l in lines]

    zymake.simulate(halt=False, file=sys.stderr)
    print('\n'.join(lines), file=sys.stdout)
