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

    #retrieves the most current price available for a stock in the user's portfolio. Recursive
    #calls are made to go back to previous dates. Recursive calls are only needed for the first stock 
    #in the portfolio; once the price is found, date is already set appropriately for finding the 
    #prices of the other stocks in the portfolio 
    def getMostRecentPrice(self, auth_token, stock_name, date, stockPricesList):
        url_part1 = "https://www.quandl.com/api/v1/datasets/WIKI/" + stock_name
        url_part2 = ".json?" + auth_token + "&column=4&sort_order=asc&collapse=daily&trim_start=" + str(date) + "&trim_end=" + str(date)
        url = url_part1 + url_part2
        r = None
        try:
          r = requests.get(url)
          if r is not None:
            try:
              
              data = r.json() 

              try:
              
                stockPricesList.append([stock_name, data[u'data'][0][1]])
                return {"stockPricesList" : stockPricesList, "price_date" : date}

              except IndexError: #today's stock prices not available, 
              #so go back one day and make recursive method call
              
                dateInStackFrame = date
                current_datetime = datetime.now() + timedelta(hours = -4)
                current_date = current_datetime.date()
              
                #the following conditional is to prevent more than 5 recursive calls from being made
                if (current_date - dateInStackFrame < timedelta(days = 5)):
                  
                  date = date + timedelta(days = -1)
                  return self.getMostRecentPrice(auth_token, stock_name, date, stockPricesList)
              
                else:
                  self.response.write("<h1>Error loading data. Please try again later</h1>")
              except TypeError:
                self.response.write("<h1>Error loading data. Please try again later</h1>")
            except KeyError:
                  stockPricesList.append([stock_name, "NA"])
                  return {"stockPricesList" : stockPricesList, "price_date" : date}
          else:
            self.response.write("<h1>Error loading data. Please try again later</h1>")
        except:
          self.response.write("<h1>Error loading data for " + stock_name + ". Please try again later</h1>")

    #retrieves historical portfolio data, from the database, for a particular user. When first
    #logging onto the site, the default is to show the most recent portfolio data, but the user can
    #then select a particular date to see the portfolio data from that date.
    def getOldData(self, oldDate, username, date_to_feature):
        
        if date_to_feature == "most_recent":
          #old_listings_object has stocks from the most recently saved date in this case
          old_listings_object = db.GqlQuery("SELECT * FROM StockListing2 WHERE username = :1 AND date =:2", str(username), oldDate)
          #old_total_holding is total value from the most recently saved data
          old_total_holding = db.GqlQuery("SELECT * FROM TotalHolding WHERE username = :1 AND date =:2", str(username), oldDate)

        else: #date_to_feature is a date selected by the user
            #old_listings_object has stocks from the date the user has requested in this case
            old_listings_object = db.GqlQuery("SELECT * FROM StockListing2 WHERE username = :1 AND date =:2", str(username), long(oldDate))
            #old_total_holding is total value from the requested data
            old_total_holding = db.GqlQuery("SELECT * FROM TotalHolding WHERE username = :1 AND date =:2", str(username), long(oldDate))
        
        for holding in old_total_holding:
            oldDate_total_amount = holding.amount

        oldListings = []

        for listing in old_listings_object:
            formattedDate = self.formatDate(str(listing.date))
            oldListings.append([str(listing.stock_name), formattedDate, listing.price, listing.dollar_value])
        
        oldDate_dict = {"total_amount" : oldDate_total_amount, "oldListings": oldListings}

        return oldDate_dict

    #dates when the user saved stock prices are retrieved and added to a set (eliminating duplication).
    #Set of dates then converted to list and sorted
    def getSavedStockDates(self, username):
        set_of_dates = set()
        saved_dates = db.GqlQuery("SELECT date FROM StockListing2 WHERE username = :1", str(username))
        for saved_date in saved_dates:
          set_of_dates.add(saved_date.date)
        datesListFromSet = list(set_of_dates)
        datesListFromSet.sort(reverse = True)
        return datesListFromSet

    def getDate(self):

        raw_date = datetime.now() + timedelta(hours = -4) #for EST
        date = raw_date.date()
        dateToDisplay = format(date, '%m/%d/%Y')
        yearmonthday = format(date, '%Y%m%d')
        return [date, dateToDisplay]
    
    def formatDate(self, dateString):
        formattedDate = dateString[4:6] + "/" + dateString[6:] + "/" + dateString[0:4]
        # if formattedDate[0] == "0" and formattedDate[3] == "0":
        #   formattedDate = formattedDate[1:3] + formattedDate[4:]
        # elif formattedDate[3] == "0":
        #   formattedDate = formattedDate[0:3] + formattedDate[4:]
        if formattedDate[0] == "0":
          formattedDate = formattedDate[1:]
        return formattedDate

    def getUsername(self):

        return users.get_current_user()

    def getLogout(self):

        return users.create_logout_url('/')

    #mainMethod is called by either the get or post method
    def mainMethod(self, username, dateArray, logout, oldDate, get_or_post):

        saved_stock_dates = self.getSavedStockDates(username);
        oldDate_dict = {}

        if get_or_post == "get":
           if saved_stock_dates:
             #returns stock listings and total portfolio value from the most recent date that portfolio data was saved,
             oldDate_dict = self.getOldData(saved_stock_dates[0], username, "most_recent")
        else:  #if get_or_post == "post"
           #returns stock listings and total portfolio value from a date the user has requested
           oldDate_dict = self.getOldData(oldDate, username, "old_date")

        #the following section (until ###) is for producing a list (stockPricesList) with all stocks in the user's portfolio, as well
        #as their most recently available price and the date for that price
        mystocks = db.GqlQuery("SELECT stock_name FROM Stock WHERE username = :1", str(username))
        auth_token = "auth_token=UQyxTU4BY5osYsTTqpRd"
        stockPricesList = []
        price_date = dateArray[0]
        for stock in mystocks:
            stock_name = stock.stock_name
            #first date passed into method call is current date, but if recursive calls are needed to find
            #the first stock's price, price_date will be changed
            stockPricesDict = self.getMostRecentPrice(auth_token, stock_name, price_date, stockPricesList)
            if stockPricesDict:
              stockPricesList = stockPricesDict["stockPricesList"]
              price_date = stockPricesDict["price_date"]
        ###

        formatted_price_date = format(price_date, '%m/%d/%Y')
        stockPricesList.append(["S+P", "Type in price"])
        
        if oldDate_dict.get("total_amount"):
          total_amount = oldDate_dict["total_amount"]
        else:
          total_amount = None

        #sort oldListings and stockPricesList alphabetically
        if oldDate_dict.get("oldListings"):
          oldListings = sorted(oldDate_dict["oldListings"], key = itemgetter(0))
        else:
           oldListings = []   
        stockPricesList = sorted(stockPricesList, key = itemgetter(0))

        dateListForTemplate = []
        for aDate in saved_stock_dates:
          formattedDate = self.formatDate(str(aDate));
          dateListForTemplate.append({"yearmonthday": aDate, "formattedDate": formattedDate})


        template_values = {"listings": oldListings, "stock_prices": stockPricesList, "list_of_dates": dateListForTemplate, "username":str(username.nickname()), "logout":logout, "total_holding" : total_amount, "formatted_price_date": formatted_price_date ,"price_date": price_date}
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
            total_amount = self.request.get("total_holding")
            price_date = self.request.get("price_date")
            price_date = price_date.replace("-","")
            
            total_amount_saved = False
            try:
              total_amount = float(total_amount)
              e = TotalHolding(username = str(username), date = int(price_date), amount = total_amount)
              e.put()
              total_amount_saved = True
            except:
              pass
            
            if total_amount_saved:
              count = 0
              for listed_stock in listed_stocks:
                data_saved = False
                try:
                  dollar_value = float(dollar_values[count]) 
                  price = float(current_prices[count])
                  e = StockListing2(username = str(username), date = int(price_date), stock_name = listed_stock, price = price , dollar_value = dollar_value )
                  e.put()
                  data_saved = True
                  count += 1
                except:
                  pass
                if data_saved:
                  if count + 1 == len(listed_stocks):
                    self.redirect("/")
                  else:
                    pass
                else:
                  self.response.write("<h1>Error saving data. Please try again.</h1>")
            else:
              self.response.write("<h1>Error saving data. Please try again.</h1>")

        if oldDate:

            self.mainMethod(username, dateArray, logout, oldDate, "post")


app = webapp2.WSGIApplication([
    ('/', MainHandler)
], debug=True)

