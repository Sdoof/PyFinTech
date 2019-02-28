#!/usr/bin/env python 

from regress import *
from loaddata import *
from util import *

def calc_qhl_daily(daily_df, horizon):
    print "Caculating daily qhl..."
    result_df = filter_expandable(daily_df)

    print "Calculating qhl0..."
    result_df['qhl0'] = result_df['close'] / np.sqrt(result_df['qhigh'] * result_df['qlow'])
    result_df['qhl0_B'] = winsorize_by_date(result_df[ 'qhl0' ])

    demean = lambda x: (x - x.mean())
    indgroups = result_df[['qhl0_B', 'gdate', 'ind1']].groupby(['gdate', 'ind1'], sort=True).transform(demean)
    result_df['qhl0_B_ma'] = indgroups['qhl0_B']

    print "Calulating lags..."
    for lag in range(1,horizon+1):
        shift_df = result_df.unstack().shift(lag).stack()
        result_df['qhl'+str(lag)+'_B_ma'] = shift_df['qhl0_B_ma']
    
    return result_df

def calc_qhl_intra(intra_df):
    print "Calculating qhl intra..."
    result_df = filter_expandable(intra_df)

    print "Calulating qhlC..."
    result_df['qhlC'] = result_df['iclose'] / np.sqrt(result_df['qhigh'] * result_df['qlow'])
    result_df['qhlC_B'] = winsorize_by_ts(result_df[ 'qhlC' ])

    print "Calulating qhlC_ma..."
    demean = lambda x: (x - x.mean())
    indgroups = result_df[['qhlC_B', 'giclose_ts', 'ind1']].groupby(['giclose_ts', 'ind1'], sort=True).transform(demean)
    result_df['qhlC_B_ma'] = indgroups['qhlC_B']
    
    print "Calculated {} values".format(len(result_df['qhlC_B_ma'].dropna()))
    return result_df

def qhl_fits(daily_df, intra_df, horizon, name, middate=None):
    insample_intra_df = intra_df
    insample_daily_df = daily_df
    outsample_intra_df = intra_df
    if middate is not None:
        insample_intra_df = intra_df[ intra_df['date'] <  middate ]
        insample_daily_df = daily_df[ daily_df.index.get_level_values('date') < middate ]
        outsample_intra_df = intra_df[ intra_df['date'] >= middate ]

    outsample_intra_df['qhl_b'] = np.nan
    outsample_intra_df[ 'qhlC_B_ma_coef' ] = np.nan
    for lag in range(1, horizon+1):
        outsample_intra_df[ 'qhl' + str(lag) + '_B_ma_coef' ] = np.nan

    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])
    for lag in range(1,horizon+1):
        fitresults_df = regress_alpha(insample_daily_df, 'qhl0_B_ma', lag, True, 'daily')
        fits_df = fits_df.append(fitresults_df, ignore_index=True) 
    plot_fit(fits_df, "qhl_daily_"+name+"_" + df_dates(insample_daily_df))
    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    
    
    coef0 = fits_df.ix['qhl0_B_ma'].ix[horizon].ix['coef']
    outsample_intra_df['qhlC_B_ma_coef'] = coef0
    print "Coef0: {}".format(coef0)
    for lag in range(1,horizon):
        coef = coef0 - fits_df.ix['qhl0_B_ma'].ix[lag].ix['coef'] 
        print "Coef{}: {}".format(lag, coef)
        outsample_intra_df[ 'qhl'+str(lag)+'_B_ma_coef' ] = coef

    outsample_intra_df['qhl_b'] = outsample_intra_df['qhlC_B_ma'] * outsample_intra_df['qhlC_B_ma_coef']
    for lag in range(1,horizon):
        outsample_intra_df[ 'qhl_b'] += outsample_intra_df['qhl'+str(lag)+'_B_ma'] * outsample_intra_df['qhl'+str(lag)+'_B_ma_coef']

    return outsample_intra_df

def calc_qhl_forecast(daily_df, intra_df, horizon, middate):
    daily_results_df = calc_qhl_daily(daily_df, horizon) 
    forwards_df = calc_forward_returns(daily_df, horizon)
    daily_results_df = pd.concat( [daily_results_df, forwards_df], axis=1)
    intra_results_df = calc_qhl_intra(intra_df)
    intra_results_df = merge_intra_data(daily_results_df, intra_results_df)

    sector_name = 'Energy'
    print "Running qhl for sector {}".format(sector_name)
    sector_df = daily_results_df[ daily_results_df['sector_name'] == sector_name ]
    sector_intra_results_df = intra_results_df[ intra_results_df['sector_name'] == sector_name ]
    result1_df = qhl_fits(sector_df, sector_intra_results_df, horizon, "in", middate)

    print "Running qhl for not sector {}".format(sector_name)
    sector_df = daily_results_df[ daily_results_df['sector_name'] != sector_name ]
    sector_intra_results_df = intra_results_df[ intra_results_df['sector_name'] != sector_name ]    
    result2_df = qhl_fits(sector_df, sector_intra_results_df, horizon, "ex", middate)    

    result_df = pd.concat([result1_df, result2_df], verify_integrity=True)
    return result_df

if __name__=="__main__":            
    parser = argparse.ArgumentParser(description='G')
    parser.add_argument("--start",action="store",dest="start",default=None)
    parser.add_argument("--end",action="store",dest="end",default=None)
    parser.add_argument("--mid",action="store",dest="mid",default=None)
    parser.add_argument("--freq",action="store",dest="freq",default='15Min')
    args = parser.parse_args()
    
    start = args.start
    end = args.end
    lookback = 30
    horizon = 3
    pname = "./qhl_b" + start + "." + end
    start = dateparser.parse(start)
    end = dateparser.parse(end)
    middate = dateparser.parse(args.mid)
    freq = args.freq
    loaded = False
    try:
        daily_df = pd.read_hdf(pname+"_daily.h5", 'table')
        intra_df = pd.read_hdf(pname+"_intra.h5", 'table')
        loaded = True
    except:
        print "Did not load cached data..."

    if not loaded:
        uni_df = get_uni(start, end, lookback)
        BARRA_COLS = ['ind1']
        barra_df = load_barra(uni_df, start, end, BARRA_COLS)
        PRICE_COLS = ['close']
        price_df = load_prices(uni_df, start, end, PRICE_COLS)
        DBAR_COLS = ['close', 'qhigh', 'qlow']
        intra_df = load_daybars(price_df[['ticker']], start, end, DBAR_COLS, freq)

        daily_df = merge_barra_data(price_df, barra_df)
        daily_df = merge_intra_eod(daily_df, intra_df)
        intra_df = merge_intra_data(daily_df, intra_df)

        daily_df.to_hdf(pname+"_daily.h5", 'table', complib='zlib')
        intra_df.to_hdf(pname+"_intra.h5", 'table', complib='zlib')

    result_df = calc_qhl_forecast(daily_df, intra_df, horizon, middate)
    dump_alpha(result_df, 'qhl_b')



