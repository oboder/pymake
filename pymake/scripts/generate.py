#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import numpy as np
import scipy as sp
from numpy import ma
from pymake import ExpTensor, ModelManager, FrontendManager, GramExp, ExpeFormat, ExpSpace

import logging
lgg = logging.getLogger('root')
_spec = GramExp.Spec()

USAGE = '''\
----------------
Generate data  --or find the answers :
----------------
 |
 |   methods
 |   ------
 |   burstiness : global + local + feature burstiness.
 |   homo       : homophily based analysis.
 |
>> Examples
    parallel ./generate.py -k {}  ::: $(echo 5 10 15 20)
    generate --alpha 1 --gmma 1 -n 1000 --seed
'''

Corpuses = _spec['CORPUS_SYN_ICDM']

Exp = ExpTensor ((
    ('corpus', Corpuses),
    ('data_type'    , 'networks'),
    ('refdir'        , 'debug111111') , # ign in gen
    #('model'        , 'mmsb_cgs')   ,
    ('model'        , ['immsb', 'ibp'])   ,
    ('K'            , 10)        ,
    ('N'            , 'all')     , # ign in gen
    ('hyper'        , ['auto', 'fix'])    , # ign in gen
    ('homo'         , 0)         , # ign in gen
    ('repeat'      , 1)       ,
    ('_bind'    , ['immsb.auto', 'ibp.fix']),
    ('alpha', 1),
    ('gmma', 1),
    ('delta', [(1, 5)]),
))

class GenNetwork(ExpeFormat):
    def __init__(self, *args, **kwargs):
        super(GenNetwork, self).__init__(*args, **kwargs)
        expe = self.expe

        if expe._mode == 'predictive':
            ### Generate data from a fitted model
            model = ModelManager.from_expe(expe)

            # __future__ remove
            try:
                # this try due to mthod modification entry in init not in picke object..
                expe.hyperparams = model.get_hyper()
            except:
                if model is not None:
                    model._mean_w = 0
                    expe.hyperparams = 0

            frontend = FrontendManager.load(expe)
            N = frontend.getN()
            expe.title = None
        elif expe._mode == 'generative':
            N = expe.gen_size
            ### Generate data from a un-fitted model
            if expe.model == 'ibp':
                keys_hyper = ('alpha','delta')
                hyper = (expe.alpha, expe.delta)
            else:
                keys_hyper = ('alpha','gmma','delta')
                hyper = (expe.alpha, expe.gmma, expe.delta)
            expe.hyperparams = dict(zip(keys_hyper, hyper))
            expe.hyper = 'fix' # dummy
            model = ModelManager.from_expe(expe, init=True)
            #model.update_hyper(hyper)

            if expe.model == 'ibp':
                title = 'N=%s, K=%s alpha=%s, lambda:%s'% ( N, expe.K, expe.alpha, expe.delta)
            elif expe.model == 'immsb':
                title = 'N=%s, K=%s alpha=%s, gamma=%s, lambda:%s'% (N, expe.K, expe.alpha, expe.gmma, expe.delta)
            elif expe.model == 'mmsb_cgs':
                title = 'N=%s, K=%s alpha=%s, lambda:%s'% ( N, expe.K, expe.alpha, expe.delta)
            else:
                raise NotImplementedError

            expe.title = title

        else:
            raise NotImplementedError('What generation context ? predictive/generative..')

        lgg.debug('Deprecated : get symmetric info from model.')
        expe.symmetric = frontend.is_symmetric()
        self.expe = expe
        self.frontend = frontend
        self.model = model

        if model is None:
            raise FileNotFoundError('No model for Expe at :  %s' % self.expe.output_path)

        if expe._do[0] in ('burstiness','pvalue','homo', 'homo_mustach'):
            ### Generate data
            Y = []
            now = Now()
            for i in range(expe.epoch):
                try:
                    y = model.generate(mode=expe._mode, N=N, K=expe.K)
                except:
                # __future__, remove, one errror, update y = model.gen.....
                    y,_,_ = model.generate(mode=expe._mode, N=N, K=expe.K)
                Y.append(y)
            lgg.info('Data Generation : %s second' % nowDiff(now))

            #R = rescal(data, expe['K'])

            if expe.symmetric:
                for y in Y:
                    frontend.symmetrize(y)
            self._Y = Y

        lgg.info('=== M_e Mode === ')
        lgg.info('Mode: %s' % expe._mode)
        lgg.info('hyper: %s' % (str(expe.hyperparams)))


    def init_fit_tables(self,_type, Y=[]):
        expe = self.expe
        if not hasattr(self.gramexp, 'tables'):
            corpuses = _spec.name(self.gramexp.getCorpuses())
            models = self.gramexp.getModels()
            Meas = [ 'pvalue', 'alpha', 'x_min', 'n_tail']
            tables = {}
            for m in models:
                if _type == 'local':
                    table_shape = (len(corpuses), len(Meas), expe.K**2)
                    table = ma.array(np.empty(table_shape), mask=True)
                elif _type == 'global':
                    table = np.empty((len(corpuses), len(Meas), len(Y)))
                tables[m] = table
            self.gramexp.Meas = Meas
            self.gramexp.tables = tables
            Table = tables[expe.model]
        else:
            Table = self.gramexp.tables[expe.model]
            Meas = self.gramexp.Meas

        return Table, Meas

    def init_roc_tables(self):
        expe = self.expe
        if not hasattr(self.gramexp, 'tables'):
            corpuses = _spec.name(self.gramexp.getCorpuses())
            if not 'testset_ratio' in self.pt:
                Meas = ['20']
            else:
                Meas = self.gramexp.exp_tensor['testset_ratio']
            tables = ma.array(np.empty((len(corpuses), len(Meas),len(self.gramexp.get('repeat')), 2)), mask=True)
            self.gramexp.Meas = Meas
            self.gramexp.tables = tables
        else:
            tables = self.gramexp.tables
            Meas = self.gramexp.Meas

        return tables, Meas

    @ExpeFormat.plot
    def burstiness(self, _type='all'):
        '''Zipf Analysis
           (global burstiness) + local burstiness + feature burstiness
        '''
        if self.model is None: return
        expe = self.expe
        figs = []

        Y = self._Y
        N = Y[0].shape[0]
        model = self.model

        if _type in ('global', 'all'):
            # Global burstiness
            d, dc, yerr = random_degree(Y)
            fig = plt.figure()
            plot_degree_2((d,dc,yerr), logscale=True, title=expe.title)

            figs.append(plt.gcf())

        if _type in  ('local', 'all'):
            # Local burstiness
            print ('Computing Local Preferential attachment')
            theta, phi = model.get_params()
            Y = Y[:expe.limit_gen]
            now = Now()
            if expe.model == 'immsb':
                ### Z assignement method #
                ZZ = []
                for _ in Y:
                #for _ in Y: # Do not reflect real local degree !
                    Z = np.empty((2,N,N))
                    order = np.arange(N**2).reshape((N,N))
                    if expe.symmetric:
                        triu = np.triu_indices(N)
                        order = order[triu]
                    else:
                        order = order.flatten()
                    order = zip(*np.unravel_index(order, (N,N)))

                    for i,j in order:
                        Z[0, i,j] = categorical(theta[i])
                        Z[1, i,j] = categorical(theta[j])
                    Z[0] = np.triu(Z[0]) + np.triu(Z[0], 1).T
                    Z[1] = np.triu(Z[1]) + np.triu(Z[1], 1).T
                    ZZ.append( Z )
                lgg.info('Z formation %s second', nowDiff(now))

            clustering = 'modularity'
            comm = model.communities_analysis(data=Y[0], clustering=clustering)
            print('clustering method: %s, active clusters ratio: %f' % (
                clustering,
                len(comm['block_hist']>0)/float(theta.shape[1])))

            local_degree_c = {}
            ### Iterate over all classes couple
            if expe.symmetric:
                #k_perm = np.unique( map(list, map(set, itertools.product(np.unique(clusters) , repeat=2))))
                k_perm =  np.unique(list(map(list, map(list, map(set, itertools.product(range(theta.shape[1]) , repeat=2))))))
            else:
                #k_perm = itertools.product(np.unique(clusters) , repeat=2)
                k_perm = itertools.product(range(theta.shape[1]) , repeat=2)

            fig = plt.figure()
            for i, c in enumerate(k_perm):
                if i > expe.limit_class:
                    break
                if len(c) == 2:
                    # Stochastic Equivalence (outer class)
                    k, l = c
                else:
                    # Comunnities (inner class)
                    k = l = c.pop()

                degree_c = []
                YY = []
                if expe.model == 'immsb':
                    for y, z in zip(Y, ZZ): # take the len of ZZ if < Y
                        y_c = np.zeros(y.shape)
                        phi_c = np.zeros(y.shape)
                        # UNDIRECTED !
                        phi_c[(z[0] == k) & (z[1] == l)] = 1
                        y_c = y * phi_c
                        #degree_c += adj_to_degree(y_c).values()
                        #yerr= None
                        YY.append(y_c)
                elif expe.model == 'ibp': # or Corpus !
                    for y in Y:
                        YY.append((y * np.outer(theta[:,k], theta[:,l] )).astype(int))

                d, dc, yerr = random_degree(YY)
                if len(d) == 0: continue
                plot_degree_2((d,dc,yerr), logscale=True, colors=True, line=True,
                             title='Local Preferential attachment (Stochastic Block)')
            figs.append(plt.gcf())

        ### Blockmodel Analysis
        lgg.info('Skipping Features burstiness')
        #plt.figure()
        #if expe.model == "immsb":
        #    # Class burstiness
        #    hist, label = clusters_hist(comm['clusters'])
        #    bins = len(hist)
        #    plt.bar(range(bins), hist)
        #    plt.xticks(np.arange(bins)+0.5, label)
        #    plt.xlabel('Class labels')
        #    plt.title('Blocks Size (max assignement)')
        #elif expe.model == "ibp":
        #    # Class burstiness
        #    hist, label = sorted_perm(comm['block_hist'], reverse=True)
        #    bins = len(hist)
        #    plt.bar(range(bins), hist)
        #    plt.xticks(np.arange(bins)+0.5, label)
        #    plt.xlabel('Class labels')
        #    plt.title('Blocks Size (max assignement)')

        figs.append(plt.gcf())

        if expe.write:
            from private import out
            out.write_figs(expe, figs, _fn=expe.model)
            return



    # @redondancy with burstiness !
    # in @ExpFormat.table
    def pvalue(self, _type='global'):
        """ similar to zipf but compute pvalue and print table

            Parameters
            ==========
            _type: str in [global, local, feature]
        """
        if self.model is None: return
        expe = self.expe
        figs = []

        Y = self._Y
        N = Y[0].shape[0]
        model = self.model

        Table, Meas = self.init_fit_tables(_type, Y)

        lgg.info('using `%s\' burstiness' % _type)

        if _type == 'global':

            ### Global degree
            for it_dat, data in enumerate(Y):
                d, dc = degree_hist(adj_to_degree(data), filter_zeros=True)
                gof = gofit(d, dc)
                if not gof:
                    continue

                for i, v in enumerate(Meas):
                    Table[self.corpus_pos, i, it_dat] = gof[v]

        elif _type == 'local':
            ### Z assignement method
            Y = Y[:expe.limit_gen]
            theta, _phi = model.get_params()
            K = theta.shape[1]
            now = Now()
            if expe.model == 'immsb':
                ZZ = []
                for _ in Y:
                #for _ in Y: # Do not reflect real local degree !
                    Z = np.empty((2,N,N))
                    order = np.arange(N**2).reshape((N,N))
                    if expe.symmetric:
                        triu = np.triu_indices(N)
                        order = order[triu]
                    else:
                        order = order.flatten()
                    order = zip(*np.unravel_index(order, (N,N)))

                    for i,j in order:
                        Z[0, i,j] = categorical(theta[i])
                        Z[1, i,j] = categorical(theta[j])
                    Z[0] = np.triu(Z[0]) + np.triu(Z[0], 1).T
                    Z[1] = np.triu(Z[1]) + np.triu(Z[1], 1).T
                    ZZ.append( Z )
                lgg.info('Z formation %s second', nowDiff(now))

            clustering = 'modularity'
            comm = model.communities_analysis(data=Y[0], clustering=clustering)
            print('clustering method: %s, active clusters ratio: %f' % (
                clustering,
                len(comm['block_hist']>0)/float(theta.shape[1])))

            local_degree_c = {}
            ### Iterate over all classes couple
            if expe.symmetric:
                #k_perm = np.unique( map(list, map(set, itertools.product(np.unique(clusters) , repeat=2))))
                k_perm =  np.unique(list(map(list, map(list, map(set, itertools.product(range(theta.shape[1]) , repeat=2))))))
            else:
                #k_perm = itertools.product(np.unique(clusters) , repeat=2)
                k_perm = itertools.product(range(theta.shape[1]) , repeat=2)

            for it_k, c in enumerate(k_perm):
                if it_k > expe.limit_class:
                    break
                if len(c) == 2:
                    # Stochastic Equivalence (extra class bind
                    k, l = c
                    #continue
                else:
                    # Comunnities (intra class bind)
                    k = l = c.pop()

                degree_c = []
                YY = []
                if expe.model == 'immsb':
                    for y, z in zip(Y, ZZ): # take the len of ZZ if < Y
                        y_c = y.copy()
                        phi_c = np.zeros(y.shape)
                        # UNDIRECTED !
                        phi_c[(z[0] == k) & (z[1] == l)] = 1 #; phi_c[(z[0] == l) & (z[1] == k)] = 1
                        y_c[phi_c != 1] = 0
                        #degree_c += adj_to_degree(y_c).values()
                        #yerr= None
                        YY.append(y_c)
                elif expe.model == 'ibp':
                    for y in Y:
                        YY.append((y * np.outer(theta[:,k], theta[:,l])).astype(int))

                d, dc, yerr = random_degree(YY)
                if len(d) == 0: continue
                gof =  gofit(d, dc)
                if not gof:
                    continue

                for i, v in enumerate(Meas):
                    Table[self.corpus_pos, i, it_k] = gof[v]
        elif _type == "feature":
            raise NotImplementedError

        if self._it == self.expe_size -1:
            for _model, table in self.gramexp.tables.items():

                # Mean and standard deviation
                table_mean = np.char.array(np.around(table.mean(2), decimals=3)).astype("|S20")
                table_std = np.char.array(np.around(table.std(2), decimals=3)).astype("|S20")
                table = table_mean + b' $\pm$ ' + table_std

                # Table formatting
                corpuses = _spec.name(self.gramexp.getCorpuses())
                table = np.column_stack((_spec.name(corpuses), table))
                tablefmt = 'simple'
                table = tabulate(table, headers=['__'+_model.upper()+'__']+Meas, tablefmt=tablefmt, floatfmt='.3f')
                print()
                print(table)
                if expe.write:
                    from private import out
                    fn = '%s_%s' % (_spec.name(_model), _type)
                    out.write_table(table, _fn=fn, ext='.md')

    @ExpeFormat.plot
    def draw(self):
        expe = self.expe
        if expe._mode == 'predictive':
            model = self.frontend
            y = model.data
            # move this in draw data
        elif expe._mode == 'generative':
            model = self.model
            y = model.generate(**vars(expe))

        clustering = 'modularity'
        print('@heeere, push commmunities annalysis outside static method of frontendnetwork')
        comm = model.communities_analysis(data=y, clustering=clustering)

        clusters = comm['clusters']

        draw_graph_spring(y, clusters)
        draw_graph_spectral(y, clusters)
        draw_graph_circular(y, clusters)

        #adjblocks(y, clusters=comm['clusters'], title='Blockmodels of Adjacency matrix')
        #adjshow(reorder_mat(y, comm['clusters']), 'test reordering')
        #draw_blocks(comm)

    def homo(self, _type='pearson', _sim='latent'):
        """ Hmophily test -- table output
            Parameters
            ==========
            _type: similarity type in (contengency, pearson)
            _sim: similarity metric in (natural, latent)
        """
        if self.model is None: return
        expe = self.expe
        figs = []

        Y = self._Y
        N = Y[0].shape[0]
        model = self.model

        lgg.info('using `%s\' type' % _type)

        if not hasattr(self.gramexp, 'tables'):
            corpuses = _spec.name(self.gramexp.getCorpuses())
            models = self.gramexp.getModels()
            tables = {}
            corpuses = _spec.name(self.gramexp.getCorpuses())
            for m in models:
                if _type == 'pearson':
                    Meas = [ 'pearson coeff', '2-tailed pvalue' ]
                    table = np.empty((len(corpuses), len(Meas), len(Y)))
                elif _type == 'contingency':
                    Meas = [ 'natural', 'latent', 'natural', 'latent' ]
                    table = np.empty((2*len(corpuses), len(Meas), len(Y)))
                tables[m] = table

            self.gramexp.Meas = Meas
            self.gramexp.tables = tables
            table = tables[expe.model]
        else:
            table = self.gramexp.tables[expe.model]
            Meas = self.gramexp.Meas

        if _type == 'pearson':
            lgg.info('using `%s\' similarity' % _sim)
            import scipy as sp
            # No variance for link expecation !!!
            Y = [Y[0]]

            ### Global degree
            d, dc, yerr = random_degree(Y)
            sim = model.similarity_matrix(sim=_sim)
            #plot(sim, title='Similarity', sort=True)
            #plot_degree(sim)
            for it_dat, data in enumerate(Y):
                #homo_object = data
                homo_object = model.likelihood()
                table[self.corpus_pos, :,  it_dat] = sp.stats.pearsonr(homo_object.flatten(), sim.flatten())

        elif _type == 'contingency':

            ### Global degree
            d, dc, yerr = random_degree(Y)
            sim_nat = model.similarity_matrix(sim='natural')
            sim_lat = model.similarity_matrix(sim='latent')
            step_tab = len(_spec.name(self.gramexp.getCorpuses()))
            for it_dat, data in enumerate(Y):

                #homo_object = data
                homo_object = model.likelihood()

                table[self.corpus_pos, 0,  it_dat] = sim_nat[data == 1].mean()
                table[self.corpus_pos, 1,  it_dat] = sim_lat[data == 1].mean()
                table[self.corpus_pos, 2,  it_dat] = sim_nat[data == 1].var()
                table[self.corpus_pos, 3,  it_dat] = sim_lat[data == 1].var()
                table[self.corpus_pos+step_tab, 0,  it_dat] = sim_nat[data == 0].mean()
                table[self.corpus_pos+step_tab, 1,  it_dat] = sim_lat[data == 0].mean()
                table[self.corpus_pos+step_tab, 2,  it_dat] = sim_nat[data == 0].var()
                table[self.corpus_pos+step_tab, 3,  it_dat] = sim_lat[data == 0].var()

        if self._it == self.expe_size -1:
            for _model, table in self.gramexp.tables.items():
                # Function in (utils. ?)
                # Mean and standard deviation
                table_mean = np.char.array(np.around(table.mean(2), decimals=3)).astype("|S20")
                table_std = np.char.array(np.around(table.std(2), decimals=3)).astype("|S20")
                table = table_mean + b' $\pm$ ' + table_std

                # Table formatting
                corpuses = _spec.name(self.gramexp.getCorpuses())
                try:
                    table = np.column_stack((corpuses, table))
                except:
                    table = np.column_stack((corpuses*2, table))
                tablefmt = 'simple' # 'latex'
                table = tabulate(table, headers=['__'+_model.upper()+'__']+Meas, tablefmt=tablefmt, floatfmt='.3f')
                print()
                print(table)
                if expe.write:
                    from private import out
                    fn = '%s_homo_%s' % (_spec.name(_model), _type)
                    out.write_table(table, _fn=fn, ext='.md')

    @ExpeFormat.plot('model')
    def homo_mustach(self,):
        """ Hmophily mustach
        """
        if self.model is None: return
        expe = self.expe
        figs = []

        Y = self._Y
        N = Y[0].shape[0]
        model = self.model


        if not hasattr(self.gramexp, 'tables'):
            corpuses = _spec.name(self.gramexp.getCorpuses())
            models = self.gramexp.getModels()
            tables = {}
            corpuses = _spec.name(self.gramexp.getCorpuses())
            for m in models:
                sim = [ 'natural', 'latent']
                Meas = ['links', 'non-links']
                table = {'natural': {'links':[], 'non-links':[]},'latent': {'links':[], 'non-links':[]} }
                tables[m] = table

            self.gramexp.Meas = Meas
            self.gramexp.tables = tables
            table = tables[expe.model]
        else:
            table = self.gramexp.tables[expe.model]
            Meas = self.gramexp.Meas


        ### Global degree
        d, dc, yerr = random_degree(Y)
        sim_nat = model.similarity_matrix(sim='natural')
        sim_lat = model.similarity_matrix(sim='latent')
        step_tab = len(_spec.name(self.gramexp.getCorpuses()))

        if not hasattr(self.gramexp.figs[expe.model], 'damax'):
            damax = -np.inf
        else:
            damax = self.gramexp.figs[expe.model].damax
        self.gramexp.figs[expe.model].damax = max(sim_nat.max(), sim_lat.max(), damax)
        for it_dat, data in enumerate(Y):

            #homo_object = data
            #homo_object = model.likelihood()

            table['natural']['links'].extend(sim_nat[data == 1].tolist())
            table['natural']['non-links'].extend(sim_nat[data == 0].tolist())
            table['latent']['links'].extend(sim_lat[data == 1].tolist())
            table['latent']['non-links'].extend(sim_lat[data == 0].tolist())


        if self._it == self.expe_size -1:
            for _model, table in self.gramexp.tables.items():
                ax = self.gramexp.figs[_model].fig.gca()

                bp = ax.boxplot([table['natural']['links']    ], widths=0.5,  positions = [1])
                bp = ax.boxplot([table['natural']['non-links']], widths=0.5,  positions = [2])
                bp = ax.boxplot([table['latent']['links']     ], widths=0.5,  positions = [4])
                bp = ax.boxplot([table['latent']['non-links'] ], widths=0.5,  positions = [5])

                ax.set_ylabel('Similarity')
                ax.set_xticks([1.5,4.5])
                ax.set_xticklabels((_spec.name(_model)+'/natural', _spec.name(_model)+'/latent'), rotation=15)
                ax.set_xlim(0,6)

                nbox = 4
                top = self.gramexp.figs[_model].damax
                pos = [1,2,4,5]
                upperLabels = ['links','non-links']*2
                weights = ['light', 'ultralight']
                for tick  in range(nbox):
                    ax.text(pos[tick], top+top*0.015 , upperLabels[tick],
                             horizontalalignment='center', size='x-small', weight=weights[tick%2])

                print(_model)
                t1 = sp.stats.ttest_ind(table['natural']['links'], table['natural']['non-links'])
                t2 = sp.stats.ttest_ind(table['latent']['links'], table['latent']['non-links'])
                print(t1)
                print(t2)

    @ExpeFormat.plot('corpus', 'testset_ratio')
    def roc(self, _type='testset', _ratio=20):
        ''' AUC/ROC test report '''
        from sklearn.metrics import roc_curve, auc, precision_recall_curve
        expe = self.expe
        model = self.model
        data = self.frontend.data
        _ratio = int(_ratio)
        _predictall = (_ratio >= 100) or (_ratio < 0)
        if not hasattr(expe, 'testset_ratio'):
            setattr(expe, 'testset_ratio', 20)

        ax = self.gramexp.figs[expe.corpus].fig.gca()

        if _type == 'testset':
            y_true, probas = model.mask_probas(data)
            if not _predictall:
                # take 20% of the size of the training set
                n_d =int( _ratio/100 * data.size * (1 - expe.testset_ratio/100) / (1 - _ratio/100))
                y_true = y_true[:n_d]
                probas = probas[:n_d]
            else:
                pass

        elif _type == 'learnset':
            n = int(data.size * _ratio)
            mask_index = np.unravel_index(np.random.permutation(data.size)[:n], data.shape)
            y_true = data[mask_index]
            probas = model.likelihood()[mask_index]

        fpr, tpr, thresholds = roc_curve(y_true, probas)
        roc_auc = auc(fpr, tpr)
        ax.plot(fpr, tpr, label='ROC %s (area = %0.2f)' % (expe.model, roc_auc))
        self.noplot = True

        #precision, recall, thresholds = precision_recall_curve( y_true, probas)
        #plt.plot(precision, recall, label='PR curve; %s' % (expe.model ))

        if self._it == self.expe_size -1:
            for c, f in self.gramexp.figs.items():
                ax = f.fig.gca()
                ax.plot([0, 1], [0, 1], linestyle='--', color='k', label='Luck')
                ax.legend(loc="lower right", prop={'size':10})


    def roc_evolution(self, _type='testset', _type2='max', _ratio=20, _type3='errorbar'):
        ''' AUC difference between two models against testset_ratio
            * _type : learnset/testset
            * _type2 : max/min/mean
            * _ratio : ration of the traning set to predict. If 100 _predictall will be true

        '''
        from sklearn.metrics import roc_curve, auc, precision_recall_curve
        expe = self.expe
        model = self.model
        data = self.frontend.data
        _ratio = int(_ratio)
        _predictall = (_ratio >= 100) or (_ratio < 0)
        if not hasattr(expe, 'testset_ratio'):
            setattr(expe, 'testset_ratio', 20)
            self.testset_ratio_pos = 0
        else:
            self.testset_ratio_pos = self.pt['testset_ratio']

        table, Meas = self.init_roc_tables()

        #mask = model.get_mask()
        if _type == 'testset':
            y_true, probas = model.mask_probas(data)
            if not _predictall:
                # take 20% of the size of the training set
                n_d =int( _ratio/100 * data.size * (1 - expe.testset_ratio/100) / (1 - _ratio/100))
                y_true = y_true[:n_d]
                probas = probas[:n_d]
            else:
                pass

        elif _type == 'learnset':
            n = int(data.size * _ratio)
            mask_index = np.unravel_index(np.random.permutation(data.size)[:n], data.shape)
            y_true = data[mask_index]
            probas = model.likelihood()[mask_index]

        # Just the ONE:1
        #idx_1 = (y_true == 1)
        #idx_0 = (y_true == 0)
        #size_1 = idx_1.sum()
        #y_true = np.hstack((y_true[idx_1], y_true[idx_0][:size_1]))
        #probas = np.hstack((probas[idx_1], probas[idx_0][:size_1]))

        fpr, tpr, thresholds = roc_curve(y_true, probas)
        roc_auc = auc(fpr, tpr)

        table[self.corpus_pos, self.testset_ratio_pos, self.pt['repeat'], self.model_pos] = roc_auc

        #precision, recall, thresholds = precision_recall_curve( y_true, probas)
        #plt.plot(precision, recall, label='PR curve; %s' % (expe.model ))

        if self._it == self.expe_size -1:

            # Reduce each repetitions
            take_type = getattr(np, _type2)
            t = ma.array(np.empty(table[:,:,0,:].shape), mask=True)
            t[:,:,0] = take_type(table[:, :, :, 0], -1)
            t[:,:,1] = take_type(table[:, :, :, 1], -1)
            table_mean = t.copy()
            t[:,:,0] = table[:, :, :, 0].std(-1)
            t[:,:,1] = table[:, :, :, 1].std(-1)
            table_std = t

            # Measure is comparaison of two AUC.
            id_mmsb = self.gramexp.exp_tensor['model'].index('immsb')
            id_ibp = 1 if id_mmsb == 0 else 0
            table_mean = table_mean[:,:, id_mmsb] - table_mean[:,:, id_ibp]
            table_std = table_std[:,:, id_mmsb] + table_std[:,:, id_ibp]

            if _type2 != 'mean':
                table_std = [None] * len(table_std)

            fig = plt.figure()
            corpuses = _spec.name(self.gramexp.getCorpuses())
            for i in range(len(corpuses)):
                if _type3 == 'errorbar':
                    plt.errorbar(list(map(int, Meas)), table_mean[i], yerr=table_std[i],
                                 fmt=_markers.next(),
                                 label=corpuses[i])
                elif _type3 == 'boxplot':
                    bplot = table[i,:,:,0] - table[i,:,:,1]
                    plt.boxplot(bplot.T, labels=corpuses[i])
                    fig.gca().set_xticklabels(Meas)

            plt.errorbar(Meas,[0]*len(Meas), linestyle='--', color='k')
            plt.legend(loc='upper left',prop={'size':7})

            # Table formatting
            #table = table_mean + b' $\pm$ ' + table_std
            table = table_mean

            corpuses = _spec.name(self.gramexp.getCorpuses())
            table = np.column_stack((_spec.name(corpuses), table))
            tablefmt = 'simple'
            headers = ['']+Meas
            table = tabulate(table, headers=headers, tablefmt=tablefmt, floatfmt='.3f')
            print()
            print(table)
            if expe.write:
                from private import out
                fn = '%s_%s_%s' % ( _type, _type2, _ratio)
                figs = {'roc_evolution': ExpSpace({'fig':fig, 'table':table, 'fn':fn})}
                out.write_table(figs, ext='.md')
                out.write_figs(expe, figs)

    @ExpeFormat.plot('corpus')
    def plot_some(self, _type='likelihood'):
        ''' likelihood/perplxity convergence report '''
        expe = self.expe
        model = self.model

        ax = self.gramexp.figs[expe.corpus].fig.gca()

        data = model.load_some(get='likelihood')
        burnin = 5
        ll_y = np.ma.masked_invalid(np.array(data, dtype='float'))
        ax.plot(ll_y, label=_spec.name(expe.model))

    @ExpeFormat.plot
    def clustering(self):
        algo = 'Louvain'
        algo = 'Annealing'
        data = self.frontend.data

        mat = data
        #mat = phi

        alg = getattr(A, algo)(mat)
        clusters = alg.search()

        mat = draw_boundary(alg.hi_phi(), alg.B)
        #mat = draw_boundary(mat, clusters)

        adjshow(mat, algo)
        plt.colorbar()

if __name__ == '__main__':
    from pymake.util.algo import gofit, Louvain, Annealing
    from pymake.util.math import reorder_mat, sorted_perm, categorical, clusters_hist
    from pymake.util.utils import Now, nowDiff
    import matplotlib.pyplot as plt
    from pymake.plot import plot_degree, degree_hist, adj_to_degree, plot_degree_poly, adjshow, plot_degree_2, random_degree, colored, draw_graph_circular, draw_graph_spectral, draw_graph_spring, tabulate, _markers
    import itertools

    config = dict(
        block_plot = False,
        write  = False,
        _do            = 'burstiness',
        #generative    = 'generative',
        _mode    = 'predictive',
        gen_size      = 1000,
        epoch         = 30 , #20
        limit_gen   = 5, # Local superposition !!!
        limit_class   = 30,
        spec = Exp
    )

    GramExp.generate(config, USAGE).pymake(GenNetwork)

