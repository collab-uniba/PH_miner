import json

import numpy
import pandas
import seaborn
from matplotlib import pyplot
from sklearn import metrics
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler

seed = 0

df = pandas.read_csv('../../../features.csv',
                     sep=';',
                     header=0,
                     index_col=0,
                     encoding='utf-8')

# correlation analysis
corr = df[['is_featured', 'hunter_followers', 'hunter_has_website', 'maker_followers', 'maker_has_website']].corr()
corr.style.background_gradient(cmap='coolwarm', axis=None).set_precision(2)
# Drop self-correlations
dropSelf = numpy.zeros_like(corr)
dropSelf[numpy.triu_indices_from(dropSelf)] = True
# Generate Color Map
colormap = seaborn.diverging_palette(220, 10, as_cmap=True)
# Generate Heat Map, allow annotations and place floats in map
seaborn.heatmap(corr, cmap=colormap, annot=True, fmt=".2f", mask=dropSelf)
# Apply ticks
pyplot.xticks(range(len(corr.columns)), corr.columns)
pyplot.yticks(range(len(corr.columns)), corr.columns)
pyplot.savefig('corrmatrix.png')

# build train and test sets
cols = ['hunter_followers', 'hunter_has_website', 'maker_followers', 'maker_has_website']
X = df[cols]
X_train, X_test, y_train, y_test = train_test_split(X, df.is_featured, test_size=0.25, random_state=seed,
                                                    stratify=df.is_featured)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# build logistic regression model
logreg = LogisticRegression(random_state=seed)
param_grid = {'C': [0.001, 0.01, 0.1, 1, 5, 10, 20, 50, 100]}
clf = GridSearchCV(logreg,
                   param_grid=param_grid,
                   cv=10,
                   n_jobs=-1)
logreg.fit(X_train_scaled, y_train)

# model assessment
y_pred = logreg.predict(X_test)
cnf_matrix = metrics.confusion_matrix(y_test, y_pred)
class_names = ['not featured', 'featured']  # name  of classes
_, ax = pyplot.subplots()
tick_marks = numpy.arange(len(class_names))
pyplot.xticks(tick_marks, class_names)
pyplot.yticks(tick_marks, class_names)
seaborn.heatmap(pandas.DataFrame(cnf_matrix), annot=True, cmap="YlGnBu", fmt='g')
ax.xaxis.set_label_position("top")
pyplot.tight_layout()
pyplot.title('Confusion matrix', y=1.1)
pyplot.ylabel('Actual')
pyplot.xlabel('Predicted')
pyplot.savefig('confmatrix.png')

acc = round(metrics.accuracy_score(y_test, y_pred), 3)
prec = round(metrics.precision_score(y_test, y_pred), 3)
rec = round(metrics.recall_score(y_test, y_pred), 3)
f1 = round(metrics.f1_score(y_test, y_pred), 3)

y_pred_proba = logreg.predict_proba(X_test_scaled)[::, 1]
fpr, tpr, _ = metrics.roc_curve(y_test, y_pred_proba)
auc = round(metrics.roc_auc_score(y_test, y_pred_proba), 3)
pyplot.subplots()
pyplot.plot(fpr, tpr, label="auc=" + str(round(auc, 3)))
pyplot.legend(loc=4)
pyplot.title('ROC')
pyplot.savefig('rocplot.png')

# final logging
params = {"random_state": seed,
          "model_type": "logreg",
          "scaler": "standard scaler",
          "param_grid": str(param_grid),
          "stratify": True
          }
with open('hyperparams.json', 'w') as f:
    f.write(json.dumps(params))
    f.close()

metrics = {
    "f1": f1,
    "accuracy": acc,
    "recall": rec,
    "precision": prec,
    "AUC": auc
}
with open('metrics.json', 'w') as f:
    f.write(json.dumps(metrics))
    f.close()
