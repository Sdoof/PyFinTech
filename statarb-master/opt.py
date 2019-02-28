#!/usr/bin/env python

import sys
import numpy
import math
import openopt

import util

max_sumnot = 50.0e6
max_expnot = 0.048
max_posnot = 0.0048
max_trdnot = 1.0
max_iter = 500
min_iter = 500
plotit = False

hard_limit = 1.02
kappa = 4.3e-5

#HAND-TWEAKED PARAMETERS TO MATCH CURRENT TRADING BEHAVIOR
slip_alpha = 1.0
slip_delta = 0.25
slip_beta = 0.6
slip_gamma = 0.3
slip_nu = 0.14
execFee= 0.00015

num_secs = 0
num_factors = 0
stocks_ii = 0
factors_ii = 0
zero_start = 0

#prefix them with g_ to avoid errors
g_positions = None
g_lbound = None
g_ubound = None
g_mu = None
g_rvar = None
g_advp = None
g_borrowRate = None
g_price = None
g_factors = None
g_fcov = None
g_vol = None
g_mktcap = None
g_advpt = None
numpy.set_printoptions(threshold=float('nan'))

p=None

class Terminator():
    def __init__(self, lookback, stopThreshold, minIter):
        self.iter = 0
        self.objValues = []
        self.maxAtLookback = None
        self.lookback = lookback
        self.stopThreshold = stopThreshold
        self.minIter = minIter
        
    def __call__(self, p):
        self.iter += 1
        #infeasible points are disregarded from computations
        if p.rk <= 0:
            self.objValues.append(p.fk)
        else:
            self.objValues.append(float('inf'))
        
        #don't start checking until we have seen at least min iters
        if self.iter <= self.lookback + self.minIter:
            return False
        #only check every 10 iterations
        if self.iter % 10 != 0:
            return False
        
        #internally it works as a minimizer, so take that into account by getting the minimum values and inverting them
        #each iteration is not guaranteed to increase the obj function values.
        curr = -min(self.objValues[-self.lookback:-1])
        prev = -min(self.objValues[0:(-self.lookback -1)])
        
        if numpy.isinf(prev):
            print "Haven't found a feasible point yet"
            return False
        elif numpy.isinf(curr):
            print "We are probably diverging, but we are staying the course for a huge comeback"
            return False
        
        if self.iter % 10 == 0:
            print "Current improvement after {} iterations is {}".format(self.lookback, float(curr-prev))
        if curr - prev < self.stopThreshold:
            print "Current improvement after {} iterations is {}".format(self.lookback, float(curr-prev))
            return True
        else:
            return False
        

def printinfo(target, kappa, slip_gamma, slip_nu,positions, mu, rvar, factors, fcov, advp, advpt, vol, mktcap, brate, price, execFee, untradeable_info):
    clong=0
    cshort=0
    tlong=0
    tshort=0
    diff=0
    for ii in xrange(len(positions)):
        if positions[ii]>=0:
            clong+=positions[ii]
        else:
            cshort-=positions[ii]
    for ii in xrange(len(target)):
        if target[ii]>=0:
            tlong+=target[ii]
        else:
            tshort-=target[ii]
        diff+=abs(target[ii]-positions[ii])
    print "[CURRENT] Long: {:.0f}, Short: {:.0f}, Total: {:.0f}".format(clong,cshort,clong+cshort)
    print "[TARGET]  Long: {:.0f}, Short: {:.0f}, Total: {:.0f}".format(tlong,tshort,tlong+tshort)
    print "Dollars traded: {:.0f}".format(diff)
    __printpointinfo("Current",positions,  kappa, slip_gamma, slip_nu, positions, mu, rvar, factors, fcov, advp, advpt, vol, mktcap, brate, price, execFee, untradeable_info)
    __printpointinfo("Optimum",target,  kappa, slip_gamma, slip_nu, positions, mu, rvar, factors, fcov, advp, advpt, vol, mktcap, brate, price, execFee, untradeable_info)

def __printpointinfo(name,target, kappa, slip_gamma, slip_nu, positions, mu, rvar, factors, fcov, advp, advpt, vol, mktcap, brate, price, execFee, untradeable_info):
    untradeable_mu, untradeable_rvar, untradeable_loadings = untradeable_info[0], untradeable_info[1], untradeable_info[2]
    
    loadings = numpy.dot(factors, target)+untradeable_loadings
    utility1 = numpy.dot(target, mu) + untradeable_mu
    utility2 = kappa * ( untradeable_rvar + numpy.dot(target * rvar, target) + numpy.dot(numpy.dot(loadings, fcov), loadings) )
    utility3 = slippageFuncAdv(target, positions, advp, advpt, vol, mktcap, slip_gamma, slip_nu)
    utility4 = costsFunc(target, positions, brate, price, execFee)
    var = kappa * numpy.dot(target * rvar, target)
    covar = kappa * numpy.dot(numpy.dot(loadings, fcov), loadings)
    print "@{}: total={:.0f}, mu={:.0f}, risk={:.0f}, slip={:.2f}, costs={:.2f}, ratio={:.3f}, var={:.0f}, covar={:.0f}".format(name,utility1-utility2-utility3-utility4, utility1,utility2,utility3,utility4,utility1/utility2, var, covar)

def slippageFuncAdv(target, positions, advp, advpt, vol, mktcap, slip_gamma, slip_nu):
    newpos_abs = abs(target-positions)
    I = slip_gamma * vol * (newpos_abs/advp) * (mktcap/advp) ** slip_delta 
    J = I/2 + slip_nu * vol * (newpos_abs/advpt) ** slip_beta
    slip = J * newpos_abs
    return slip.sum()

def slippageFunc_grad(target, positions, advp, advpt, vol, mktcap, slip_gamma, slip_nu):
    newpos = target-positions
    Id = .5 * slip_gamma * vol * (1/advp) * (mktcap/advp) ** slip_delta  
    Jd = (Id + slip_nu * vol * (1 + slip_beta) * (abs(newpos)/advpt) ** slip_beta) * numpy.sign(newpos)
    return Jd

def costsFunc(target, positions, brate, price, execFee):
    costs = execFee * numpy.dot(1.0/price, abs(target - positions))
    #ATTENTION! borrow costs are negative, negative times negative gives a positive cost
    #XXX add back once we have borrow costs!
    #costs += numpy.dot(brate, numpy.minimum(0.0, target))
    return costs

def costsFunc_grad(target, positions, brate, price, execFee):
    grad = execFee * numpy.sign(target - positions) / price
#    for i in xrange(len(grad)):
        #ATTENTION!  borrow costs are negative, derivative is negative (more positive position, lower costs)
#        if target[i] <=0 : grad[i] += brate[i]
    return grad

def objective(target, kappa, slip_gamma, slip_nu, positions, mu, rvar, factors, fcov, advp, advpt, vol, mktcap, brate, price, execFee, untradeable_info):
    return objective_detail(target, kappa, slip_gamma, slip_nu, positions, mu, rvar, factors, fcov, advp, advpt, vol, mktcap, brate, price, execFee, untradeable_info)[0]

def objective_detail(target, kappa, slip_gamma, slip_nu, positions, mu, rvar, factors, fcov, advp, advpt, vol, mktcap, brate, price, execFee, untradeable_info):
    untradeable_mu, untradeable_rvar, untradeable_loadings = untradeable_info[0], untradeable_info[1], untradeable_info[2]
    
    # objective function to be minimized (negative utility)    
    loadings = numpy.dot(factors, target) + untradeable_loadings

    tmu = numpy.dot(target, mu) + untradeable_mu
    tsrisk = kappa * (untradeable_rvar + numpy.dot(target * rvar, target))
    tfrisk = kappa * numpy.dot(numpy.dot(loadings, fcov), loadings) 
    tslip = slippageFuncAdv(target, positions, advp, advpt, vol, mktcap, slip_gamma, slip_nu)
    tcosts = costsFunc(target, positions, brate, price, execFee)

    utility = tmu
    utility -= tsrisk
    utility -= tfrisk
    utility -= tslip
    utility -= tcosts

    return (utility, tmu, tsrisk, tfrisk, tslip, tcosts)

def objective_grad(target, kappa, slip_gamma, slip_nu, positions, mu, rvar, factors, fcov, advp, advpt, vol, mktcap, brate, price, execFee, untradeable_info):
    untradeable_mu, untradeable_rvar, untradeable_loadings = untradeable_info[0], untradeable_info[1], untradeable_info[2]
    
    F = factors
    Ft = numpy.transpose(F)
    grad = numpy.zeros(len(target))
    grad += mu
    grad -= 2 * kappa * (rvar * target + numpy.dot(Ft, numpy.dot(fcov, numpy.dot(F, target) + untradeable_loadings)))
    grad -= slippageFunc_grad(target, positions, advp, advpt, vol, mktcap, slip_gamma, slip_nu)
    grad -= costsFunc_grad(target, positions, brate, price, execFee)
    return grad

# constrain <= 0
def constrain_by_capital(target, positions, max_sumnot, factors, lbexp, ubexp, max_trdnot_hard):
    ret = abs(target).sum() - max_sumnot
    return ret

def constrain_by_capital_grad(target, positions, max_sumnot, factors, lbexp, ubexp, max_trdnot_hard):
    return numpy.sign(target)

#def constrain_by_exposures(target, positions, max_sumnot, factors, lbexp, ubexp, max_trdnot_hard):
#    exposures = numpy.dot(factors, target)
#    ret = max(numpy.r_[lbexp - exposures, exposures - ubexp])
#    return ret

### UGH this is ignored!
def constrain_by_trdnot(target, positions, max_sumnot, factors, lbexp, ubexp, max_trdnot_hard):
    ret = abs(target - positions).sum() - max_trdnot_hard
    return ret

def setupProblem(positions, mu, rvar, factors, fcov, advp, advpt, vol, mktcap, borrowRate, price, lb, ub, Ac, bc, lbexp, ubexp, untradeable_info, sumnot, zero_start):
    if zero_start > 0: 
        p = openopt.NLP(goal='max', f=objective, df=objective_grad, x0=numpy.zeros(len(positions)), lb=lb, ub=ub, A=Ac, b=bc, plot=plotit)
    else: 
        p = openopt.NLP(goal='max', f=objective, df=objective_grad, x0=positions, lb=lb, ub=ub, A=Ac, b=bc, plot=plotit)
    p.args.f = (kappa, slip_gamma, slip_nu, positions, mu, rvar, factors, fcov, advp, advpt, vol, mktcap, borrowRate, price, execFee, untradeable_info)
    p.args.df = (kappa, slip_gamma, slip_nu, positions, mu, rvar, factors, fcov, advp, advpt, vol, mktcap, borrowRate, price, execFee, untradeable_info)
    p.c = [constrain_by_capital]
    p.dc = [constrain_by_capital_grad]
    p.args.c = (positions, sumnot, factors, lbexp, ubexp, sumnot)
    p.args.dc = (positions, sumnot, factors, lbexp, ubexp, sumnot)
    p.ftol = 1e-6
    p.maxFunEvals = 1e9
    p.maxIter = max_iter
    p.minIter = min_iter
    p.callback = Terminator(50, 10, p.minIter)
    
    return p

def optimize():
    global p
    
    tradeable, untradeable = getUntradeable()
    
    t_num_secs = len(tradeable)
    t_positions = numpy.copy(g_positions[tradeable])
    t_factors = numpy.copy(g_factors[:, tradeable])
    t_lbound = numpy.copy(g_lbound[tradeable])
    t_ubound = numpy.copy(g_ubound[tradeable])
    t_mu = numpy.copy(g_mu[tradeable])
    t_rvar = numpy.copy(g_rvar[tradeable])
    t_advp = numpy.copy(g_advp[tradeable])

    t_advpt = numpy.copy(g_advpt[tradeable])
    t_vol = numpy.copy(g_vol[tradeable])
    t_mktcap = numpy.copy(g_mktcap[tradeable])

    t_borrowRate = numpy.copy(g_borrowRate[tradeable])
    t_price = numpy.copy(g_price[tradeable]) 

    u_positions = numpy.copy(g_positions[untradeable])
    u_factors = numpy.copy(g_factors[:, untradeable])
    u_mu = numpy.copy(g_mu[untradeable])
    u_rvar = numpy.copy(g_rvar[untradeable])
        
    exposures = numpy.dot(g_factors, g_positions)
    lbexp = exposures
    lbexp = numpy.minimum(lbexp, -max_expnot * max_sumnot)
    lbexp = numpy.maximum(lbexp, -max_expnot * max_sumnot * hard_limit)
    ubexp = exposures
    ubexp = numpy.maximum(ubexp, max_expnot * max_sumnot)
    ubexp = numpy.minimum(ubexp, max_expnot * max_sumnot * hard_limit)
    #offset the lbexp and ubexp by the untradeable positions
    untradeable_exposures = numpy.dot(u_factors, u_positions)
    lbexp -= untradeable_exposures
    ubexp -= untradeable_exposures

    sumnot = abs(g_positions).sum()
    sumnot = max(sumnot, max_sumnot)
    sumnot = min(sumnot, max_sumnot * hard_limit)
    #offset sumnot by the untradeable positions
    sumnot -= abs(u_positions).sum()

    lb = numpy.maximum(t_lbound, -max_posnot * max_sumnot)
    ub = numpy.minimum(t_ubound, max_posnot * max_sumnot)
        
    #exposure constraints
    Ac = numpy.zeros((2 * num_factors, t_num_secs))
    bc = numpy.zeros(2 * num_factors)
    for i in xrange(num_factors):
        for j in xrange(t_num_secs):
            Ac[i, j] = t_factors[i, j]
            Ac[num_factors + i, j] = -t_factors[i, j]
        bc[i] = ubexp[i]
        bc[num_factors + i] = -lbexp[i]

    untradeable_mu = numpy.dot(u_mu, u_positions)
    untradeable_rvar = numpy.dot(u_positions * u_rvar, u_positions)
    untradeable_loadings = untradeable_exposures
    untradeable_info = (untradeable_mu, untradeable_rvar, untradeable_loadings) 

    p = setupProblem(t_positions, t_mu, t_rvar, t_factors, g_fcov, t_advp, t_advpt, t_vol, t_mktcap, t_borrowRate, t_price, lb, ub, Ac, bc, lbexp, ubexp, untradeable_info, sumnot, zero_start)
    r = p.solve('ralg')
    
    #XXX need to check for small number of iterations!!!
    if (r.stopcase == -1 or r.isFeasible == False) and zero_start > 0:
        #try again with zero_start = 0
        p = setupProblem(t_positions, t_mu, t_rvar, t_factors, g_fcov, t_advp, t_advpt, t_vol, t_mktcap, t_borrowRate, t_price, lb, ub, Ac, bc, lbexp, ubexp, untradeable_info, sumnot, 0)
        r = p.solve('ralg')

    target = numpy.zeros(num_secs)
    g_params = [kappa, slip_gamma, slip_nu, g_positions, g_mu, g_rvar, g_factors, g_fcov, g_advp, g_advpt, g_vol, g_mktcap, g_borrowRate, g_price, execFee, (0.0,0.0, numpy.zeros_like(untradeable_loadings))]
    
    if (r.stopcase == -1 or r.isFeasible == False):
        print objective_detail(target, *g_params)
        raise Exception("Optimization failed")

    #the target is the zipping of the opt result and the untradeable securities
    opt = numpy.array(r.xf)
#    print "SEAN: " + str(r.xf)
#    print str(r.ff)
    targetIndex = 0
    optIndex = 0
    tradeable = set(tradeable)
    while targetIndex < num_secs:
        if targetIndex in tradeable:
            target[targetIndex] = opt[optIndex]
            optIndex += 1
        else:
            target[targetIndex] = g_positions[targetIndex]
        targetIndex += 1
            
    dutil = numpy.zeros(len(target))
    dutil2 = numpy.zeros(len(target))
    dmu = numpy.zeros(len(target))
    dsrisk = numpy.zeros(len(target))
    dfrisk = numpy.zeros(len(target))
    eslip = numpy.zeros(len(target))
    costs = numpy.zeros(len(target))
    for ii in range(len(target)):
        targetwo = target.copy()
        targetwo[ii] = g_positions[ii]

        dutil_o1 = objective_detail(target, *g_params)
        dutil_o2 = objective_detail(targetwo, *g_params)
        dutil[ii] = dutil_o1[0] - dutil_o2[0]
        dmu[ii] = dutil_o1[1]  - dutil_o2[1]
        dsrisk[ii] = dutil_o1[2] - dutil_o2[2]
        dfrisk[ii] = dutil_o1[3] - dutil_o2[3]
        eslip[ii] = dutil_o1[4] - dutil_o2[4]
        costs[ii] = dutil_o1[5] - dutil_o2[5]

        trade = target[ii]-g_positions[ii]

        positions2 = g_positions.copy()
        positions2[ii] = target[ii]
        dutil2[ii] = objective(positions2, *g_params) - objective(g_positions, *g_params)

    printinfo(target, *g_params)

    return (target, dutil, eslip, dmu, dsrisk, dfrisk, costs, dutil2)

def init():
    global num_secs, num_factors, g_positions, g_lbound, g_ubound, g_mu, g_rvar, g_advp, g_advpt, g_vol, g_mktcap, g_borrowRate, g_price, g_factors, g_fcov
    
    g_positions = numpy.zeros(num_secs)
    g_lbound = numpy.zeros(num_secs) 
    g_ubound = numpy.zeros(num_secs)
    g_mu = numpy.zeros(num_secs)
    g_rvar = numpy.zeros(num_secs)
    g_advp = numpy.zeros(num_secs)
    g_advpt = numpy.zeros(num_secs)
    g_vol = numpy.zeros(num_secs)
    g_mktcap = numpy.zeros(num_secs)
    g_borrowRate = numpy.zeros(num_secs)
    g_price = numpy.zeros(num_secs)
    g_factors = numpy.zeros((num_factors, num_secs))
    g_fcov = numpy.zeros((num_factors, num_factors)) 
    return

def getUntradeable():
    untradeable = []
    tradeable = []

    for ii in xrange(num_secs):
        if abs(g_lbound[ii] - g_ubound[ii]) < 10:
            untradeable.append(ii)
        else:
            tradeable.append(ii)
            
    return tradeable, untradeable

