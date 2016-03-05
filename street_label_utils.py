from easydict import EasyDict as edict
import street_config as cfg
import my_exp_config as mec
from transforms3d.transforms3d import euler as t3eu
import numpy as np
from scipy import linalg as linalg

class LabelPrms(object):
	dbName = cfg.DEF_DB % ('label', 'default') 
	def __init__(self):
		self.lb = edict()
		self.lb['type'] = 'default'

	def get_lbsz(self):
		return 1	

	def get_lbstr(self):
		print (self.dbName)
		return mec.get_sql_id(self.dbName, self.lb)


def get_mat_dist(m1, m2):
	return linalg.norm(linalg.logm(np.dot(np.transpose(m1), m2)), ord='fro')

##
#Get the difference in pose of two configurations
def get_pose_delta(lbInfo, rot1, rot2, pt1=None, pt2=None,
             isRadian=False, debugMode=False):
	'''
		rot1, rot2: rotations in degrees
		pt1,  pt2 : the location of cameras expressed as (lat, long, height)
		the output labels are provided in radians
	'''
	rotOrder = 'szxy'
	#rotOrder = 'syxz'
	if not isRadian:
		y1, x1, z1 = map(lambda x: x*np.pi/180., rot1)
		y2, x2, z2 = map(lambda x: x*np.pi/180., rot2)
	rMat1      = t3eu.euler2mat(x1, y1, z1, rotOrder)
	rMat2      = t3eu.euler2mat(x2, y2, z2, rotOrder)
	dRot       = np.dot(rMat2, rMat1.transpose())
	#pitch, yaw, roll are rotations around x, y, z axis
	pitch, yaw, roll = t3eu.mat2euler(dRot, rotOrder)
	_, thRot  = t3eu.euler2axangle(pitch, yaw, roll, rotOrder)
	lb = None
	#Figure out if the rotation is within or outside the limits
	if lbInfo.maxRot is not None:
		if (np.abs(thRot) > lbInfo.maxRot):
				return lb
	#Calculate the rotation
	if lbInfo['angleType'] == 'euler':
		if lbInfo['dof'] <= 3:
			lb = (yaw, pitch, roll)
		elif lbInfo['dof'] in [5,6]:
			g1 = spd.GeoCoordinate.from_point(pt1)
			g2 = spd.GeoCoordinate.from_point(pt2)
			dx, dy, dz = g1.get_displacement_vector(g2)
			if lbInfo['dof'] == 5:
				lb = (yaw, pitch, dx, dy, dz)
			else:
				lb = (yaw, pitch, roll, dx, dy, dz)
	elif lbInfo['angleType'] == 'quat':
		quat = t3eu.euler2quat(pitch, yaw, roll, axes=rotOrder)
		q1, q2, q3, q4 = quat
		lb = (q1, q2, q3, q4)
	else:
		raise Exception('Type not recognized')
	if not debugMode:	
		return lb
	else:
		dRotEst = t3eu.euler2mat(pitch, yaw, roll, rotOrder)
		print (get_mat_dist(dRot, dRotEst))
		rot2Est = np.dot(dRotEst, rMat1)
		print (get_mat_dist(rMat2, rot2Est))
			


class PosePrms(LabelPrms):
	dbName = cfg.DEF_DB % ('label', 'pose') 
	def __init__(self, angleType='euler', dof=3):
		LabelPrms.__init__(self)
		self.lb['type']      = 'pose'
		self.lb['angleType'] = angleType
		self.lb['dof']       = dof
		self.lb['maxRot']    = None 

	def get_lbsz(self):
		if self.lb.angleType == 'euler':
			return self.lb.dof
		else:
			raise Exception('Angle Type %s not recognized' % self.lb.angleType)