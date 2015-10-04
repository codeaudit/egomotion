import numpy as np
from easydict import EasyDict as edict
import os.path as osp
from pycaffe_config import cfg
import os
import pdb
import subprocess
import matplotlib.pyplot as plt
import mydisplay as mydisp
import h5py as h5
import pickle
import street_io as stio

def _mkdir(fName):
	if not osp.exists(fName):
		os.makedirs(fName)

def get_paths():
	paths      = edict()
	#For storing the directories
	paths.dirs = edict()
	#The raw data
	paths.dataDr  = '/data0/pulkitag/data_sets/streetview'
	paths.raw     = edict()
	paths.raw.dr  = osp.join(paths.dataDr, 'raw')
	#Processed data
	paths.proc    = edict()
	paths.proc.dr = osp.join(paths.dataDr, 'proc')
	#Raw Tar Files
	paths.tar     = edict()
	paths.tar.dr  = osp.join(paths.dataDr, 'tar')
	#The Code directory
	paths.code    = edict()
	paths.code.dr = '/home/ubuntu/code/streetview'
	#List of tar files
	paths.tar.fileList = osp.join(paths.code.dr, 'data_list.txt') 

	#Store the names of all the folders
	paths.proc.folders    = edict()
	paths.proc.folders.dr = osp.join(paths.proc.dr, 'folders')
	_mkdir(paths.proc.folders.dr)
	#Stores the folder names along with the keys
	paths.proc.folders.key  = osp.join(paths.proc.folders.dr, 'key.txt') 
	paths.proc.folders.pre  = osp.join(paths.proc.folders.dr, '%s.txt') 
	#The keys for the algined folders
	paths.proc.folders.aKey = osp.join(paths.proc.folders.dr, 'key-aligned.txt') 

	#Count info
	paths.proc.countFile = osp.join(paths.folders.dr, 'counts.h5')	

	#Label data
	paths.label    = edict()
	paths.label.dr   = osp.join(paths.proc.dr, 'labels')
	nrmlDir          = osp.join(paths.label.dr, 'nrml')
	_mkdir(nrmlDir)
	paths.label.nrml = osp.join(nrmlDir, '%s.txt')		 

	#Window data file
	paths.exp    = edict()
	paths.exp.dr = osp.join(paths.dataDr, 'exp')
	_mkdir(paths.exp.dr)
	paths.exp.window    = edict()
	paths.exp.window.dr = osp.join(paths.exp.dr, 'window-files')
	_mkdir(paths.exp.window.dr) 
	paths.exp.window.tr = osp.join(paths.exp.window.dr, 'train-%s.txt')
	paths.exp.window.te = osp.join(paths.exp.window.dr, 'test-%s.txt')
	
	return paths


##
# Get the label dimensions
def get_label_size(labelClass, labelType):
	if labelClass == 'nrml':
		if labelType == 'xyz':
			lSz = 3
		else:
			raise Exception('%s,%s not recognized' % (labelClass, labelType))
	elif labelClass == 'ptch':
		if labelType in ['wngtv', 'hngtv']:
			lSz = 3
		else:
			raise Exception('%s,%s not recognized' % (labelClass, labelType))
	elif labelClass == 'pose':
		if labelType in ['quat', 'euler']:
			lSz = 6
		else:
			raise Exception('%s,%s not recognized' % (labelClass, labelType))
	else:
		raise Exception('%s not recognized' % labelClass)
	return lSz

##
class LabelNLoss(object):
	def __init__(self, labelClass, labelType, loss):
		self.label_     = labelClass
		self.labelType_ = labelType
		self.loss_      = loss
		#augLbSz_ - augmented labelSz to include the ignore label option
		self.augLbSz_, self.lbSz_  = self.get_label_sz()
		self.lbStr_     = '%s-%s' % (self.label_, self.labelType_)
		
	def get_label_sz(self):
		lbSz = get_label_size(self.label_, self.labelType_) 
		if self.loss_ in ['l2', 'l1', 'l2-tukey']:
			augLbSz = lbSz + 1
		else:
			augLbSz = lbSz
		return augLbSz, lbSz

##
#get prms
def get_prms_v2(labels=['nrml'], labelType=['xyz'], 
						 labelNrmlz=None, 
						 crpSz=256,
						 numTrain=1e+06, numTest=1e+04,
						 lossType=['l2'],
						 trnSeq=[]):
	'''
		labels    : What labels to use - make it a list for multiple
								kind of labels
								 nrml - surface normals
									 xyz - as nx, ny, nz
								 ptch - patch matching
									 wngtv - weak negatives 
									 hngtv = hard negatices
								 pose - relative pose	
									 euler - as euler angles
									 quat  - as quaternions
		labelNrmlz : Normalization of the labels
								 	None - no normalization of labels
		lossType   : What loss is being used
								 	l2
								 	l1
								 	l2-tukey : l2 loss with tukey biweight
								 	cntrstv  : contrastive
		cropSz      : Size of the image crop to be used.
		trnSeq      : Manually specif train-sequences by hand

		NOTES
		I have tried to form prms so that they have enough information to specify
		the data formation and generation of window files. 
		randomCrop, concatLayer are properties of the training
                            they should not be in prms, but in caffePrms
	'''
	assert type(labels) == list, 'labels must be a list'
	assert type(lossType) == list, 'lossType should be list'
	assert len(lossType) == len(labels)
	assert len(labels)   == len(labelType)

	paths = get_paths()
	prms  = edict()
	prms.labels = []
	for lb,lbT,ls in zip(labels, labelType, lossType):
		prms.labels = prms.labels + LabelNLoss(lb, lbT, ls)
	prms['lbNrmlz'] = labelNrmlz
	prms['crpSz']        = crpSz
	prms['trnSeq']       = trnSeq

	prms.numSamples = edict()
	prms.numSamples.train = numTrain
	prms.numSamples.test  = numTest

	expStr = ''.join(['%s_' % lb.lbStr_ for lb in prms.labels])
	expName   = '%s_crpSz%d_nTr-%d' % (expStr, crpSz, numTrain) 
	teExpName = '%s_crpSz%d_nTe-%d' % (expStr, crpSz, numTest)
	prms['expName'] = expName

	paths['windowFile'] = {}
	paths['windowFile']['train'] = osp.join(paths['windowDir'], 'train_%s.txt' % expName)
	paths['windowFile']['test']  = osp.join(paths['windowDir'], 'test_%s.txt'  % teExpName)
	paths['resFile']       = osp.join(paths['resDir'], expName, '%s.h5')

	prms['paths'] = paths
	#Get the pose stats
	prms['poseStats'] = {}
	prms['poseStats']['mu'], prms['poseStats']['sd'], prms['poseStats']['scale'] =\
						get_pose_stats(prms)
	return prms

##
# Get the prms 
def get_prms(isAligned=True):
	prms = edict()
	prms.paths = get_paths()
	prms.isAligned = isAligned
	return prms



