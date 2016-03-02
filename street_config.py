import socket
import os
from os import path as osp
from easydict import EasyDict as edict

pths = edict()
REAL_PATH = os.path.dirname(os.path.realpath(__file__))
HOST_NAME = socket.gethostname()
DEF_DB    = osp.join(REAL_PATH, 'exp-data/db-store/%s-%s-%s-db.sqlite')
if 'ivb' in HOST_NAME:
	HOST_STR = 'nvCluster'
	pths.mainDataDr = '/scratch/pulkitag/data_sets/streetview'
	pths.expDir     = '/scratch/pulkitag/streetview/exp'
else:
	pths.mainDataDr = '/data0/pulkitag/data_sets/streetview'
	pths.expDir     = '/data0/pulkitag/streetview/exp'
	HOST_STR = HOST_NAME
DEF_DB    = DEF_DB % ('%s',HOST_STR, '%s')

#Other paths
pths.folderDerivDir = osp.join(pths.mainDataDr, 'proc2-deriv', '%s', '%s')
pths.folderProc    = osp.join(pths.mainDataDr, 'proc2', '%s')
pths.folderProcTar = osp.join(pths.mainDataDr, 'proc2-tar', '%s.tar')
pths.cwd = osp.dirname(osp.abspath(__file__))

