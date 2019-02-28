#!/usr/bin/env python 

from regress import *
from loaddata import *
from util import *

def wavg(group):
    b = group['pbeta']
    d = group['log_ret']
    w = group['mkt_cap_y'] / 1e6
    res = b * ((d * w).sum() / w.sum())
    return res

def wavg2(group):
    b = group['pbeta']
    d = group['cur_log_ret']
    w = group['mkt_cap_y'] / 1e6
    res = b * ((d * w).sum() / w.sum())
    return res

def calc_bd_daily(daily_df, horizon):
    print "Caculating daily bd..."
    result_df = filter_expandable(daily_df)

#    decile = lambda x: 10.0 * x.rank()/float(len(x))
#    result_df['log_ret_decile'] = result_df[['log_ret', 'gdate']].groupby(['gdate'], sort=False).transform(decile)['log_ret']
    result_df['bret'] = result_df[['log_ret', 'pbeta', 'mkt_cap_y', 'gdate']].groupby('gdate').apply(wavg).reset_index(level=0)['pbeta']
    result_df['badjret'] = result_df['log_ret'] - result_df['bret']

    print "Calculating bd0..."
    result_df['bd0'] = (result_df['askHitDollars'] - result_df['bidHitDollars']) / (result_df['askHitDollars'] + result_df['midHitDollars'] + result_df['bidHitDollars'])
    result_df['bd0_B'] = winsorize_by_date( result_df['bd0'] / np.sqrt(result_df['spread_bps']) / 10000.0)

    demean = lambda x: (x - x.mean())
    indgroups = result_df[['bd0_B', 'gdate', 'ind1']].groupby(['gdate', 'ind1'], sort=False).transform(demean)
    result_df['bd0_B_ma'] = indgroups['bd0_B']
 #   result_df['bd0_B_ma'] = result_df['bd0_B_ma'] * np.abs(result_df['badjret'])
#    result_df['bd0_B_ma'] =  result_df['bd0_B_ma'].clip(0,1000) * np.sign(result_df['log_ret'])
    #    result_df.ix[ (result_df['log_ret_decile'] < 2) | (result_df['log_ret_decile'] == 9), 'bd0_B_ma'] = np.nan

    print "Calulating lags..."
    for lag in range(1,horizon+1):
        shift_df = result_df.unstack().shift(lag).stack()
        result_df['bd'+str(lag)+'_B_ma'] = shift_df['bd0_B_ma']
        result_df['bd'+str(lag)+'_B'] = shift_df['bd0_B']

    return result_df

def calc_bd_intra(intra_df):
    print "Calculating bd intra..."
    result_df = filter_expandable(intra_df)

    result_df['cur_log_ret'] = np.log(result_df['iclose']/result_df['bopen'])
    result_df['bret'] = result_df[['cur_log_ret', 'pbeta', 'mkt_cap_y', 'giclose_ts']].groupby(['giclose_ts'], sort=False).apply(wavg2).reset_index(level=0)['pbeta']
    result_df['badjret'] = result_df['cur_log_ret'] - result_df['bret']

#    decile = lambda x: 10.0 * x.rank()/float(len(x))
#    result_df['cur_log_ret_decile'] = result_df[['cur_log_ret', 'giclose_ts']].groupby(['giclose_ts'], sort=False).transform(decile)['cur_log_ret']

    print "Calulating bdC..."    
    result_df['bdC'] = (result_df['askHitDollars'] - result_df['bidHitDollars']) / (result_df['askHitDollars'] + result_df['midHitDollars'] + result_df['bidHitDollars'])
    result_df['bdC_B'] = winsorize_by_ts(result_df['bdC'] / np.sqrt(result_df['spread_bps']) / 10000.0)

    print "Calulating bdC_ma..."
    demean = lambda x: (x - x.mean())
    indgroups = result_df[['bdC_B', 'giclose_ts', 'ind1']].groupby(['giclose_ts', 'ind1'], sort=False).transform(demean)
    result_df['bdC_B_ma'] = indgroups['bdC_B']
#    result_df['bdC_B_ma'] = result_df['bdC_B_ma'] * np.abs(result_df['badjret'])

#    result_df['bdC_B_ma'] =  result_df['bdC_B_ma'].clip(0,1000) * np.sign(result_df['cur_log_ret'])
#    result_df.ix[ (result_df['cur_log_ret_decile'] < 1) | (result_df['cur_log_ret_decile'] == 9), 'bdC_B_ma'] = np.nan
#    result_df['bdC_B_ma'] = result_df['bdC_B_ma'] * (2 - result_df['cur_log_ret_r'])

    # result_df['eod_ts'] = result_df['date'].apply(lambda x: x + timedelta(hours=15, minutes=30))
    # result_df['scale'] = result_df['eod_ts'] - result_df['giclose_ts'] 
    # result_df['scale'] = result_df['scale'].apply(lambda x: 1.0 - (x/np.timedelta64(1, 's'))/(360*60))
    # result_df[ result_df['scale'] > 1 ] = 0
    # result_df['bdC_B_ma_tod'] = result_df['bdC_B_ma'] * result_df['scale']

    return result_df

def bd_fits(daily_df, intra_df, horizon, name, middate):
    insample_intra_df = intra_df
    insample_daily_df = daily_df
    outsample_intra_df = intra_df
    outsample = False
    if middate is not None:
        outsample = True
        insample_intra_df = intra_df[ intra_df['date'] <  middate ]
        insample_daily_df = daily_df[ daily_df.index.get_level_values('date') < middate ]
        outsample_intra_df = intra_df[ intra_df['date'] >= middate ]

    outsample_intra_df['bdma'] = np.nan
    outsample_intra_df['bdC_B_ma_coef'] = np.nan
    for lag in range(0, horizon+1):
        outsample_intra_df[ 'bd' + str(lag) + '_B_ma_coef' ] = np.nan

    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])
    fitresults_df = regress_alpha(insample_intra_df, 'bdC_B_ma', horizon, True, 'intra')
    fits_df = fits_df.append(fitresults_df, ignore_index=True)
    plot_fit(fits_df, "bdma_intra_"+name+"_" + df_dates(insample_intra_df))
    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    
    unstacked = outsample_intra_df[ ['ticker'] ].unstack()
    coefs = dict()
    coefs[1] = unstacked.between_time('09:30', '10:31').stack().index
    coefs[2] = unstacked.between_time('10:30', '11:31').stack().index
    coefs[3] = unstacked.between_time('11:30', '12:31').stack().index
    coefs[4] = unstacked.between_time('12:30', '13:31').stack().index
    coefs[5] = unstacked.between_time('13:30', '14:31').stack().index
    coefs[6] = unstacked.between_time('14:30', '15:59').stack().index
    print fits_df.head()
    for ii in range(1,7):
        outsample_intra_df.ix[ coefs[ii], 'bdC_B_ma_coef' ] = fits_df.ix['bdC_B_ma'].ix[ii].ix['coef']

    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])
    for lag in range(1,horizon+1):
        fitresults_df = regress_alpha(insample_daily_df, 'bd0_B_ma', lag, outsample, 'daily')
        fits_df = fits_df.append(fitresults_df, ignore_index=True) 
    plot_fit(fits_df, "bdma_daily_"+name+"_" + df_dates(insample_daily_df))
    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    

    coef0 = fits_df.ix['bd0_B_ma'].ix[horizon].ix['coef']
#    full_df.ix[ outsample_intra_df.index, 'bdC_B_ma_coef' ] = coef0
    print "Coef0: {}".format(coef0)
    for lag in range(1,horizon):
        coef = coef0 - fits_df.ix['bd0_B_ma'].ix[lag].ix['coef'] 
        print "Coef{}: {}".format(lag, coef)
        outsample_intra_df[ 'bd'+str(lag)+'_B_ma_coef' ] = coef

    outsample_intra_df[ 'bdma'] = outsample_intra_df['bdC_B_ma'] * outsample_intra_df['bdC_B_ma_coef']
    for lag in range(1,horizon):
        outsample_intra_df['bdma'] += outsample_intra_df['bd'+str(lag)+'_B_ma'] * outsample_intra_df['bd'+str(lag)+'_B_ma_coef']
    
    return outsample_intra_df

def calc_bd_forecast(daily_df, intra_df, horizon):
    daily_results_df = calc_bd_daily(daily_df, horizon) 
    forwards_df = calc_forward_returns(daily_df, horizon)
    daily_results_df = pd.concat( [daily_results_df, forwards_df], axis=1)
    intra_results_df = calc_bd_intra(intra_df)
    intra_results_df = merge_intra_data(daily_results_df, intra_results_df)

    full_df = bd_fits(daily_results_df, intra_results_df, horizon, "", middate)

    return full_df

if __name__=="__main__":            
    parser = argparse.ArgumentParser(description='G')
    parser.add_argument("--start",action="store",dest="start",default=None)
    parser.add_argument("--end",action="store",dest="end",default=None)
    parser.add_argument("--mid",action="store",dest="mid",default=None)
    parser.add_argument("--freq",action="store",dest="freq",default=15)
    parser.add_argument("--horizon",action="store",dest="horizon",default=3)
    args = parser.parse_args()
    
    start = args.start
    end = args.end
    lookback = 30
    horizon = int(args.horizon)
    freq = int(args.freq)
    pname = "./bd" + start + "." + end
    start = dateparser.parse(start)
    end = dateparser.parse(end)
    middate = dateparser.parse(args.mid)

    loaded = False
    try:
        daily_df = pd.read_hdf(pname+"_daily.h5", 'table')
        intra_df = pd.read_hdf(pname+"_intra.h5", 'table')
        loaded = True
    except:
        print "Did not load cached data..."

    if not loaded:
        uni_df = get_uni(start, end, lookback)
        BARRA_COLS = ['ind1', 'pbeta']
        barra_df = load_barra(uni_df, start, end, BARRA_COLS)
        PRICE_COLS = ['close', 'overnight_log_ret', 'tradable_volume', 'tradable_med_volume_21']
        price_df = load_prices(uni_df, start, end, PRICE_COLS)
        BAR_COLS = ['askHitDollars', 'midHitDollars', 'bidHitDollars', 'bopen', 'spread_bps']
        intra_df = load_bars(price_df[['ticker']], start, end, BAR_COLS, freq)
        daily_df = merge_barra_data(price_df, barra_df)
        daily_df = merge_intra_eod(daily_df, intra_df)
        intra_df = merge_intra_data(daily_df, intra_df)
        daily_df.to_hdf(pname+"_daily.h5", 'table', complib='zlib')
        intra_df.to_hdf(pname+"_intra.h5", 'table', complib='zlib')
    
    outsample_df = calc_bd_forecast(daily_df, intra_df, horizon)
    dump_alpha(outsample_df, 'bdma')
    # dump_alpha(outsample_df, 'bdC_B_ma')
    # dump_alpha(outsample_df, 'bd0_B_ma')
    # dump_all(outsample_df)



