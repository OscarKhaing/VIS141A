#!/usr/bin/python3
# https://weather-gov.github.io/api/general-faqs is free from noaa
# most api schemes are similar in that they need an api key
# either to track your usage of their service, or charge you
# NOAA is free

# here is how to "talk" to the web services API:
# https://api.weather.gov/points/33.0775,-116.4383
# the above returns some metadata and info about other services
# we need not pick out an particular attribute in that file:
# properties:forecast
# from there we get the url:
# https://api.weather.gov/gridpoints/SGX/86,25/forecast
# which is were the actual weather predictions are
# This example does a double read, calling the first url with 
# (Shelter Valley, CA) latitude and longitude, receives the json,
# parses out the forecast url, loads that url, gets the json,
# then prints out some weather data from that url.

import requests # need to pip3 install requests
import json
import datetime

# this is the base url for the service, (protocol, domain, path)
baseurlmeta =  "https://api.weather.gov/points/"
forecasturl = None
lat = 33.0775 
lon = -116.4383 
json_data = None

# a utility function that goes to the internet, grabs the url/as a file,
# and converts it into a json object - actually a dictionary - for us
def get_json_from_url(url):
    print("the url: ", url)
    response = requests.get(url)
    data = response.json()
    #print(type(data))
    #print(data)
    return data

# for our python program to work, we need to for the (parameters)
# these are the moving parts:
# lat is latitude in decimal form, lon is longitude in decimal form,
# and for this api they are simply appended to the url path with a comma *
# example: 33.0775,-116.4383
# lat + "," + lon

# * you can see weather_old.py for an example with url parameters

# now we get the current weather!
# form url and get json object
json_data = get_json_from_url(baseurlmeta + str(lat) + "," + str(lon))

# now get the url from the first request/url/json:
forecasturl = json_data["properties"]["forecast"]
print("forcasturl: ", forecasturl)

# get the forcast json (reusing json_data name because I am done with it)
json_data = get_json_from_url(forecasturl)

# well, now we have forecast data, so we can store it, process it, visualize it, etc
fout = open("saved_forecast_data.txt", "a")
periods = json_data["properties"]["periods"]
# interate over the forecasts
for period in periods:
    fout.write("{0},{1},{2}{3},{4},{5}\n".format(period["name"], period["startTime"], period["temperature"], period["temperatureUnit"], period["probabilityOfPrecipitation"]["value"], period["shortForecast"]))
fout.close()

