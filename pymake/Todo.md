# WIP

# @v0.5 ?
* ipython builder helper
* web server interface and visualization  (flask...)
* spec swagger integration ? https://swagger.io
* [cli]["packet" manager]save and update the repo/ seen by pmk.
* [cli] makes able to list them (the repo), and to select one by default => it will enable to execute pmk from any path, and to move/cd inside an existing repo/.
* [cli] make `-l script [script_name]` to list mehtod, doctring, and arguement !
* [cli] pmk -l => show spec script and model.


Debug
----------
* there is a random effect when doing checknetworks zipf. Class re-ordering is stochastik f. why ?!


CLI
---
* pmk push [spec] [opts] # push expe in spec !!! (Update MAN)
* pmk fetch text/hugh (corpus etc !)
* see: https://github.com/Kaggle/kaggle-api


Core
----
* print warning on duplicate class name duplicate for Scipt, Model, Spec or Copus, but especially for Script and Spec class définition wich is more probable to happen
* Re-structure Gramexp with pymake (pymake should be design with pymake !:
        * model => gram.py
        * script => update/hist/run etc (advantage the pmk command will be available for autocompletion !
* integration of _pymake_settings (in util/) and better structure (and visibility) for gramexp core.


Frontend
--------
* merge vocabulary and frontendtext
* build_corpus and build_networks (and broken !) are identical : wrap in DataBase
* @issue42

Model
-----
* Model structure ?
* Zsampler in hdp.hdp ?
* use expe._fmt if given to format extract_csv_sample from model fmt.

* -> catch type error in manager.get_model._model.__init,:
        1. first find the number of required argument andt cut the expe surplus
        2. find a way to pass the argument  from signature **kwargs to command-line. (index the signature)
*  \_initialize  random init !!!! do cleaner init of class for empty model....
* ModelManager constructor from_model (object) (it calls \_load_model)
* ILFM create sampler and proper inhheritance form GibbsSampler.

Corpus/Dataset
--------------
* check 'jbenet/data' !
* expe_meas script ("*" specification obsolete ???? )
* CorpusModules :load from package (sklearn) and disk (
* Whoosh integration !!!
* LDA on my own paper !



@purge: 
* model/lda
* clean and homogeneize, the communities analysis framework. There is redoncdancy, and non consistent call to modularity...
* import models -> import pymake.models ?


@web3
* How should be the backend to make big scale learning with database and search engine interface...
* Spark/Hadoop interface... (hdfs = htable)
* MPI / pymake integration ?
* ipfs dataset packaging/broadcasting

@Examples
* [docsearch] own pdftotext ? quickest ? multi platform !?

