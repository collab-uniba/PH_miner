# ORDINE DI ESECUZIONE PER L'ANALISI DEI FATTORI DI SUCCESSO
* Eseguire il file *extraction.py* presente nella cartella `features` per poter effettuare l'estrazione dal database delle varie metriche relative ai cinque fattori di successo

Da questo momento in poi eseguire i **Jupyter Notebook** presenti nella cartella `notebook` nel seguente ordine<sup>1</sup>:

1. notebook *normality_test.ipynb* presente nella cartella `normality_test` per poter effettuare il test di normalità delle feature numeriche presenti nel dataset

2. notebook *logistic_regression_notebook.ipynb* presente nella cartella `initial_model_logistic_regression` per poter costruire il primo modello della regressione logistica

3. notebook *data_analysis.ipynb* presente nella cartella `data_analysis` per effettuare l'analisi qualitativa dei maker che sono attivi nei commenti nel proprio post

4. Nella cartella `final_model_logistic_regression` eseguire: <br><br>
&nbsp;4.1 notebook *logistic_regression_notebook.ipynb* per poter costruire il modello finale della regressione logistica <br><br>
&nbsp;4.2 notebook *AUC_ROC_Curve.ipynb* per poter realizzare la curva ROC e calcolare il valore AUC includendo la feature score nelle varibili indipendenti nella formula della regressione logistica<br><br>
&nbsp;4.3 notebook *AUC_ROC_Curve_without_score.ipynb* per poter realizzare la curva ROC e calcolare il valore AUC escludendo la feature score dalle variabili indipendenti nella formula della regressione logistica

5. notebook *Boruta_feature_selection_notebook.ipynb* presente nella cartella `feature_selection` per effettuare feature selection e controllare in questo modo quali altre feature, oltre a score, risultano più influenti e hanno maggiore potere discriminante

<sup>1</sup> <span style="font-size: 14px">I jupyter notebook *extraction_features_notebook.ipynb* e *discretization_features_notebook.ipynb* sono stati utilizzati solo come prova per l'estrazione del topic dominante  in ogni post (effettuando il topic modeling) e per discretizzare le variabili continue. Una volta eseguito il file *extraction.py* non c'è bisogno di eseguire questi due notebook, in quanto l'estrazione delle metriche e la discretizzazione sono già stati effettuati.</span>


