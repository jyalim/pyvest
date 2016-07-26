Pyvest
======

Create plain text files of the type `sample.vst` in the directory tree

   dat/<asset_type>/broker.vst

e.g., if e-trade is broker,

   dat/stocks/e-trade.vst

Note that the only currently supported asset types are:

  * Stocks
  * Moneys
    * BTCUSD   
    * ETHBTC    ( Convert cost value/basis to USD )
    * USD       ( Set cost value to account balance )
