
import argparse
from decimal import Decimal
from sigopt import Connection
import sys
sys.path.insert(0, "..")
sys.path.insert(0, "../..")
sys.path.insert(0, "../../../")
import os
import shutil

from train import train
# from forceconv import *
from forcepai import ForcePai

parser = argparse.ArgumentParser()
parser.add_argument("-logdir", type=str, default='mkxu/fpai_ethanol')
parser.add_argument("-device", type=int, default=0)
parser.add_argument("-data", type=str, default='ethanol_dft')
parser.add_argument("-epoch", type=int, default=2000)
parser.add_argument("-id", type=int, default=None)
parser.add_argument("--dry_run", action='store_true', default=False)
params = vars(parser.parse_args())

if params['dry_run']:
    token = 'GMBSZWXFWPHHUCXSDYLLCBBCBTKZUBVCBQRMCMXEFNEYGCFY'
    params['epoch'] = 100
    n_obs = 2
else:
    token = 'JGTKFUYDJMOKBMDFXICMGNEFBXOOSIPAVSGUWPSMJCVDWYMA'
    n_obs = 1000


# Generate parameter range 
logdir = params['logdir']

#Intiailize connections 
conn = Connection(client_token=token)

if params['id'] == None:
    experiment = conn.experiments().create(
        name=logdir,
        metrics=[dict(name='loss', objective='minimize')],
        parameters=[
            # dict(name='feat_dim', type="int", bounds=dict(min=6, max=9), default_value=7),  # 64->512
            # dict(name='num_conv', type='int', bounds=dict(min=2, max=4), default_value=3),
            dict(name='n_rbf', type='int', bounds=dict(min=2, max=6), default_value=3),  # 4->32
            dict(name='batch_size', type='int', bounds=dict(min=2, max=6), default_value=3),  # 4->32
            dict(name='cutoff', type='double', bounds=dict(min=4.0, max=8.0), default_value=7),
            dict(name='lr', type='double', bounds=dict(min=1e-4, max=1e-3), default_value=5e-4, transformation="log"),
            # dict(name='conv_dropout', type='double', bounds=dict(min=0.0, max=0.1), default_value=0.0, precision=1),
            dict(name='readout_dropout', type='double', bounds=dict(min=0.0, max=0.5), default_value=0.0),
        ],
        observation_budget=n_obs, # how many iterations to run for the optimization
        parallel_bandwidth=10,
    )

elif type(params['id']) == int:
    experiment = conn.experiments(params['id']).fetch()


while experiment.progress.observation_count < experiment.observation_budget:

    suggestion = conn.experiments(experiment.id).suggestions().create()

    # tranform parameter s
    trainparam = suggestion.assignments
    ## exp process
    # trainparam['feat_dim'] = 2**trainparam['feat_dim']
    trainparam['n_rbf'] = 2**trainparam['n_rbf']
    trainparam['batch_size'] = 2**trainparam['batch_size']
    ## constant
    trainparam['conv_dropout'] = 0.0
    trainparam['num_conv'] = 3
    trainparam['feat_dim'] = 256
    print(trainparam)

    test_mae = train(params, trainparam, suggestion.id, ForcePai, params['epoch'])
    # updat result to server
    conn.experiments(experiment.id).observations().create(
      suggestion=suggestion.id,
      value=test_mae,
    )

    experiment = conn.experiments(experiment.id).fetch()

