#!/usr/bin/env python 

from regress import *
from loaddata import *
from util import *

def calc_rev_daily(daily_df, horizon, lag):
    print "Caculating daily rev..."
    result_df = filter_expandable(daily_df)

    print "Calculating rev0..."
    result_df['rev0'] = pd.rolling_sum(result_df['log_ret'], lag)

    demean = lambda x: (x - x.mean())
    indgroups = result_df[['rev0', 'gdate', 'ind1']].groupby(['gdate', 'ind1'], sort=True).transform(demean)
    result_df['rev0_ma'] = indgroups['rev0']
    shift_df = result_df.unstack().shift(1).stack()
    result_df['rev1_ma'] = shift_df['rev0_ma']

    return result_df

def rev_fits(daily_df, horizon, name, middate=None):
    insample_daily_df = daily_df
    if middate is not None:
        insample_daily_df = daily_df[ daily_df.index.get_level_values('date') < middate ]
        outsample_daily_df = daily_df[ daily_df.index.get_level_values('date') >= middate ]

    outsample_daily_df['rev'] = np.nan

    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])
    fitresults_df = regress_alpha(insample_daily_df, 'rev1_ma', horizon, True, 'daily') 
    fits_df = fits_df.append(fitresults_df, ignore_index=True) 
    plot_fit(fits_df, "rev_daily_"+name+"_" + df_dates(insample_daily_df))
    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    

    coef0 = fits_df.ix['rev1_ma'].ix[horizon].ix['coef']
    print "Coef{}: {}".format(0, coef0)
    outsample_daily_df[ 'rev1_ma_coef' ] = coef0

    outsample_daily_df[ 'rev_' + name ] = outsample_daily_df['rev1_ma'] * outsample_daily_df['rev1_ma_coef']
    
    return outsample_daily_df

def calc_rev_forecast(daily_df, horizon, middate, lag):
    daily_results_df = calc_rev_daily(daily_df, horizon, lag) 
    forwards_df = calc_forward_returns(daily_df, horizon)
    daily_results_df = pd.concat( [daily_results_df, forwards_df], axis=1)

    result_df = rev_fits(daily_results_df, horizon, str(lag), middate)

    return result_df

if __name__=="__main__":            
    parser = argparse.ArgumentParser(description='G')
    parser.add_argument("--start",action="store",dest="start",default=None)
    parser.add_argument("--end",action="store",dest="end",default=None)
    parser.add_argument("--mid",action="store",dest="mid",default=None)
    parser.add_argument("--lag",action="store",dest="lag",default=21)
#    parser.add_argument("--horizon",action="store",dest="horizon",default=20)
    args = parser.parse_args()
    
    start = args.start
    end = args.end
    lookback = 30
    horizon = int(args.lag)
    pname = "./rev" + start + "." + end
    start = dateparser.parse(start)
    end = dateparser.parse(end)
    middate = dateparser.parse(args.mid)
    lag = int(args.lag)

    loaded = False
    try:
        daily_df = pd.read_hdf(pname+"_daily.h5", 'table')
        loaded = True
    except:
        print "Did not load cached data..."

    if not loaded:
        uni_df = get_uni(start, end, lookback)
        BARRA_COLS = ['ind1']
        barra_df = load_barra(uni_df, start, end, BARRA_COLS)
        PRICE_COLS = ['close']
        price_df = load_prices(uni_df, start, end, PRICE_COLS)

        daily_df = merge_barra_data(price_df, barra_df)
        daily_df.to_hdf(pname+"_daily.h5", 'table', complib='zlib')

    result_df = calc_rev_forecast(daily_df, horizon, middate, lag)
    dump_daily_alpha(result_df, 'rev_' + str(lag))



