#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2, jinja2, urllib, requests
import re, os, cgi, logging
from google.appengine.ext import db
from google.appengine.api import users
from datetime import datetime, timedelta
from operator import itemgetter

jinja_environment = jinja2.Environment(
		loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
        extensions=['jinja2.ext.autoescape'])

class Stock(db.Model):
    username = db.StringProperty()
    stock_name = db.StringProperty()

class TotalHolding(db.Model):
    username = db.StringProperty()
    amount = db.FloatProperty()
    date = db.IntegerProperty()

class StockListing2(db.Model):
    username = db.StringProperty()
    date = db.IntegerProperty()
    stock_name = db.StringProperty()
    price = db.FloatProperty()
    dollar_value = db.FloatProperty()     

class MainHandler(webapp2.RequestHandler):

    #This retrieves the most current prices available for stocks in the user's portfolio. Recursive
    #calls are made to go back to previous dates. date and price_date are lists (and therefore
    #on the heap). date is needed for the api call, and price_date will be displayed to the user. 
    #Recursive calls are only needed for the first stock in the portfolio; once the prices are found, 
    #date is already set appropriately for finding the prices of the other stocks in the portfolio 
    def getMostRecentPrices(self, auth_token, stock_name, date, price_date, stockPricesList):

        url_part1 = "http://www.quandl.com/api/v1/datasets/WIKI/" + stock_name
        url_part2 = ".json?" + auth_token + "&column=4&sort_order=asc&collapse=daily&trim_start=" + str(date[0]) + "&trim_end=" + str(date[0])
        url = url_part1 + url_part2
        r = None
        try:
          r = requests.get(url)
          if r is not None:
            try:
              
              data = r.json() 

              try:
              
                stockPricesList.append([stock_name, data[u'data'][0][1]])
                price_date[0] = format(date[0], '%m/%d/%Y')

              except IndexError: #today's stock prices not available, 
              #so go back one day and make recursive method call
              
                dateInStackFrame = date[0]
                current_datetime = datetime.now() + timedelta(hours = -4)
                current_date = current_datetime.date()
              
                #the following conditional is to prevent more than 5 recursive calls from being made
                if (current_date - dateInStackFrame < timedelta(days = 5)):
                  
                  date[0] = date[0] + timedelta(days = -1)
                  self.getMostRecentPrices(auth_token, stock_name, date, price_date, stockPricesList)
              
                else:
                  self.response.write("<h1>Error loading data. Please try again later</h1>")
              except TypeError:
                self.response.write("<h1>Error loading data. Please try again later</h1>")
            except KeyError:
                  stockPricesList.append([stock_name, "NA"])
                  price_date[0] = format(date[0], '%Y-%m-%d')
          else:
            self.response.write("<h1>Error loading data. Please try again later</h1>")
        except:
          self.response.write("<h1>Error loading data for " + stock_name + ". Please try again later</h1>")

    #This retrieves historical portfolio data, from the database, for a particular user. When first
    #logging onto the site, the default is to show the most recent portfolio data, but the user can
    #then select a particular date to see the portfolio data from that date.
    def getOldData(self, listingsList, set_of_dates, username, date, date_to_feature, oldDate):

        stock_listings = db.GqlQuery("SELECT * FROM StockListing2 WHERE username = :1", str(username))
        for stock_listing in stock_listings:
          set_of_dates.add(stock_listing.date)
        datesListFromSet = list(set_of_dates)
        datesListFromSet.sort(reverse = True)
        
        if datesListFromSet:

          if date_to_feature == "most_recent":
            #old_listings are stocks from the most recently saved date in this case
            old_listings = db.GqlQuery("SELECT * FROM StockListing2 WHERE username = :1 AND date =:2", str(username), datesListFromSet[0])
            #old_total_holding is total value from the most recently saved data
            old_total_holding = db.GqlQuery("SELECT * FROM TotalHolding WHERE username = :1 AND date =:2", str(username), datesListFromSet[0])

          else: #date_to_feature is a date selected by the user
              #old_listings are stocks from the date the user has requested in this case
              old_listings = db.GqlQuery("SELECT * FROM StockListing2 WHERE username = :1 AND date =:2", str(username), long(oldDate))
              #old_total_holding is total value from the requested data
              old_total_holding = db.GqlQuery("SELECT * FROM TotalHolding WHERE username = :1 AND date =:2", str(username), long(oldDate))
          
          for holding in old_total_holding:
              oldDate_total_amount = holding.amount
 
          for listing in old_listings:
              listingDate = str(listing.date)
              formattedDate = listingDate[4:6] + "/" + listingDate[6:] + "/" + listingDate[0:4]
              if formattedDate[0] == "0" and formattedDate[3] == "0":
                formattedDate = formattedDate[1:3] + formattedDate[4:]
              elif formattedDate[3] == "0":
                formattedDate = formattedDate[0:3] + formattedDate[4:]
              elif formattedDate[0] == "0":
                formattedDate = formattedDate[1:]
              listingsList.append([str(listing.stock_name), formattedDate, listing.price, listing.dollar_value])
          
          return oldDate_total_amount

    def getDate(self):

        raw_date = datetime.now() + timedelta(hours = -4) #for EST
        date = raw_date.date()
        dateToDisplay = format(date, '%Y-%m-%d')
        yearmonthday = format(date, '%Y%m%d')
        return [date, dateToDisplay]

    def getUsername(self):

        return users.get_current_user()

    def getLogout(self):

        return users.create_logout_url('/')

    #mainMethod is called by either the get or post method
    def mainMethod(self, username, dateArray, logout, oldDate, get_or_post):

        listingsList = []
        set_of_dates = set()

        if get_or_post == "get":
           #this method appends to listingsList the stock listings from the most recent date that portfolio data was saved,
           #and returns the total portfolio value from that date. It also adds to set_of_dates all dates on which portfolio data was saved
           oldDate_total_amount = self.getOldData(listingsList, set_of_dates, username, dateArray[0], "most_recent", None)
        else:  #if get_or_post == "post"
           #this method appends to listingsList the stock listings from a date the user has requested, and returns the total portfolio value from that date.
           #It also adds to set_of_dates all dates on which portfolio data was saved
           oldDate_total_amount = self.getOldData(listingsList, set_of_dates, username, dateArray[0], "old_date", oldDate)

        #the following section (until ###) is for producing a list (stockPricesList) with all stocks in the user's portfolio, as well
        #as their most recently available price and the date for that price
        stockPricesList = []
        mystocks = db.GqlQuery("SELECT * FROM Stock WHERE username = :1", str(username))
        auth_token = "auth_token=UQyxTU4BY5osYsTTqpRd"
        #dates are being given to getMostRecentPrices() in arrays so that if method is called recursively to go back to
        #previous dates, these dates will be changed on the heap. As a result, the second stock and on will not need recursive
        #calls, but will first check the correct date
        date =  [dateArray[0]]
        price_date = [dateArray[1]]
        for stock in mystocks:
            stock_name = stock.stock_name
            self.getMostRecentPrices(auth_token, stock_name, date, price_date, stockPricesList)
        ###

        stockPricesList.append(["S+P", "Type in price"])

        #sort listingsList and stockPricesList alphabetically
        listingsList = sorted(listingsList, key = itemgetter(0)) 
        stockPricesList = sorted(stockPricesList, key = itemgetter(0))

        list_of_dates = list(set_of_dates)
        list_of_dates.sort(reverse = True)
        dateList = []
        for date in list_of_dates:
          date = str(date)
          formattedDate = date[4:6] + "/" + date[6:] + "/" + date[0:4]
          if formattedDate[0] == "0" and formattedDate[3] == "0":
            formattedDate = formattedDate[1:3] + formattedDate[4:]
          elif formattedDate[3] == "0":
            formattedDate = formattedDate[0:3] + formattedDate[4:]
          elif formattedDate[0] == "0":
            formattedDate = formattedDate[1:]
          dateList.append({"yearmonthday": date, "formattedDate": formattedDate})


        template_values = {"listings": listingsList,"stock_prices": stockPricesList, "list_of_dates": dateList, "username":str(username.nickname()), "logout":logout, "total_holding" : oldDate_total_amount, "price_date": price_date[0]}
        template = jinja_environment.get_template('index.html')
        self.response.write(template.render(template_values))
   
    def get(self):

        username = self.getUsername()
        logout = self.getLogout()

        dateArray = self.getDate()

        if username:      

          self.mainMethod(username, dateArray, logout, None, "get")

        else:

      	  self.redirect(users.create_login_url(self.request.uri))

    def post(self):	

        username = self.getUsername()
        logout = self.getLogout()

        dateArray = self.getDate()

        new_stock = cgi.escape(self.request.get("new_stock")).upper()
        stock_to_delete = self.request.get("deleteStock")
        savebutton = self.request.get("savebutton")
        oldDate = self.request.get("oldDate")

        if new_stock:
      	    e = Stock(username = str(username), stock_name = new_stock.upper())
            e.put()
            self.redirect("/")
      
        if stock_to_delete:
            stock_to_delete = db.GqlQuery("SELECT * FROM Stock WHERE username = :1 AND stock_name = :2", str(username), stock_to_delete)
            db.delete(stock_to_delete)
            self.redirect("/")
      
        if savebutton:
            dollar_values = self.request.get_all("dollar_value")
            listed_stocks = self.request.get_all("listed_stock")
            current_prices = self.request.get_all("current_price")
            total_amount = self.request.get_all("total_holding")
            price_date = self.request.get("price_date")
            price_date = price_date.replace("-","")
            
            total_amount_added = False
            try:
              total_amount = float(total_amount[0])
              e = TotalHolding(username = str(username), date = int(price_date), amount = total_amount)
              e.put()
              total_amount_added = True
            except:
              pass
            
            if total_amount_added:
              count = 0
              for listed_stock in listed_stocks:
                 dollar_value_converted = False
                 try:
                   dollar_value = float(dollar_values[count])
                   dollar_value_converted = True
                 except:
                   pass
                 if dollar_value_converted:
                   current_prices_converted = False
                   try:  
                     price = float(current_prices[count])
                     current_prices_converted = True
                   except:
                     pass
                   if current_prices_converted:  
                     try:
                        e = StockListing2(username = str(username), date = int(price_date), stock_name = listed_stock, price = price , dollar_value = dollar_value )
                        e.put()
                        count += 1
                     except ValueError:
                       pass
                     self.redirect("/")
                   else:
                     self.response.write("<h1>Error saving data. Please try again.</h1>")  
                 else:
                   self.response.write("<h1>Error saving data. Please try again.</h1>")
            else:
              self.response.write("<h1>Error saving data. Please try again.</h1>")

        if oldDate:

            self.mainMethod(username, dateArray, logout, oldDate, "post")


app = webapp2.WSGIApplication([
    ('/', MainHandler)
], debug=True)

