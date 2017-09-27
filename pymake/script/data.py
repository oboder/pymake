from pymake import ModelManager, FrontendManager, ExpeFormat

from collections import OrderedDict


import matplotlib.pyplot as plt
from pymake.util.utils import colored
from pymake.expe.format import tabulate

class Data(ExpeFormat):

    _default_expe = { '_expe_silent' : True }

    def missing(self, _type='pk'):
        if self.is_first_expe():
            self.gramexp.n_exp_total = self.expe_size
            self.gramexp.n_exp_missing = 0

        is_fitted = self.gramexp.make_output_path(self.expe, _type=_type, status='f')
        if not is_fitted:
            self.gramexp.n_exp_missing += 1
            self.log.debug(self.expe['_output_path'])


        if self.is_last_expe():
            table = OrderedDict([('missing', [self.gramexp.n_exp_missing]),
                                 ('total', [self.gramexp.n_exp_total]),
                                ])
            print (tabulate(table, headers='keys', tablefmt='simple', floatfmt='.3f'))


    def completed(self, _type='pk'):
        if self.is_first_expe():
            self.gramexp.n_exp_total = self.expe_size
            self.gramexp.n_exp_completed = 0

        is_fitted = self.gramexp.make_output_path(self.expe, _type=_type, status='f')
        if is_fitted:
            self.gramexp.n_exp_completed += 1
            self.log.debug(self.expe['_output_path'])


        if self.is_last_expe():
            table = OrderedDict([('completed', [self.gramexp.n_exp_completed]),
                                 ('total', [self.gramexp.n_exp_total]),
                                ])
            print (tabulate(table, headers='keys', tablefmt='simple', floatfmt='.3f'))


