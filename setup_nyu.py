import pickle
import scipy.io as sio
import scipy.misc as scm
import numpy as np
import street_config as cfg
from easydict import EasyDict as edict
import matplotlib.pyplot as plt
import os
from os import path as osp
import other_utils as ou
import pascal_exp as pep
import subprocess
import pdb
import cv2
from sklearn.cluster import KMeans
import copy
import math
import nn_utils as nnu

REAL_PATH = cfg.REAL_PATH
DEF_DB    = cfg.DEF_DB % ('default', '%s')

def get_paths():
	expDir, dataDir = cfg.pths.nyu.expDr, cfg.pths.nyu.dataDr
	pth = edict()	
	pth.exp = edict()
	pth.exp.dr= expDir
	#Snapshots
	pth.exp.snapshot    = edict()
	pth.exp.snapshot.dr = osp.join(pth.exp.dr, 'snapshot')
	ou.mkdir(pth.exp.snapshot.dr)
	#Nearest Neighbor experiments
	pth.exp.nn   = edict()
	pth.exp.nn.dr  = osp.join(pth.exp.dr, 'nn')
	#Nearesest neigbor using netName %s
	pth.exp.nn.feats = osp.join(pth.exp.nn.dr, 'features/im%04d.p') 
	pth.exp.nn.net   = osp.join(pth.exp.nn.dr, 'net_%s.pkl') 
	pth.exp.nn.results = osp.join(pth.exp.nn.dr, 'results/%s.pkl') 
	pth.exp.nn.netTrainOnly   = osp.join(pth.exp.nn.dr, 'net_%s_trainonly.pkl') 
	pth.exp.nn.resultsTrainOnly = osp.join(pth.exp.nn.dr, 'results/%s_trainonly.pkl') 
	#Get the label-stats
	#Get the label-stats
	pth.exp.labelStats  = osp.join(pth.exp.dr, 'label_stats.pkl')
	#Normal centers
	pth.exp.nrmlClusters = osp.join(pth.exp.dr, 'nrml_clusters.pkl')
	pth.exp.nrmlClustersReSz = osp.join(pth.exp.dr, 'nrml_clusters_resize.pkl')
	#info label for the experiment
	#pth.exp.lbInfo     = osp.join(pth.exp.dr, 'label_info', dPrms.expStr, 'lbinfo.pkl') 
	#ou.mkdir(osp.dirname(pth.exp.lbInfo))
	#Results
	pth.exp.results = edict()
	pth.exp.results.dr   = osp.join(pth.exp.dr, 'results', '%s')
	pth.exp.results.file = osp.join(pth.exp.results.dr, 'iter%d.pkl') 
	#Data files
	pth.data      = edict()
	pth.data.dr   = dataDir	
	pth.data.splits    = osp.join(dataDir, 'splits.mat')
	pth.data.gtnrmlRaw = osp.join(dataDir, 'normals_gt', 'normals','%04d.png')
	pth.data.maskRaw   = osp.join(dataDir, 'normals_gt', 'masks','%04d.png')
	pth.data.gtnrml    = osp.join(dataDir, 'normals_gt_renamed', 'normals', '%04d.png')
	pth.data.imRaw     = osp.join(dataDir, 'ims', 'im%04d.jpg')
	#base net files
	pth.baseProto = osp.join(REAL_PATH, 'base_files', '%s.prototxt')
	#Window files
	windowDr      = osp.join(REAL_PATH, 'pose-files')
	pth.window  = edict()
	#Window files stores theta in degrees
	#pth.window.train = osp.join(windowDr, 'euler_train_pascal3d_imSz%d_pdSz%d.txt')
	#pth.window.test  = osp.join(windowDr, 'euler_test_pascal3d_imSz%d_pdSz%d.txt')
	#pth.window.train = pth.window.train % (dPrms.imCutSz, dPrms.imPadSz)
	#pth.window.test  = pth.window.test %  (dPrms.imCutSz, dPrms.imPadSz)
	return pth	

#original files are named starting with 0, rename them to start with 1
def rename_gt_normals(pths=None):
	if pths is None:
		pths = get_paths()
	for i in range(0,1449):
		rawName = pths.data.gtnrmlRaw % i
		finName = pths.data.gtnrml  % (i+1)		 
		subprocess.check_call(['cp %s %s' % (rawName, finName)], shell=True)

def show_images(pths=None):
	plt.ion()
	if pths is None:
		pths = get_paths()
	for i in range(100):
		im = scm.imread(pths.data.imRaw % (i+1))
		plt.imshow(im)		
		plt.show()
		plt.draw()
		ip = raw_input()
		if ip == 'q':
			return			

def blah():
	pass
	

def compute_normal_centers(isReSz=False):
	'''
		nrmls: N x 3 where N is the number of points
	'''
	pth       = get_paths()
	numIm     = 1449
	nSamples  = 20000
	K         = 20
	nrmls     = np.zeros((nSamples, 3))
	randState = np.random.RandomState(11)
	#Load all masks
	masks, ims = [], []
	for nn in range(numIm):
		mkName	= pth.data.maskRaw % nn
		mask    = scm.imread(mkName)
		mask    = mask[45:471, 41:601]
		if isReSz:
			mask  = cv2.resize(mask, (20,20))
		masks.append(mask.reshape((1,) + mask.shape))
		imName  = pth.data.gtnrmlRaw % nn
		im      = scm.imread(imName)/255.
		im      = im[45:471, 41:601,:]	
		if isReSz:
			im  = cv2.resize(im, (20,20))
		ims.append(im.reshape((1,) + im.shape))
	for ns in range(nSamples):
		while True:
			n = randState.randint(numIm)
			#Load he mask
			mask    = masks[n].squeeze()
			cmsm    = np.cumsum(mask)
			cmsm    = cmsm/float(cmsm[-1])
			rd      = randState.rand()
			try:
				idx     = pep.find_bin_index(cmsm, rd)
				yIdx, xIdx = np.unravel_index(idx, mask.shape)
			except:
				pdb.set_trace()
			#print (n, rd, idx)
			if not mask[yIdx][xIdx]:
				xIdx += 1
			if xIdx == mask.shape[1]:
				continue
			break
		assert mask[yIdx][xIdx], '%d, %d' % (yIdx, xIdx)
		#Load the image
		im      = ims[n].squeeze()
		nrl     = im[yIdx, xIdx,:].squeeze()
		sqSum   = np.sqrt(np.sum(nrl * nrl))
		nrl     = nrl / sqSum
		nrmls[ns,:] = nrl
	#K-Means clustering	
	cls = KMeans(n_clusters=20, random_state=randState)	
	cls.fit(nrmls)
	nrmlCenters = cls.cluster_centers_
	pickle.dump({'clusters': nrmlCenters}, open(pth.exp.nrmlClusters, 'w')) 


def load_clusters():
	pths = get_paths()
	dat  = pickle.load(open(pths.exp.nrmlClusters, 'r'))
	dat  = dat['clusters']
	Z    = np.sum(dat * dat, 1)
	N,_  = dat.shape
	dat  = dat / Z.reshape(N,1)
	return dat
		

def get_cluster_index(dat, clusters):
	dist = clusters - dat
	dist = np.sum(dist * dist, 1)
	return np.argmin(dist)


def normals2cluster(nrml, mask, clusters):
	nrml     = copy.deepcopy(nrml)/255.
	mask     = copy.deepcopy(mask)
	mask     = mask.astype(np.float32)
	mask     = cv2.resize(mask, (20, 20))
	nrml     = cv2.resize(nrml, (20, 20))
	mask     = mask > 0.5
	nrmlCluster = 20 * np.ones((20, 20))
	for i in range(20):
		for j in range(20): 
			if mask[i,j]:
				nrmlCluster[i,j] = get_cluster_index(nrml[i,j], clusters)
	return nrmlCluster			


def normals2cluster_fullim(nrml, mask, clusters):
	nrml     = copy.deepcopy(nrml)
	mask     = copy.deepcopy(mask)
	nrmlCluster = 20 * np.ones(mask.shape)
	for i in range(mask.shape[0]):
		for j in range(mask.shape[1]): 
			if mask[i,j]:
				nrmlCluster[i,j] = get_cluster_index(nrml[i,j], clusters)
	return nrmlCluster			


def normals2cluster_from_idx(n, clusters=None):
	if clusters is None:
		clusters = load_clusters()
	pths = get_paths()
	nrml = read_normals_from_idx(n)
	mask = read_mask_from_idx(n)
	return normals2cluster(nrml, mask, clusters)

	
def cluster2normals(nrmlCluster, clusters=None):
	if clusters is None:
		clusters = load_clusters()
	H, W  = nrmlCluster.shape	
	nrml = np.zeros((20,20,3)) 
	for i in range(H):
		for j in range(W):
			idx = nrmlCluster[i,j]
			if idx == 20:
				continue
			else:
				nrml[i,j,:] = clusters[idx,:]
	return nrml


def vis_clusters():
	pth = get_paths()
	clusters = load_clusters()
	fig = plt.figure()
	ax1  = fig.add_subplot(211)
	ax2  = fig.add_subplot(212)
	for n in range(10):
		#Cluster to normals
		nrmlCluster = assign_normals_cluster(n, clusters)
		nrml  = cluster2normals(nrmlCluster)
		ax1.imshow(nrml, interpolation='none')	
		#Actual normals
		pths = get_paths()
		nrmlFile = pth.data.gtnrmlRaw % n
		nrml     = scm.imread(nrmlFile)
		nrml     = nrml[45:471, 41:601]
		nrml     = cv2.resize(nrml, (20, 20))
		ax2.imshow(nrml, interpolation='none')
		plt.savefig('tmp/nrmls/vis%d.png' % n)	
	

def get_set_index(setName='train'):
	pths = get_paths()
	data = sio.loadmat(pths.data.splits)
	if setName == 'train':
		idxs = data['trainNdxs']
	elif setName == 'test':
		idxs = data['testNdxs']
	else:
		raise Exception('set %s not recognized' % setName)	
	#Conver to pythonic format
	idxs = idxs.squeeze()
	idxs = [i-1 for i in idxs]
	return idxs
	
	
def read_file(fName):
	data    = scm.imread(fName)
	data    = data[45:471, 41:601]
	return data

def read_file_bgr(fName):
	data    = scm.imread(fName)
	data    = data[45:471, 41:601]
	return data[:,:,[2, 1, 0]]


def read_normals_from_idx(n):
	pths = get_paths()
	nrmlFile = pths.data.gtnrmlRaw % n
	return read_file(nrmlFile)

def read_mask_from_idx(n):
	pths = get_paths()
	maskFile = pths.data.maskRaw % n
	mask = scm.imread(maskFile, mode='L')
	mask = mask.astype(np.bool)
	mask = mask[45:471, 41:601]
	#print (maskFile, np.sum(mask))
	return mask

def read_image_from_idx(n):
	pths   = get_paths()
	imFile = pths.data.imRaw % (n+1)
	return read_file_bgr(imFile) 

## evaluate a single file
def eval_single(gt, pd, mask=None, clusters=None):
	gt   = copy.deepcopy(gt)/255.0
	pd   = copy.deepcopy(pd)/255.0 
	eps = 1e-8
	gtZ = np.sqrt(np.sum(gt * gt, axis=2)) + eps
	pdZ = np.sqrt(np.sum(pd * pd, axis=2)) + eps
	gtZ = gtZ.reshape(gtZ.shape + (1,))
	pdZ = pdZ.reshape(pdZ.shape + (1,))
	gt  = gt / gtZ
	pd  = pd / pdZ
	assert gt.shape == pd.shape
	theta = np.minimum(1,np.maximum(-1, np.sum(gt * pd, axis=2)))
	acos  = np.vectorize(math.acos)
	theta = acos(theta)
	theta = 180. * (theta / np.pi)
	if not theta.shape[0:2] == gt.shape[0:2]:
		pdb.set_trace()
	assert theta.shape == gt.shape[0:2]
	#Binned errors
	if clusters is not None:
		nrmlCls = normals2cluster_fullim(gt, mask, clusters)
		nCls    = clusters.shape[0]
		errs    = []
		for n in range(nCls):
			err = theta[nrmlCls==n]
			errs.append(err)
	#Find errors asfter masking out pixels for which no depth info
	N = np.sum(mask)
	if mask is not None:
		theta = theta[mask]
	if not N == len(theta):
		print ('Something ois weird')
		pdb.set_trace()
	if clusters is None:
		return theta
	else:
		return theta, errs

def demo_eval():
	for n in range(10):
		nrml  = read_normals_from_idx(n)
		theta = eval_single(nrml, nrml)
		print (np.median(theta), np.min(theta), np.max(theta)) 

#Makes it very easy to evaluate non-parametric methods
def eval_from_index(gtIdx, pdIdx, clusters=None):
	gtNrml = read_normals_from_idx(gtIdx)
	mask   = read_mask_from_idx(gtIdx)
	pdNrml = read_normals_from_idx(pdIdx)
	return eval_single(gtNrml, pdNrml, mask, clusters=clusters)

def eval_random():
	testIdx = get_set_index('test') 
	thetas  = np.array([])
	for i,n in enumerate(testIdx):
		if np.mod(i,100)==1:
			print (i)
		#Prediction
		while True:
			idx    = np.random.randint(1449)		
			if not idx == n:
				break
		tht  = eval_from_index(n, idx)
		thetas = np.concatenate((thetas, tht))
	print (np.median(thetas), np.min(thetas), np.max(thetas)) 
	return thetas


#Evaluation using random nearest neigbors
def load_features_all(netName):
	'''
		caffe_lsm_conv5: learning to see by moving
		caffe_video_fc7: CMU ICCV15 paper
		caffe_alex_pool5: alexnet pool5
		caffe_alex_fc7: alexnet fc7
		caffe_pose_fc5: caffe posenet fc5
		torch_pose_fc6: torch posenet fc6
		caffe_street_fc6: 08mar16 models - caffe pose 
		caffe_PoseMatch_fc5: joint pose and match
	'''
	pths = get_paths()
	feats = []
	N = 1449
	print ('Loading Features')
	for n in range(N):
		#The features are stored in matlab indexing
		fName = pths.exp.nn.feats % (n+1)
		dat   = pickle.load(open(fName, 'r'))
		ff    = dat[netName].flatten()
		ff = ff.reshape((1, ff.shape[0]))
		feats.append(ff)
	feats = np.concatenate(feats)
	print ('Loading Features Done')
	return feats

#Save the indexes of nearest neigbors
def save_nn_indexes(netName='caffe_street_fc6', feats=None, trainOnly=False):
	'''
		trainOnly: True - only consider examples for trainset for NN
               False - consider al examples except the query for NN
	'''
	pths  = get_paths()
	if feats is None:
		feats = load_features_all(netName)
	testIdx   = get_set_index('test')
	trainIdx  = get_set_index('train')
	testFeats  = [feats[i] for i in testIdx]
	trainFeats = [feats[i] for i in trainIdx]   
	N     = 1449
	nnIdx = []
	for n in range(N):
		if np.mod(n,100)==1:
			print (n)
		ff = feats[n].flatten()
		ff = ff.reshape((1, ff.shape[0]))
		if trainOnly:
			idx = nnu.find_nn(ff, trainFeats, numNN=11)
			idx = idx[0]
			idx = [trainIdx[i] for i in idx]
			if idx[0] == n:
				idx = idx[1:]
			else:
				idx = idx[0:10]
		else:
			idx = nnu.find_nn(ff, feats, numNN=11)
			idx = idx[0][1:]
		nnIdx.append(idx)
	if trainOnly:
		oFile = pths.exp.nn.netTrainOnly % netName
	else:
		oFile = pths.exp.nn.net % netName
	ou.mkdir(osp.dirname(oFile))
	pickle.dump({'nn': nnIdx}, open(oFile, 'w'))


def get_all_netnames():
	netName = ['caffe_lsm_conv5', 'caffe_video_fc7',
            'caffe_alex_pool5', 'caffe_alex_fc7',
             'caffe_pose_fc5' , 'torch_pose_fc6',
             'caffe_street_fc6', 'caffe_PoseMatch_fc5']
	return netName

def save_nn_indexes_all(trainOnly=False):
	netName = get_all_netnames()
	for n in netName:
		print (n)
		save_nn_indexes(n, trainOnly=trainOnly)

def load_nn_indexes(netName, trainOnly=False):
	pths    = get_paths()
	if trainOnly:
		netFile = pths.exp.nn.netTrainOnly % netName
	else:
		netFile = pths.exp.nn.net % netName
	dat     = pickle.load(open(netFile, 'r'))
	nnIdx   = dat['nn']
	return nnIdx

def vis_nn():
	#Chose the test images for which visualization needs to be made
	randState = np.random.RandomState(13)
	testIdx = get_set_index('test')
	perm    = np.random.permutation(len(testIdx))
	testIdx = [testIdx[p] for p in perm]
	testIdx = testIdx[0:10]
	#Load the nn data	
	netNames = ['caffe_alex_pool5', 'caffe_alex_fc7',
              'torch_pose_fc6', 'caffe_street_fc6']
	nnIdx = edict()
	for net in netNames:
		nnIdx[net] = load_nn_indexes(net)
	#Create the figures
	fig = plt.figure()
	plt.tick_params(
    axis='x',          # changes apply to the x-axis
    which='both',      # both major and minor ticks are affected
    bottom='off',      # ticks along the bottom edge are off
    top='off',         # ticks along the top edge are off
    labelbottom='off')
	ax  = edict()
	for net in netNames:
		ax[net] = []
		for i in range(7):
			axs = fig.add_subplot(1,7,i+1)
			ax[net].append(fig.add_subplot(1,7, i+1))


#Save nearest neighbor results for a certain net
def save_nn_results(netName, trainOnly=False):
	pths   = get_paths()
	nnIdx   = load_nn_indexes(netName, trainOnly=trainOnly)
	testIdx = get_set_index('test')
	clusters = load_clusters()
	nCl      = clusters.shape[0]
	print ('Num clusters: %d' % nCl)
	thetas  = np.array([])
	binErrs = []
	for n in range(nCl):
		binErrs.append(np.array([]))
	for i,tIdx in enumerate(testIdx):
		if np.mod(i,100)==1:
			print (i)
		#print (tIdx, nnIdx[tIdx][0])
		tht, binErr  = eval_from_index(tIdx, nnIdx[tIdx][0], clusters=clusters)
		thetas = np.concatenate((thetas, tht))
		for n in range(nCl):
			if len(binErr[n]) > 0:
				binErrs[n] = np.concatenate((binErrs[n], binErr[n]))
	if trainOnly:
		oFile = pths.exp.nn.resultsTrainOnly % netName
	else:
		oFile = pths.exp.nn.results % netName
	print ('Saving to: %s' % oFile)
	ou.mkdir(osp.dirname(oFile))
	pickle.dump({'thetas': thetas, 'binErrs': binErrs, 
      'clusters': clusters}, open(oFile, 'w'))
	print (netName)
	print (np.median(thetas), np.min(thetas), np.max(thetas))

#Save nearest neighbor results for all the nets
def save_nn_results_all(trainOnly=False):
	netName = get_all_netnames()
	for n in netName:
		print (n)
		save_nn_results(n, trainOnly=trainOnly)

#Read the nearest neighbor results for a certain net
def read_nn_results(netName, trainOnly=False):
	pths  = get_paths()
	if trainOnly:
		oFile = pths.exp.nn.resultsTrainOnly % netName
	else:
		oFile = pths.exp.nn.results % netName
	dat   = pickle.load(open(oFile, 'r'))
	theta = np.array(dat['thetas'])
	print (theta.shape, len(theta)/(426 * 560))
	md    = np.median(theta)
	N     = len(theta)
	err11 = np.sum(theta <= 11.25)/float(N)
	err22 = np.sum(theta <= 22.5)/float(N)
	err30 = np.sum(theta <=30)/float(N)
	print ('%s, %.1f, %.1f, %.1f, %.1f' % (netName, md, 100*err11, 100*err22, 100*err30))

def read_nn_results_all(trainOnly=False):
	for n in get_all_netnames():
		read_nn_results(n, trainOnly=trainOnly)


def debug_num_pixels(netName):
	pths    = get_paths()
	netFile = pths.exp.nn.net % netName
	dat     = pickle.load(open(netFile, 'r'))
	nnIdx   = dat['nn']
	testIdx = get_set_index('test')
	thetas  = np.array([])
	nSum = 0
	for i,tIdx in enumerate(testIdx):
		if np.mod(i,100)==1:
			print (i)
		#print (tIdx, nnIdx[tIdx][0])
		tht  = eval_from_index(tIdx, nnIdx[tIdx][0])
		mask = read_mask_from_idx(tIdx)
		N    = np.sum(mask)
		if not N== len(tht):
			pdb.set_trace()
		nSum += N
	return (nSum)

def debug_mask():
	for i in range(100):	
		mask = read_mask_from_idx(0)

