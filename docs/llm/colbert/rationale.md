<h2> ColBERT Agent </h2>

ColBERT is a _fast_ and _accurate_ retrieval model, enabling scalable BERT-based search over large text collections in tens of milliseconds.

Our ColBERT agent is based on [colBERT V2](https://github.com/stanford-futuredata/ColBERT), version 0.2.0.
They already include a very detailed documentation, so we will not go into detail here.


When installing this program as a service, Deberta V2 by default will not compile as TorchScript requires the source code to be available.
For this reason, I have added a patch in order to switch @torch.jit.script for @torch.jit._script_if_tracing. The model
will supposedly be slower, but it will work. If you want to use the model in TorchScript, you can remove the patch from the code.

On src/llm/ColBERT/modelling/hf_colbert.py:


```python
def script_method(fn, _rcb=None):
    return fn


def script(obj, optimize=True, _frames_up=0, _rcb=None):
    return obj


import torch.jit
script_method1 = torch.jit.script_method
script1 = torch.jit.script_if_tracing
torch.jit.script_method = script_method
torch.jit.script = script
```


<h3> ColBERT Agent Configuration </h3>

The configuration file is located in the `llm/ColBERT` folder, and is named `config.json`. It contains the following parameters:

* `k`: The number of documents to retrieve from the index.
* `queries`: The queries to use for the query-document retrieval. This is a list of strings.
* `kmeans_iters`: The number of iterations to use for the k-means clustering algorithm.
* `document_max_length`: The maximum length of the document to index.
