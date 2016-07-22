#!/usr/bin/env python
import yahoo_finance as yf
import sys
from datetime import datetime as dtime
from ast import literal_eval as leval
from hellaPy import *
from pylab import *
from glob import glob


bcomm = {
  'optionshouse' : 4.75,
  'tradeking'    : 4.95,
  'coinbase'     : 0.00,
  'poloniex'     : 0.00,
  'none'         : 0.00,
}

def update_price(yfobj):
  yfobj.refresh()
  return float(yfobj.get_price())

def as_currency(money):
  negstr = int(money<0) * '-' # Remove deprecation warning w/ int (dumb)
  outstr = negstr + '${:,.2f}'.format(abs(money))
  return outstr

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
    return Stock(**kwargs)

  def update(self):
    self.cprice = self.currentprice = self.price = update_price(self.yf)
    self.dprice = self.price - self.cbasis
    self.pprice = '{:6.2f}%'.format(( self.dprice / self.cbasis ) * 100)
    self.value  = self.price  * self.shares
    self.gross  = self.dvalue = self.value  - self.cvalue
    self.net    = self.gross - self.comm - sum([bcomm[b] for b in self.broker ])
    self.net_r  = self.net / self.cvalue 
    self.net_p  = '{:6.2f}%'.format(self.net_r * 100)
    return None

  def __str__(self):
    self.update()
    dsn = as_currency(self.cvalue)
    cpr = as_currency(self.cprice)
    out = '{:>8s}: {:>12s}  :  {:>12s} : {:>8s}'.format(self.symbol,dsn,cpr,self.net_p)
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

class Currency(Investment):
  def __init__(self,**kwargs):
    Investment.__init__(self,**kwargs)
    # Non input constants
    self.yf = yf.Currency(symbol)
    self.yf.get_price = self.yf.get_rate
    self.update()

class Portfolio:
  def __init__(self,source_file):
    self.source_file = source_file
    with open(source_file,'r') as f:
      stock_dict = leval(f.read())
    stocks  = array([ Stock( **s ) for s in stock_dict ])
    tickers = array([ s.symbol for s in stocks  ])
    u,c = unique(tickers,return_counts=True)
    self.stocks  = empty(u.shape,dtype=object)
    self.tickers = u 
    for k in range(len(c)):
      self.stocks[k] = sum(stocks[where(tickers==u[k])[0]])  

    self.num_assets = self.portfolio_size = self.psize = len(self.stocks)
    dgrab = zeros((self.psize,8))
    for k in range(self.psize):
      s = self.stocks[k]
      dgrab[k] = array([ s.shares,s.cvalue,s.price,s.value,s.ccomm,s.gross,s.net,s.net_r ])
    dgrab = dgrab.T
    self.shares = dgrab[0]
    self.cvalues= dgrab[1]
    self.prices = dgrab[2]
    self.values = dgrab[3]
    self.ccomms = dgrab[4]
    self.grosses= dgrab[5]
    self.nets   = dgrab[6]
    self.nets_r = dgrab[7]

    self.cvalue = sum(self.cvalues)
    self.value  = sum(self.values )
    self.gross  = sum(self.grosses)
    self.net    = sum(self.nets   )
    self.net_r  = self.net / self.cvalue
    self.net_p  = '{:6.2f}%'.format(self.net / self.cvalue * 100)

  def update(self):
    for s in self.stocks:
      s.update()
    return None

  def __str__(self):
    N   = 60
    out = N*'=' + '\n'
    out+= '  Ticker:  Cost Value   : Current Price :   Net\n'
    out+= N*'-' + '\n'
    for s in self.stocks:
      out+= str(s) + '\n'
    out+= N*'-' + '\n'
    out+= 'Portfolio cost value: {:s}\n'.format(as_currency(self.cvalue))
    out+= 'Portfolio equity    : {:s}\n'.format(as_currency(self.value))
    out+= 'Portfolio net       : {:s}\n'.format(self.net_p)
    out+= N*'=' + '\n'
    return out

  def __repr__(self):
    cmod,cname,ntp = self.__module__,self.__class__.__name__,self.net_p
    return '<{:s}.{:s}: {:s}>'.format(cmod,cname,ntp)
    
p = Portfolio('dat/assets.trak')
print(p)
