import os.path as osp
import numpy as np
import street_utils as su
import my_pycaffe_utils as mpu

##
# Parameters required to specify the n/w architecture
def get_nw_prms(**kwargs):
	dArgs = edict()
	dArgs.concatLayer = 'fc6'
	dArgs.concatDrop  = False
	dArgs.contextPad  = 24
	dArgs.imSz        = 227
	dArgs.imgntMean   = False
	dArgs = mpu.get_defaults(kwargs, dArgs)
	expStr = 'cnct-%s_cnctDrp%d_contPad%d_imSz%d_imgntMean%d'\
						% (dArgs.concatLayer, dArgs.concatDrop, dArgs.contextPad,
							 dArgs.imSz, dArgs.imgntMean)
	dArgs.expStr = expStr 
	return dArgs 

##
# Parameters that specify the learning
def get_lr_prms(**kwargs):	
	dArgs = edict()
	dArgs.batchsize = 128
	dArgs.stepsize  = 20000	
	dArgs.base_lr   = 0.001
	dArgs.max_iter  = 250000
	dArgs.gamma     = 0.5
	dArgs.weight_decay = 0.0005 
	dArgs  = mpu.get_defaults(kwargs, dArgs)
	expStr = 'batchSz%d_stepSz%d_blr%.5f_mxItr%.2e_gamma%.2f_wdecay%.6f'\
					 % (dArgs.batchsize, dArgs.stepsize, dArgs.base_lr,
							dArgs.max_iter, dArgs.gamma, dArgs.weight_decay)
	dArgs.expStr = expStr
	#Make the solver 
	solArgs = edict({'test_iter': 100, 'test_interval': 1000,
						 'snapshot': 1000, 'debug_info': 'true'})
	for k in dArgs.keys():
		solArgs[k] = copy.deepcopy(dArgs[k])
	dArgs.solver = mpu.make_solver(**solArgs)	
	return dArgs 

##
# Parameters for fine-tuning
def get_finetune_prms(**kwargs):
	'''
		sourceModelIter: The number of model iterations of the source model to consider
		fine_max_iter  : The maximum iterations to which the target model should be trained.
		lrAbove        : If learning is to be performed some layer. 
		fine_base_lr   : The base learning rate for finetuning. 
 		fineRunNum     : The run num for the finetuning.
		fineNumData    : The amount of data to be used for the finetuning. 
		fineMaxLayer   : The maximum layer of the source n/w that should be considered.  
	''' 
	dArgs = edict()
	dArgs.base_lr = 0.001
	dArgs.runNum  = 1
	dArgs.maxLayer = None
	dArgs.lrAbove  = None
	dArgs.dataset  = 'sun'
	dArgs.maxIter  = 40000
	dArgs.extraFc     = False
	dArgs.extraFcDrop = False
	dArgs.sourceModelIter = 60000 
	dArgs = mpu.get_defaults(kwargs, dArgs)
 	return dArgs 


def get_caffe_prms(nwPrms, lrPrms, finePrms=None, isScratch=True, deviceId=1): 
	caffePrms = edict()
	caffePrms.deviceId  = deviceId
	caffePrms.isScratch = isScratch
	caffePrms.nwPrms    = copy.deepcopy(nwPrms)
	caffePrms.lrPrms    = copy.deepcopy(lrPrms)
	caffePrms.finePrms  = copy.deepcopy(finePrms)

	expStr = nwPrms.expStr + '/' + lrPrms.expStr
	if finePrms is not None:
		expStr = expStr + '/' + finePrms.expStr
	caffePrms['expStr'] = expStr
	caffePrms['solver'] = lrPrms.solver
	return caffePrms

def setup_experiment(prms, cPrms):
	#The size of the labels
	if prms['pose'] == 'euler':
		rotSz = 3
		trnSz = 3
	elif prms['pose'] == 'sigMotion':
		rotSz = 1
		trnSz = 2
	elif prms['pose'] == 'rotOnly':
		rotSz = 3
		trnSz = 0
	elif prms['pose'] == 'slowness':
		pass
	else:
		raise Exception('Unrecognized %s pose type' % prms['pose'])

	#The base file to start with
	baseFileStr  = 'kitti_siamese_window_%s' % cPrms['concatLayer']
	if prms['lossType'] == 'classify':
		baseStr = '_cls-trn%d-rot%d' % (trnSz, rotSz)
		if cPrms['convConcat']:
			baseStr = baseStr + '_concat_conv'
		if cPrms['isMySimple']:
			baseStr = baseStr + '_mysimple'
	elif prms['lossType'] in ['contrastive']:
		baseStr =  '_%s' % prms['lossType']
	else:
		baseStr = ''
	baseFile = os.path.join(baseFilePath, baseFileStr + baseStr + '.prototxt')
	print baseFile

	protoDef = mpu.ProtoDef(baseFile)	 
	solDef   = cPrms['solver']
	
	caffeExp = get_experiment_object(prms, cPrms)
	caffeExp.init_from_external(solDef, protoDef)

	#Get the source file for the train and test layers
	caffeExp.set_layer_property('window_data', ['generic_window_data_param', 'source'],
			'"%s"' % prms['paths']['windowFile']['train'], phase='TRAIN')
	caffeExp.set_layer_property('window_data', ['generic_window_data_param', 'source'],
			'"%s"' % prms['paths']['windowFile']['test'], phase='TEST')

	#Set the root folder
	caffeExp.set_layer_property('window_data', ['generic_window_data_param', 'root_folder'],
			'"%s"' % prms['paths']['imRootDir'], phase='TRAIN')
	caffeExp.set_layer_property('window_data', ['generic_window_data_param', 'root_folder'],
			'"%s"' % prms['paths']['imRootDir'], phase='TEST')

	if prms['randomCrop']:
		caffeExp.set_layer_property('window_data', ['generic_window_data_param', 'random_crop'],
			'true', phase='TRAIN')
		caffeExp.set_layer_property('window_data', ['generic_window_data_param', 'random_crop'],
			'true', phase='TEST')
	

	if prms['lossType'] == 'classify':
		for t in range(trnSz):
			caffeExp.set_layer_property('translation_fc_%d' % (t+1), ['inner_product_param', 'num_output'],
									prms['binCount'], phase='TRAIN')
		for r in range(rotSz):
			caffeExp.set_layer_property('rotation_fc_%d' % (r+1), ['inner_product_param', 'num_output'],
									prms['binCount'], phase='TRAIN')
	elif prms['lossType'] == 'contrastive':
		caffeExp.set_layer_property('loss', ['contrastive_loss_param', 'margin'],
								cPrms['contrastiveMargin'])
	else:
		#Regression loss basically
		#Set the size of the rotation and translation layers
		caffeExp.set_layer_property('translation_fc', ['inner_product_param', 'num_output'],
								trnSz, phase='TRAIN')
		caffeExp.set_layer_property('rotation_fc', ['inner_product_param', 'num_output'],
								rotSz, phase='TRAIN')

	if prms['lossType'] in ['contrastive']:
		pass
	else:
		#Decide the slice point for the label
		#The slice point is decided by the translation labels.
		if trnSz == 0:
			slcPt = 1
		else:
			slcPt = trnSz	
		caffeExp.set_layer_property('slice_label', ['slice_param', 'slice_point'], slcPt)	
	return caffeExp



def get_experiment_object(prms, cPrms):
	caffeExp = mpu.CaffeExperiment(prms['expName'], cPrms['expStr'], 
							prms['paths']['expDir'], prms['paths']['snapDir'],
						  deviceId=cPrms['deviceId'])
	return caffeExp



