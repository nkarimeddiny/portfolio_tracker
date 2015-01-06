Portfolio Tracker offers investors a tool for comparing portfolio performance to overall market performance. Whenever you update your portfolio by adding or subtracting money from stocks, you also add or subtract money from an imaginary S&P 500 index fund. Over time, you can compare your portfolio's dollar value to the S&P 500 index fund's dollar value, and see exactly how your investments have performed relative to the market.

I built Portfolio Tracker using the Python/webapp2 framework, with JQuery for the frontend logic, and it's hosted on Google App Engine. Stock prices are obtained from Quandl.

The url for the app is nk-stocks1.appspot.com, and a demo video is available at vimeo.com/103757550.

Some details about how the app works:

When a user accesses the site, mainMethod retrieves the dates for which the user has saved portfolio data. The most recent date is passed to the getOldData method. getOldData returns the user’s stock listings from that date, and the total value of their stocks on that date. 

Ticker symbols of stocks that are currently in the user’s portfolio are then retrieved, and getMostRecentPrice is called for each stock.

For the first stock in the portfolio, getMostRecentPrice makes a call to the Quandl API to find the price for the current date. If the price is not available, getMostRecentPrice is called recursively, with the date brought back by one day (up to a maximum of 5 days). Once the price is returned, getMostRecentPrice is called for the next stock in the portfolio, with the date for the returned price being passed in. 



