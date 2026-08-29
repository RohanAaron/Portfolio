import cv2 as cv
import numpy

import modern_robotics as JMR # Replace with import JMR if using Jax methods

def PlotFrame(T,ax,len,name,col):
    x = T[0:3,0]
    y = T[0:3,1]
    z = T[0:3,2]
    p = T[0:3,3]
    xend = p + len*x
    yend = p + len*y
    zend = p + len*z
    x_x = numpy.array([p[0],xend[0]])
    x_y = numpy.array([p[1],xend[1]])
    x_z = numpy.array([p[2],xend[2]])
    y_x = numpy.array([p[0],yend[0]])
    y_y = numpy.array([p[1],yend[1]])
    y_z = numpy.array([p[2],yend[2]])
    z_x = numpy.array([p[0],zend[0]])
    z_y = numpy.array([p[1],zend[1]])
    z_z = numpy.array([p[2],zend[2]])
    ax.plot(x_x, x_y, x_z, label='{}_x'.format(name), color=col)
    ax.plot(y_x, y_y, y_z, label='{}_y'.format(name), color=col)
    ax.plot(z_x, z_y, z_z, label='{}_z'.format(name), color=col)
    ax.text(xend[0], xend[1], xend[2], name, color='k')

def PlotPoint(pt,ax,col):
    ptf = pt.reshape(-1)
    ax.scatter(ptf[0],ptf[1],ptf[2],color=col)

def PlotSegmentsFlat(pts,ax,col='m'):
    x = pts[0,:]
    y = pts[1,:]
    ax.plot(x, y, color=col)

def PlotCameraFrame(T,ax,axlen,name):
    x = T[0:3,0]
    y = T[0:3,1]
    z = T[0:3,2]
    p = T[0:3,3]
    xend = p + axlen*x
    yend = p + axlen*y
    zend = p + 2*axlen*z
    x_x = numpy.array([p[0],xend[0]])
    x_y = numpy.array([p[1],xend[1]])
    x_z = numpy.array([p[2],xend[2]])
    y_x = numpy.array([p[0],yend[0]])
    y_y = numpy.array([p[1],yend[1]])
    y_z = numpy.array([p[2],yend[2]])
    z_x = numpy.array([p[0],zend[0]])
    z_y = numpy.array([p[1],zend[1]])
    z_z = numpy.array([p[2],zend[2]])
    ax.plot(x_x, x_y, x_z, color='r')
    ax.plot(y_x, y_y, y_z, color='g')
    ax.plot(z_x, z_y, z_z, color='b')
    ax.text(p[0],p[1],p[2],name)
    
def UVCoords(pt_rel_c,K = numpy.eye(3)):
    # Project a point into image coordinates. If no K provided, this returns normalized image coordinates
    uv1 = 1.0 / pt_rel_c[2] * (K @ pt_rel_c)
    return uv1

def PlotImage(ax,pt_rel_c,uvbounds,K = numpy.eye(3),col='m'):
    uv = UVCoords(pt_rel_c,K)
    ax.scatter(uv[0],uv[1],color=col)
    ax.axes.set_xlim(uvbounds[0],uvbounds[1])
    ax.axes.set_ylim(uvbounds[2],uvbounds[3])
    ax.set_aspect('equal', adjustable='box')

def draw(img, cornersf, imgptsf):
    # A different iteration of the one I wrote for the class, and probably a lot more elegant too
    corners = numpy.int_(cornersf)
    imgpts = numpy.int_(imgptsf)
    corner = tuple(corners[0].ravel())
    img = cv.line(img, corner, tuple(imgpts[0].ravel()), (0,0,255), 5)
    img = cv.line(img, corner, tuple(imgpts[1].ravel()), (0,255,0), 5)
    img = cv.line(img, corner, tuple(imgpts[2].ravel()), (255,0,0), 5)
    return img

def CVDraw(img, cornerf, axisptsf):
    # A different iteration of the one I wrote for the class, and probably a lot more elegant too
    corner = numpy.int_(cornerf)
    axispts = numpy.int_(axisptsf)
    corner = tuple(corner[0].ravel())
    img = cv.line(img, corner, tuple(axispts[0].ravel()), (0,0,255), 5)
    img = cv.line(img, corner, tuple(axispts[1].ravel()), (0,255,0), 5)
    img = cv.line(img, corner, tuple(axispts[2].ravel()), (255,0,0), 5)
    return img

def MakeK(fx,fy,cx,cy):
    # Make an intrinsic matrix from pixel/m focal lengths and pixel center coordinates
    K = numpy.zeros((3,3))
    K[0,0] = fx
    K[1,1] = fy
    K[0,2] = cx
    K[1,2] = cy
    K[2,2] = 1
    return K

def MakeCamera(fovx,widthpix,heightpix):
    cx = widthpix/2
    cy = heightpix/2

    fx = cx / numpy.tan(fovx / 2)
    fy = fx

    K = MakeK(fx,fy,cx,cy)
    uvbounds = [0,widthpix,0,heightpix]
    return K,uvbounds




class Factor:
    wseFunction = None # Returns scalar weighted square error of this factor
    AbFunction = None # Returns whitened linearized Jacobian (A) and error (b)
    retractionFunction = None # Returns the generalized "Xc + delt" if delt is on a manifold
    stateIndices = None # The indices in the overall graph A and b for the state
    factorIndices = None # The indices in the overall graph A and b for the factors
    reducedStateIndices = None # The indices in the overall graph A and b for the factors if manifolds are used
    wseArgs = None # Extra arguments passed to wseFunction
    AbArgs = None # Extra arguments passed to AbFunction
    retractionArgs = None # Extra arguments passed to retractionFunction

    def __init__(self,wseFunction,AbFunction,retractionFunction,stateIndices,factorIndices,reducedStateIndices,wseArgs,AbArgs,retractionArgs):
        self.wseFunction = wseFunction
        self.AbFunction = AbFunction
        self.retractionFunction = retractionFunction
        self.stateIndices = stateIndices
        self.factorIndices = factorIndices
        self.reducedStateIndices = reducedStateIndices
        self.wseArgs = wseArgs
        self.AbArgs = AbArgs
        self.retractionArgs = retractionArgs

    # The below gets called if print is called on an instance of this
    def __str__(self):
        thestr = "WSE function: {}\nAb function: {}Retraction function: {}\nState indices: {}\nFactor indices: {}\nReduced state indices: {}\nWSE arguments: {}\nAbArgs: {}\nRetraction args: {}\n".format(self.wseFunction,self.AbFunction,self.retractionFunction,self.stateIndices,self.factorIndices,self.reducedStateIndices,self.wseArgs,self.AbArgs,self.retractionArgs)
        return thestr

# This just sums all the errors in the factor list
def FactorGraphWSEClass(Xc,FactorList):
    totalError = 0
    for factorinfo in FactorList:
        fn = factorinfo.wseFunction
        inds = factorinfo.stateIndices
        fn_args = factorinfo.wseArgs
        e = fn(Xc[inds],*fn_args)
        totalError = totalError + e
    return totalError

def FactorGraphAbRef(Xc,FactorList,reducedStateCount,factorCount):
    A = numpy.zeros((factorCount,reducedStateCount))
    b = numpy.zeros(factorCount)
    # A = jax.new_ref(numpy.zeros((factorCount,reducedStateCount)))
    # b = jax.new_ref(numpy.zeros(factorCount))
    for factorinfo in FactorList:
        fn = factorinfo.AbFunction
        stateInds = factorinfo.stateIndices
        factorInds = factorinfo.factorIndices
        reducedStateInds = factorinfo.reducedStateIndices
        fn_args = factorinfo.AbArgs
        Af,bf = fn(Xc[stateInds],*fn_args)

        for i in range(factorInds.size):
            A[factorInds[i], reducedStateInds] = Af[i,:]
            b[factorInds[i]] = bf[i]
    return A,b
    # return jax.freeze(A), jax.freeze(b)

def FactorGraphRetraction(Xc,delt,FactorList,stateCount):
    Xnew = numpy.zeros(stateCount)
    for factorinfo in FactorList:
        retrfn = factorinfo.retractionFunction
        stateInds = factorinfo.stateIndices
        reducedStateInds = factorinfo.reducedStateIndices
        retr_args = factorinfo.retractionArgs
        # Xnew = Xnew.at[stateInds].set(retrfn(Xc[stateInds],delt[reducedStateInds],*retr_args))
        Xnew[stateInds] = retrfn(Xc[stateInds],delt[reducedStateInds],*retr_args)
    return Xnew




def GaussNewtonSolver(Xinit,WSEfn,WSEfn_args,Abfn,Abfn_args,Retfn,Retfn_args,tol,maxsteps=100,printall=False):
    Xc = numpy.copy(Xinit)
    currenterror = WSEfn(Xc,*WSEfn_args)

    if printall:
        print("Error = {}".format(currenterror))

    for i in range(maxsteps):
        A_f, b_f = Abfn(Xc,*Abfn_args)

        # The below lines implement the Normal Equations to find the delt
        ata = A_f.T @ A_f
        atb = A_f.T @ b_f
        delt = numpy.linalg.lstsq(A_f, b_f, rcond=None)[0]
        

        # REPLACE BELOW WITH REDUCED
        Xc = Retfn(Xc, delt, *Retfn_args)
        # Xc = Xc + delt

        # Get the current error and the size of the last step taken normalized to an edge
        currenterror = WSEfn(Xc,*WSEfn_args)
        deltedgenorm = numpy.sqrt((delt.T @ delt)/len(delt))

        if printall:
            print("Step: {}, Error = {}, DeltaEdgeNorm = {}".format(i, currenterror, deltedgenorm))

        if deltedgenorm < tol:
            break
    return Xc


def LevenbergMarquardtSolver(Xinit,WSEfn,WSEfn_args,Abfn,Abfn_args,Retfn,Retfn_args,tol,maxsteps=100,printall=False,origgamma=0.0001,gammadiv=10.0,gammamult=10.0):
    # gamma = 1000. # Variable step size, also known as lambda in the literature
    gamma = origgamma

    Xc = numpy.copy(Xinit)
    currenterror = WSEfn(Xc,*WSEfn_args)

    if printall:
        print("Error = {}".format(currenterror))
    
    i = -1
    while True:
        i = i + 1

        currenterror = WSEfn(Xc,*WSEfn_args)

        A_f, b_f = Abfn(Xc,*Abfn_args)

        # The below lines implement the Normal Equations to find the delt
        ata = A_f.T @ A_f + gamma * numpy.diag(numpy.diag(A_f.T @ A_f))
        atb = A_f.T @ b_f
        delt = numpy.linalg.solve(ata,atb)

        # REPLACE BELOW WITH REDUCED
        Xnew = Retfn(Xc, delt, *Retfn_args)
        # Xnew = Xc + delt
        newerror = WSEfn(Xnew,*WSEfn_args)

        if newerror < currenterror:
            Xc = Xnew
            # REPLACE BELOW WITH REDUCED
            # Xc = Xc + delt
            gamma = gamma / gammadiv
            if i >= maxsteps:
                print("Step: {}, Error = {}".format(i, newerror))
                break
        else:
            gamma = gamma * gammamult

        # Get the current error and the size of the last step taken normalized to an edge
        deltedgenorm = numpy.sqrt((delt.T @ delt)/len(delt))

        if printall:
            if newerror < currenterror:
                print("Step: {}, Error = {}, DeltaEdgeNorm = {}".format(i, newerror, deltedgenorm))
            else:
                print("Step: {}".format(i))

        if deltedgenorm < tol:
            break

    return Xc

#@jit
def T12toT(T12):
    T = numpy.zeros((4,4))
    # T = T.at[3,3].set(1.0)
    # T = T.at[0:3,0:4].set(T12.reshape((3,4)))
    T[3,3]=1.0
    T[0:3,0:4]=T12.reshape((3,4))
    return T

#@jit
def TtoT12(T):
    return T[0:3,:].flatten()

#@jit
def FrameToTAA(T_s_this):
    p = T_s_this[0:3,3]
    aa = JMR.so3ToVec(JMR.MatrixLog3(T_s_this[0:3,0:3]))
    return numpy.array([p[0],p[1],p[2],aa[0],aa[1],aa[2]])

#@jit
def TAAToFrame(TAA_s_this):
    T_s_this = numpy.eye(4)
    # T_s_this = T_s_this.at[0:3,0:3].set(JMR.MatrixExp3(JMR.VecToso3(TAA_s_this[3:6])))
    # T_s_this = T_s_this.at[0:3,3].set(TAA_s_this[0:3])
    T_s_this[0:3,0:3]=JMR.MatrixExp3(JMR.VecToso3(TAA_s_this[3:6]))
    T_s_this[0:3,3]=TAA_s_this[0:3]
    return T_s_this

#@jit
def FrameError(T_this,T_that):
    # Both arguments must have the same base frame (e.g. global)
    # Find that in this frame, then convert to translation-axis-angle
    T_error = JMR.TransInv(T_this) @ T_that
    return FrameToTAA(T_error)

#@jit
def OneToOneRetraction(Xc,delt):
    # For Euclidean handling of deltas found by GN and LM solvers, replaces "Xc + delt" for a particular factor
    return Xc + delt



#@jit
def PixelsFromKnownPose(T_s_group, T_s_camera, M_group_corner, K):
    # Use this function if the camera pose is known with certainty, e.g. first photo at the origin

    # Project a point into image coordinates. If no K provided, this returns normalized image coordinates
    M_camera_corner = JMR.TransInv(T_s_camera) @ (T_s_group @ M_group_corner)

    uv1 = 1.0 / M_camera_corner[2] * (K @ M_camera_corner[0:3])
    return uv1[0:2]

#@jit
def PixelsFromKnownPoseFlat(T_s_group_12, T_s_camera, M_group_corner, K):
    T_s_group = T12toT(T_s_group_12)
    return PixelsFromKnownPose(T_s_group, T_s_camera, M_group_corner, K)

#@jit
def PixelsFromKnownPosePerturbed(w_s_group, T_s_group_12_0, T_s_camera, M_group_corner, K):
    T_s_group = T12toT(T_s_group_12_0) @ JMR.MatrixExp6(JMR.VecTose3(w_s_group))
    return PixelsFromKnownPose(T_s_group, T_s_camera, M_group_corner, K)

#@jit
def D_PixelsFromKnownPosePerturbed(w_s_group, T_s_group_12_0, T_s_camera, M_group_corner, K):
    # Because of the NearZero used in JMR for MatrixExp3 and MatrixExp6, it's actually better
    # to do an old-fashioned finite difference for the Jacobian instead of jacrev or jacfwd
    jac = numpy.zeros((2,6)) # uv by w
    h = 0.001
    for i in range(6):
        hvec = numpy.zeros(6)
        # hvec = hvec.at[i].set(h)
        hvec[i]=h
        jach = (PixelsFromKnownPosePerturbed(w_s_group + hvec, T_s_group_12_0, T_s_camera, M_group_corner, K) - PixelsFromKnownPosePerturbed(w_s_group - hvec, T_s_group_12_0, T_s_camera, M_group_corner, K)) / (2*h)
        # jac = jac.at[:,i].set(jach)
        jac[:,i]=jach
    return jac

#@jit
def PixelsFromKnownPoseError(T_s_group_12_0, T_s_camera, M_group_corner, K, z_camera_corner):
    return PixelsFromKnownPoseFlat(T_s_group_12_0, T_s_camera, M_group_corner, K) - z_camera_corner

#@jit
def PixelsFromKnownPoseWSE(T_s_group_12_0, T_s_camera, M_group_corner, K, z_camera_corner, Q_uv):
    e = PixelsFromKnownPoseError(T_s_group_12_0, T_s_camera, M_group_corner, K, z_camera_corner).reshape((2,1))
    return (e.T @ numpy.linalg.inv(Q_uv) @ e)[0,0]

#@jit
def PixelsFromKnownPoseAb(T_s_group_12_0, T_s_camera, M_group_corner, K, z_camera_corner, Q_uv):
    Qinvsqrt = numpy.linalg.cholesky(numpy.linalg.inv(Q_uv)).T
    A = Qinvsqrt @ D_PixelsFromKnownPosePerturbed(numpy.zeros(6),T_s_group_12_0, T_s_camera, M_group_corner, K)
    b = Qinvsqrt @ (-PixelsFromKnownPoseError(T_s_group_12_0, T_s_camera, M_group_corner, K, z_camera_corner))
    return A,b

#@jit
def PixelsFromKnownPoseRetraction(T_s_group_12_0, w_s_group):
    T_s_group = T12toT(T_s_group_12_0) @ JMR.MatrixExp6(JMR.VecTose3(w_s_group))
    return T_s_group[0:3,:].flatten()



#@jit
def Pixels(T_s_group, T_s_camera, M_group_corner, K):
    # This can use the known pose version since nothing is changed
    return PixelsFromKnownPose(T_s_group, T_s_camera, M_group_corner, K)

#@jit
def PixelsFlat(T_s_group_12_T_s_camera_12, M_group_corner, K):
    T_s_group = T12toT(T_s_group_12_T_s_camera_12[0:12])
    T_s_camera = T12toT(T_s_group_12_T_s_camera_12[12:24])
    return Pixels(T_s_group, T_s_camera, M_group_corner, K)

#@jit
def PixelsPerturbed(w_s_group_s_camera, T_s_group_12_0_T_s_camera_12_0, M_group_corner, K):
    T_s_group = T12toT(T_s_group_12_0_T_s_camera_12_0[0:12]) @ JMR.MatrixExp6(JMR.VecTose3(w_s_group_s_camera[0:6]))
    T_s_camera = T12toT(T_s_group_12_0_T_s_camera_12_0[12:24]) @ JMR.MatrixExp6(JMR.VecTose3(w_s_group_s_camera[6:12]))
    return Pixels(T_s_group, T_s_camera, M_group_corner, K)

#@jit
def D_PixelsPerturbed(w_s_group_s_camera, T_s_group_12_0_T_s_camera_12_0, M_group_corner, K):
    # Because of the NearZero used in JMR for MatrixExp3 and MatrixExp6, it's actually better
    # to do an old-fashioned finite difference for the Jacobian instead of jacrev or jacfwd
    jac = numpy.zeros((2,12)) # uv by w
    h = 0.001
    for i in range(12):
        hvec = numpy.zeros(12)
        # hvec = hvec.at[i].set(h)
        hvec[i]=h
        jach = (PixelsPerturbed(w_s_group_s_camera + hvec, T_s_group_12_0_T_s_camera_12_0, M_group_corner, K) - PixelsPerturbed(w_s_group_s_camera - hvec, T_s_group_12_0_T_s_camera_12_0, M_group_corner, K)) / (2*h)
        # jac = jac.at[:,i].set(jach)
        jac[:,i]=jach
    return jac

#@jit
def PixelsError(T_s_group_12_0_T_s_camera_12_0, M_group_corner, K, z_camera_corner):
    return PixelsFlat(T_s_group_12_0_T_s_camera_12_0, M_group_corner, K) - z_camera_corner

#@jit
def PixelsWSE(T_s_group_12_0_T_s_camera_12_0, M_group_corner, K, z_camera_corner, Q_uv):
    e = PixelsError(T_s_group_12_0_T_s_camera_12_0, M_group_corner, K, z_camera_corner).reshape((2,1))
    return (e.T @ numpy.linalg.inv(Q_uv) @ e)[0,0]

#@jit
def PixelsAb(T_s_group_12_0_T_s_camera_12_0, M_group_corner, K, z_camera_corner, Q_uv):
    Qinvsqrt = numpy.linalg.cholesky(numpy.linalg.inv(Q_uv)).T
    A = Qinvsqrt @ D_PixelsPerturbed(numpy.zeros(12),T_s_group_12_0_T_s_camera_12_0, M_group_corner, K)
    b = Qinvsqrt @ (-PixelsError(T_s_group_12_0_T_s_camera_12_0, M_group_corner, K, z_camera_corner))
    return A,b

#@jit
def PixelsRetraction(T_s_group_12_0_T_s_camera_12_0, w_s_group_s_camera):
    T_s_group = T12toT(T_s_group_12_0_T_s_camera_12_0[0:12]) @ JMR.MatrixExp6(JMR.VecTose3(w_s_group_s_camera[0:6]))
    T_s_camera = T12toT(T_s_group_12_0_T_s_camera_12_0[12:24]) @ JMR.MatrixExp6(JMR.VecTose3(w_s_group_s_camera[6:12]))
    T_s_group_12_T_s_camera_12 = numpy.zeros(24)
    # T_s_group_12_T_s_camera_12 = T_s_group_12_T_s_camera_12.at[0:12].set(T_s_group[0:3,:].flatten())
    # T_s_group_12_T_s_camera_12 = T_s_group_12_T_s_camera_12.at[12:24].set(T_s_camera[0:3,:].flatten())
    T_s_group_12_T_s_camera_12[0:12]=T_s_group[0:3,:].flatten()
    T_s_group_12_T_s_camera_12[12:24]=T_s_camera[0:3,:].flatten()
    return T_s_group_12_T_s_camera_12


class GroupPhotoData:
    cameraindex = None
    K = None
    markerindex = None # Should start at 0 and go up incrementally
    markerID = None # This corresponds to a label
    M_group_corners = None # Points with respect to group origin
    M_pixels = None # The pixel coordinates
    T_camera_group = None # From PnP, the group with respect to camera (first guess)
    UVbounds = None
    distortion = None

    def __init__(self,cameraindex,K,markerindex,markerID,M_group_corners,M_pixels,T_camera_group,UVbounds=None,distortion=None):
        self.cameraindex = cameraindex
        self.K = K
        self.markerindex = markerindex # Should start at 0 and go up incrementally
        self.markerID = markerID # This corresponds to a label
        self.M_group_corners = M_group_corners # Points with respect to group origin
        self.M_pixels = M_pixels # The pixel coordinates
        self.T_camera_group = T_camera_group # From PnP, the group with respect to camera (first guess)
        self.UVbounds = UVbounds
        self.distortion = distortion
    
    def __str__(self):
        thestr = ""
        thestr = thestr + "cameraindex: {}\n".format(self.cameraindex)
        thestr = thestr + "K: {}\n".format(self.K)
        thestr = thestr + "markerindex: {}\n".format(self.markerindex)
        thestr = thestr + "markerID: {}\n".format(self.markerID)
        thestr = thestr + "M_group_corners: {}\n".format(self.M_group_corners)
        thestr = thestr + "M_pixels: {}\n".format(self.M_pixels)
        thestr = thestr + "T_camera_group: {}\n".format(self.T_camera_group)
        thestr = thestr + "UVbounds: {}\n".format(self.UVbounds)
        thestr = thestr + "distortion: {}\n".format(self.distortion)
        return thestr




def MakeCameraGroupInitialGuess(allgroupphotos, fixedcameraindex, T_s_fixed):
    numcameras = max([d.cameraindex for d in allgroupphotos]) + 1
    numgroups = max([d.markerindex for d in allgroupphotos]) + 1
    T_s_cameras = numpy.zeros((numcameras,4,4))
    T_s_groups = numpy.zeros((numgroups,4,4))

    # T_s_cameras = T_s_cameras.at[fixedcameraindex,:,:].set(T_s_fixed)
    T_s_cameras[fixedcameraindex,:,:]=T_s_fixed

    # Intuition is that closer frames are more accurate, so use distance as a priority value, with distance accumulating
    cameraq = [(0.0,fixedcameraindex)]
    markerq = []

    # Don't redo calculations if indices have already been seen
    resolvedcameras = [fixedcameraindex]
    resolvedgroups = []

    while len(cameraq) > 0 or len(markerq) > 0:
        
        # Handle all the new groups seen by the newest visited cameras
        while len(cameraq) > 0:
            dist, thiscameraindex = cameraq.pop(0)
            for d in allgroupphotos:
                if d.cameraindex == thiscameraindex:
                    if d.markerindex not in resolvedgroups:
                        resolvedgroups.append(d.markerindex)
                        T_s_group = T_s_cameras[d.cameraindex,:,:] @ d.T_camera_group
                        groupdist = dist + numpy.linalg.norm(T_s_group[0:3,3])
                        # T_s_groups = T_s_groups.at[d.markerindex,:,:].set(T_s_group)
                        T_s_groups[d.markerindex,:,:]=T_s_group

                        markerplaceinq = [ind for ind in range(len(markerq)) if markerq[ind][1] == d.markerindex]
                        if len(markerplaceinq) > 0:
                            if (groupdist) < markerq[markerplaceinq][0]:
                                markerq.pop(markerplaceinq[0])
                                markerq.append((groupdist, d.markerindex))
                        else:
                            markerq.append((groupdist, d.markerindex))
        markerq.sort()

        # Handle all the new cameras seen by the newest visited groups
        while len(markerq) > 0:
            dist, thismarkerindex = markerq.pop(0)
            for d in allgroupphotos:
                if d.markerindex == thismarkerindex:
                    if d.cameraindex not in resolvedcameras:
                        resolvedcameras.append(d.cameraindex)
                        T_s_camera = T_s_groups[d.markerindex,:,:] @ JMR.TransInv(d.T_camera_group)
                        cameradist = dist + numpy.linalg.norm(T_s_camera[0:3,3])
                        # T_s_cameras = T_s_cameras.at[d.cameraindex,:,:].set(T_s_camera)
                        T_s_cameras[d.cameraindex,:,:]=T_s_camera

                        cameraplaceinq = [ind for ind in range(len(cameraq)) if cameraq[ind][1] == d.cameraindex]
                        if len(cameraplaceinq) > 0:
                            if (cameradist) < cameraq[cameraplaceinq][0]:
                                cameraq.pop(cameraplaceinq[0])
                                cameraq.append((cameradist, d.cameraindex))
                        else:
                            cameraq.append((cameradist, d.cameraindex))
        cameraq.sort()

    return T_s_groups, T_s_cameras




def GetGroupCameraIndices(theindex, isgroup, numgroups, numcameras):
    if isgroup:
        fullstateindices = numpy.array([12*(theindex) + x for x in range(12)])
        reducedstateindices = numpy.array([6*(theindex) + x for x in range(6)])
        return (fullstateindices, reducedstateindices)
    else:
        # Assume camera 0 is fixed, and therefore not part of the calculation
        fullstateindices = numpy.array([12*(numgroups + theindex - 1) + x for x in range(12)])
        reducedstateindices = numpy.array([6*(numgroups + theindex - 1) + x for x in range(6)])
        return (fullstateindices, reducedstateindices)
