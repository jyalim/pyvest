#!/usr/bin/env python
import sys
sys.path.append('src')
import time
import pickle 
import poloniex as polo
import yahoo_finance as yf
from datetime import datetime as dtime
from ast import literal_eval as leval
from hellaPy import *
from pylab import *
from glob import glob

"""
A work in progress...
"""

bcomm = {
  'optionshouse' : 4.75,
  'tradeking'    : 4.95,
  'coinbase'     : 0.00,
  'poloniex'     : 0.00,
  'self'         : 0.00,
}

class sarray(ndarray):
  def __new__(cls, input_array, info=None):
      obj = np.asarray(input_array).view(cls)
      obj.info = info
      return obj
  def __array_finalize__(self, obj):
      if obj is None: 
        return
      self.info = getattr(obj, 'info', None)
  def __array_wrap__(self, out_arr, context=None):
      return np.ndarray.__array_wrap__(self, out_arr, context)

def update_price(yfobj):
  yfobj.refresh()
  return float(yfobj.get_price())

def as_currency(money):
  negstr = int(money<0) * '-' # Remove deprecation warning w/ int (dumb)
  outstr = negstr + '${:,.2f}'.format(abs(money))
  return outstr

class Cash:
  def __init__(self,*args,**kwargs):
    pass
  def refresh(self):
    pass
  def get_rate(self):
    return 1

class Eth(Cash):
  def __init__(self,*args,**kwargs):
    self.__TXEX__    = 'BTC_ETH'
    self.yf          = polo.Poloniex()
    self.yf.get_txrx = lambda: float(self.yf.marketTicker()[self.__TXEX__]['last'])
    self.ETHBTC      = self.yf.get_txrx()
    self.tx_conv     = yf.Currency('BTCUSD')
    self.tx_conv.get_price = lambda: float(self.tx_conv.get_rate())
    self.BTCUSD      = update_price(self.tx_conv)
    self.yf.get_rate = lambda: update_price(self.tx_conv) * self.yf.get_txrx()
    self.USD         = self.yf.get_rate()

  def refresh(self):
    self.ETHBTC = self.yf.get_txrx()
    self.BTCUSD = self.tx_conv.get_rate()
    self.USD    = self.yf.get_rate()

  def get_rate(self):
    return self.yf.get_rate()

class Investment:
  def __init__(self,symbol,shares,cbasis,cvalue,date,comm,broker,notes=''):
    self.symbol = self.name = self.asset = symbol
    self.shares = shares
    self.cbasis = self.costbasis = self.purchase_price = cbasis 
    self.cvalue = self.costvalue = self.purchase_debit = cvalue
    self.date   = date
    self.comm   = self.commission = comm
    self.broker = self.brokers = [ broker ] if isinstance(broker,str) else broker
    self.notes  = notes
    # Non input constants
    self.ccomm  = self.comm + sum([bcomm[b] for b in self.broker])

  def get_data(self):
    s = self
    return array([ s.shares,s.cvalue,s.price,s.value,s.ccomm,s.gross,s.net,s.net_r ])

  def update(self):
    self.cprice = self.currentprice = self.price = update_price(self.yf)
    self.dprice = self.price - self.cbasis
    if self.cbasis > 0:
      self.pprice = '{:6.2%}'.format(( self.dprice / self.cbasis ))
    self.value  = self.price  * self.shares
    self.gross  = self.dvalue = self.value  - self.cvalue
    self.net    = self.gross - self.comm - sum([bcomm[b] for b in self.broker ])
    if self.cvalue > 0:
      self.net_r = self.net / self.cvalue 
    else:
      self.net_r = self.net
    self.net_p  = '{:6.2%}'.format(self.net_r)
    return None

  def __add__(self,other):
    if self.symbol != other.symbol:
      raise ValueError("Assets must be same.")
    shares = self.shares + other.shares
    cvalue = self.cvalue + other.cvalue
    nspace = ' ' * int( (len(self.notes) + len(other.notes)) > 0)
    kwargs = {
      'symbol' : self.symbol,
      'shares' : shares,
      'cvalue' : cvalue,
      'cbasis' : cvalue / shares,
      'date'   : max(self.date,other.date),
      'comm'   : self.comm + other.comm,
      'broker' : [ b for sl in [self.broker,other.broker] for b in sl ],
      'notes'  : self.notes + nspace + other.notes,
    } 
    return self.__class__(**kwargs)

  def __str__(self):
    dsn = as_currency(self.cvalue)
    cpr = as_currency(self.cprice)
    out = '{:>8s}: {:>12s}  :  {:>12s} : {:>8s}\n'.format(self.symbol,dsn,cpr,self.net_p)
    return out

  def __repr__(self):
    cmod,cname,sym = self.__module__,self.__class__.__name__,self.symbol
    return '<{:s}.{:s}: {:s}>'.format(cmod,cname,sym)

class Stock(Investment):
  def __init__(self,**kwargs):
    super().__init__(**kwargs)
    # Non input constants
    self.yf = yf.Share(self.symbol)
    self.update()

class Money(Investment):
  def __init__(self,**kwargs):
    super().__init__(**kwargs)
    symbol = self.symbol
    # Non input constants
    if 'BTCUSD' == symbol:
      self.yf = yf.Currency(self.symbol) 
    if 'ETHBTC' == symbol:
      self.yf = Eth()
    if 'USD' == symbol:
      self.yf = Cash()
    self.yf.get_price = self.yf.get_rate
    self.update()


class Portfolio:
  def __init__(self,assets_file):
    self.assets_file = assets_file
    with open(assets_file,'r') as f:
      main_dict = leval(f.read())
    stocks = array([ Stock(**s) for s in main_dict['stocks'] ])
    moneys = array([ Money(**m) for m in main_dict['moneys'] ])

    self.tickers,self.stocks = self.reduce_assets(stocks)
    self.exticks,self.moneys = self.reduce_assets(moneys)
    #self.moneys[where(self.exticks=='ETHBTC')[0]] *= 650

    self.update_asset(self.stocks)
    self.update_asset(self.moneys)

    self.assets = [ self.stocks, self.moneys ]
    self.update()

  def reduce_assets(self,asset_class_array):
    symbols = array([ aca.symbol for aca in asset_class_array ])
    u,c = unique(symbols,return_counts=True)
    assets = array(empty(u.shape,dtype=object))
    for k in range(len(c)):
      assets[k] = sum( asset_class_array[where(symbols==u[k])[0]] )
    return u,sarray(assets)

  def update_asset(self,obj):
    obj.psize = len(obj)
    dgrab = array([ a.get_data() for a in obj ]).T
    obj.shares = dgrab[0]
    obj.cvalues= dgrab[1]
    obj.prices = dgrab[2]
    obj.values = dgrab[3]
    obj.ccomms = dgrab[4]
    obj.grosses= dgrab[5]
    obj.nets   = dgrab[6]
    obj.nets_r = dgrab[7]
    obj.cvalue = sum(obj.cvalues)
    obj.value  = sum(obj.values )
    obj.gross  = sum(obj.grosses)
    obj.net    = sum(obj.nets   )
    obj.net_r  = obj.net / obj.cvalue
    obj.net_p  = '{:6.2%}'.format(obj.net_r)
    return None

  def update(self):
    self.cvalue,self.value,self.gross,self.net = zeros(4)
    for a in self.assets:
      self.update_asset(a)
      self.cvalue += a.cvalue 
      self.value  += a.value  
      self.gross  += a.gross  
      self.net    += a.net    
    self.net_r = self.net / self.cvalue
    self.net_p = '{:6.2%}'.format(self.net_r)
    self.time  = time.time()
    return None

  def __str__(self,N=60):
    tbr = '{fill:=^{width:d}}\n'.format(fill='',width=N)
    sbr = '{fill:-^{width:d}}\n'.format(fill='',width=N)
    hdr = sbr
    hdr+= '  Symbol:  Cost Value   : Current Price :   Net\n'
    hdr+= sbr
    def asset_block(asset):
      ab_out = '{:^{width:d}s}\n'.format( asset[0].__class__.__name__.upper(),width=N )
      ab_out+= hdr
      for a in asset:
        ab_out += str(a)
      ab_out+= '{:^{width:d}s}\n'.format('Totals',width=N)
      ab_out+= '  Cost value: {:s}\n'.format(as_currency(asset.cvalue))
      ab_out+= '  Equity    : {:s}\n'.format(as_currency(asset.value))
      ab_out+= '  Net       : {:s}\n'.format(asset.net_p)
      return ab_out
    out = tbr 
    for asset in self.assets:
      out += asset_block(asset)
      out += sbr
    out+= '{:^{width:d}s}\n'.format( 'PORTFOLIO',width=N )
    out+= sbr
    out+= '  Cost value: {:s}\n'.format(as_currency(self.cvalue))
    out+= '  Equity    : {:s}\n'.format(as_currency(self.value))
    out+= '  Net       : {:s}\n'.format(self.net_p)
    out+= tbr
    return out

  def __repr__(self):
    cmod,cname,ntp = self.__module__,self.__class__.__name__,self.net_p
    return '<{:s}.{:s}: {:s}>'.format(cmod,cname,ntp)
    
p = Portfolio('dat/assets.vst')
print(p)
