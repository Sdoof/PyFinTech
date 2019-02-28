# java-coxrossrubinstein
Java implementation for a Cox-Ross-Rubinstein binomial tree to price options in a discrete-time model.

The `OptionPricer` is responsible for pricing the options based on
* the option type (whether call or put),
* the option style (whether American or European),
* the strike price,
* the initial price of the underlying today (S_0),
* the volatility,
* the time step length,
* the interest rate,
* and the number of time steps.

The implementation of the binomial tree `CoxRossRubinsteinTree` uses the tree model and algorithms provided by [java-treemodel-dfs](https://github.com/danieldinter/java-treemodel-dfs).

# Copyright and license
The code and its documentation contained in this GitHub repository are licensed under [GNU General Public License v3.0](LICENSE).