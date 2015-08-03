I found some data <a href="http://www.zillow.com/research/data/#bulk">here</a>. I thought it was pretty cool, but it was difficult to analyze in csv form, so I made this application. Enter a zipcode, neighborhood, city, county or state in the search bar, then pick a data type from the select box, then hit Submit. Two charts will appear, one showing the absolute value over time and the other showing the % change. If you keep the data type constant, then entering a new area will overlay the two result sets.

This repo does not contain the actual db, though it does contain the necessary script to create the db yourself ( scripts/zillow-research-parser.py), which is quick and doesnt require much capacity.  The database is implemented in mongodb, which is accessed in the application via django and monoengine.

You can play with the app yourself at props.joshyg.com

Enjoy!
