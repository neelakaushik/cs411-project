import flask
from flask import Flask, request, redirect
from flask import Flask, render_template, url_for
from flask import jsonify
import requests
import json
import datetime
from urllib.request import urlopen
from flaskext.mysql import MySQL
import flask.ext.login as flask_login
import json
import http.client
from requests.auth import HTTPBasicAuth
from pygeocoder import Geocoder
from geopy import geocoders
from flask_googlemaps import GoogleMaps
import pprint
import dateutil.parser 
import numpy as np 
import operator


authorization_code = None
latitude = 0
longitude = 0
end_lat = 0
end_long = 0
DESTINATION = ''
ride_id = ''
final_message = ''
start_lines = []
mbta_stops = {}		#{stop_name : [stop_lat, stop_lon]}
address = ''

mysql = MySQL()

app = Flask(__name__)
app.secret_key = 'super secret string'
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'welcome1'
app.config['MYSQL_DATABASE_DB'] = 'crimebuddy'
app.config['MYSQL_DATABASE_HOST'] = '127.0.0.1'
mysql.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT email FROM Users")
users = cursor.fetchall()
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

# Grab API keys
with open('config.json') as f:
	credentials = json.load(f)
MBTA_key = credentials["MBTA_key"]
client_id = credentials["client_id"]
client_secret = credentials["client_secret"]
geocode_key = credentials["geocode_key"]

g = geocoders.GoogleV3(api_key = geocode_key)


@flask_login.login_required
@app.route("/", methods=['GET', 'POST'])
def main():
	return render_template('index.html')


def getUserList():
	cursor = conn.cursor()
	cursor.execute("SELECT email from Users") 
	return cursor.fetchall()

class User(flask_login.UserMixin):
	pass

@login_manager.user_loader
def user_loader(email):
	users = getUserList()
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	return user

@login_manager.request_loader
def request_loader(request):
	users = getUserList()
	email = request.form.get('email')
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	cursor = mysql.connect().cursor()
	cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email))
	data = cursor.fetchall()
	pwd = str(data[0][0] )
	user.is_authenticated = request.form['password'] == pwd 
	return user

'''
A new page looks like this:
@app.route('new_page_name')
def new_page_function():
	return new_page_html
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
	global authorization_code
	global address
	

	if request.method == 'GET':

		authorization_code = request.args.get('code')

		return render_template('login.html')
	#The request method is POST (page is recieving data)
	address = request.form['location']
	email = request.form['email']
	cursor = conn.cursor()
	#check if email is registered
	
	if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):
		data = cursor.fetchall()
		pwd = str(data[0][0] )
		uid = getUserIdFromEmail(email)
		if request.form['password'] == pwd:
			user = User()
			user.id = email
			flask_login.login_user(user) #okay login in user
			return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file

	#information did not match
	return "<a href='/login'>Try again</a>\
			</br><a href='/Lyftregister'>or make an account</a>"

@app.route('/logout')
def logout():
	global authorization_code
	flask_login.logout_user()
	authorization_code = None
	return render_template('index.html', message='Logged out') 

@login_manager.unauthorized_handler
def unauthorized_handler():
	return render_template('unauth.html')


@app.route('/Lyftregister')
def lyftregister():
	return redirect('https://api.lyft.com/oauth/authorize?client_id=' + client_id + '&scope=public%20profile%20rides.read%20rides.request%20offline&state=payload&response_type=code')



@app.route("/register", methods=['GET'])
def register():
	return render_template('register.html', supress='True')  

@app.route("/register", methods=['POST'])
def register_user():
	global authorization_code

	try:
		email=request.form.get('email')
		password=request.form.get('password')
		first_name=request.form.get('first_name')
		last_name=request.form.get('last_name')
		dob_month=request.form.get('dob-month')
		dob_day = request.form.get('dob-day')
		dob_year = request.form.get('dob-year')
		gender=request.form.get('gender')
		street=request.form.get('street')
		city = request.form.get('city')
		state = request.form.get('state')
		zipcode = request.form.get('zipcode')
		dob = dob_year + '-' + dob_month + '-' + dob_day
		address = street+', '+city+', '+state+', '+zipcode
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('register'))
	cursor = conn.cursor()


	# Get Access Token
	headers = {'Content-Type': 'application/json'}
	data = '{"grant_type": "authorization_code", "code": "' + authorization_code + '"}'
	authorization = requests.post('https://api.lyft.com/oauth/token', headers=headers, data=data, auth=HTTPBasicAuth(client_id, client_secret))
	token_info = json.loads(authorization.text)
	token_type = token_info["token_type"]
	access_token = token_info["access_token"]

	headers = {'Authorization': token_type + ' ' + access_token}
	# User Profile Info
	lyft_request = requests.get('https://api.lyft.com/v1/profile', headers=headers)
	print(lyft_request)
	profile = json.loads(lyft_request.text)
	print(profile)
	print("Your profile information:\t" + "Name: " + profile['first_name'] + " " + profile['last_name'] + " , ID: " + profile['id'])
	temp_split = profile['last_name'].split("'")
	real_last_name =''
	for i in range(len(temp_split)):
		real_last_name += temp_split[i]



	test =  isEmailUnique(email)
	test2 = isLyftIDUnique(profile['id'])
	if test and test2:
		print(cursor.execute("INSERT INTO Users (email, password, first_name, last_name, dob, gender, address) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}')".format(email, password, first_name, last_name, dob, gender, address)))
		conn.commit()
		#log user in
		user = User()
		user.id = email
		flask_login.login_user(user)

		uid = getUserIdFromEmail(flask_login.current_user.id)
		conn.commit()
		# List User's Ride History
		lyft_request = requests.get('https://api.lyft.com/v1/rides?start_time=2015-12-01T21:04:22Z', headers=headers)
		print(lyft_request)
		rides = json.loads(lyft_request.text)
		print('This is your ride history:')
		for ride in rides["ride_history"]:
			if ride['status'] == 'droppedOff':
				print("Date/Time of Trip: " + str(ride['dropoff']['time']) + " , Dropped off at: " + str(ride['dropoff']['address']) + " (Distance: " + str(ride['distance_miles']) + " miles)")
		return render_template('main.html', message = success(), create_message='Account Created!')
	else:
		print("couldn't find all tokens")
		return flask.redirect(flask.url_for('register'))




def getUserIdFromEmail(email):
	cursor = conn.cursor()
	anon = cursor.execute("SELECT user_id  FROM Users WHERE email = '{0}'".format(email))
	cursor.execute("SELECT user_id  FROM Users WHERE email = '{0}'".format(email))
	if anon == 0:
		return -1
	return cursor.fetchone()[0]

def isEmailUnique(email):
	#use this to check if a email has already been registered
	cursor = conn.cursor()
	if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)): 
		#this means there are greater than zero entries with that email
		return False
	else:
		return True
def isLyftIDUnique(lyft_id):
        cursor = conn.cursor()
        if cursor.execute("SELECT lyft_id FROM Lyft WHERE lyft_id = '{0}'".format(lyft_id)):
                return False
        else:
                return True

@app.route('/main')
@flask_login.login_required
def protected():
	return render_template('main.html', name=flask_login.current_user.id, message=success())




def success():
	global final_message
	global latitude
	global longitude
	global address
	if request.method == 'GET':
	# 	return render_template("results.html", message=final_message)
	# else:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		cursor = conn.cursor()
		now = datetime.datetime.now()
		date = now.strftime("%Y-%m-%d")
		# d = datetime.datetime.strptime(date, '%m-%d-%Y')
		# temp = d.strftime('%Y-%m-%d')
		#send_url = 'http://freegeoip.net/json'
		#r = requests.get(send_url)
		#j = json.loads(r.text)
		#lat = j['latitude']
		#lon = j['longitude']
		print(address)
		location = g.geocode(address)
		latitude = location.latitude
		longitude = location.longitude
		db_location = "(" + str(latitude) + str(longitude) + ")"
		db_type="N/A"
		# lon = float(location[1])
		# lat = float(location[0])
		radius = .01
		con = http.client.HTTPConnection("api.spotcrime.com")

		headers = {
		    'cache-control': "no-cache",
		    'postman-token': "8d06a41f-63f4-8b97-77d4-be22bafc72ca"
		    }
		api_string = "/crimes.json?key=privatekeyforspotcrimepublicusers-commercialuse-877.410.1607&lat={0}&lon={1}&radius={2}".format(latitude,longitude,radius)
		con.request("GET", api_string, headers=headers)

		res = con.getresponse()
		data = res.read()
		json_data = json.loads(data.decode("utf-8"))
		crime_weights={'Assault': 7, 'Burglary': 3, 'Robbery': 6, 'Shooting': 10, 'Theft': 2}
		crime_count = 0
		last_date = ''
		total_weight = 0
		shooting = False

		for i in range(len(json_data["crimes"])):
			crime_type = json_data['crimes'][i]['type'] 
			if crime_type in crime_weights:
				if crime_type == 'Shooting':
					shooting = True
				weight = crime_weights[crime_type]
				total_weight += weight
				crime_count += 1
			if i == len(json_data["crimes"]) - 1 :
				last_date = json_data["crimes"][i]["date"]

		# converts current and last dates into datetime format and grabs only the date
		temp_last = dateutil.parser.parse(last_date)		
		last_date = datetime.datetime.date(temp_last)
		temp_current = dateutil.parser.parse(date)
		current_date = datetime.datetime.date(temp_current)
		length = abs((last_date - current_date).days)

		length_type = ''
		min_val = 0
		max_val = 0
		# 100 and 500 = min and max vals that total_weight can be 
		# creates range, given difference between the current and last date
		if length <= 7:
			length = 7
			length_type = ' week'
			min_val = 14.28  	# 100/7
			max_val = 71.42		# 500/7
		elif length <= 14:
			length = 14
			length_type = ' two weeks'
			min_val = 7.14		# 100/14
			max_val = 35.71		# 500/14
		else:
			length = 30
			length_type = ' month'
			min_val = 3.33		# 100/30
			max_val = 16.66		# 500/30
		index = float(total_weight)/length
		rnge = max_val - min_val
		inc = rnge / 5	

		levels = np.arange(min_val, max_val, inc)
		levels = levels.tolist()
		levels += [max_val]

		danger_val = 0
		for i in range(len(levels)):
			if index < levels[i]:
				danger_val = i
				break
			if i == len(levels)-1:
				danger_val = 5


		message = 'The crime data from the last' + length_type + ' shows that the area within ' + str(radius) + ' miles of your current location is most likely to be '
		
		if danger_val == 1 or danger_val == 0:
			message += 'very safe.'
		if danger_val == 2:
			message += 'safe.'
		if danger_val == 3:
			message += 'moderately safe.'
		if danger_val == 4:
			message += 'dangerous. Please consider taking public transportation or calling a Lyft to your destination'
		if danger_val == 5:
			message += 'very dangerous. Please strongly consider taking public transportation or calling a Lyft to your destination.'
		if shooting == True:
			message += '\nPlease be cautious. A shooting has been reported in this area within the last' + length_type + '.'
		
		final_message = message 
		cursor.execute("INSERT INTO Favorites (user_id, location, type, access_date) VALUES ('{0}', '{1}', '{2}', '{3}')".format(uid,db_location,db_type, date))
		conn.commit()
		return final_message


@app.route("/Main", methods=['GET', 'POST'])
def get_global_destination():
	global destination_address 
	destination_address  = request.form.get('destination')
	return render_template('main.html', supress='True')  


def get_mbta_api(parameters):
	''' returns a message to display on the next page '''
	global mbta_stops
	global start_lines
	message = []
	#gets stops closest to current location
	stops_url= "http://realtime.mbta.com/developer/api/v2/stopsbylocation"
	response = requests.get(stops_url, params=parameters)
	response = response.json()

	count = 0
	for obj in response['stop']:
		stop = obj['stop_name']
		distance = round(float(obj['distance']), 2)

		# only choose stops within half a mile
		if distance >= 0.5:
			continue
		stop_id = obj['stop_id']

		stop_lat = obj['stop_lat']
		stop_lon = obj['stop_lon']

		count += 1
		if count > 5: 
			break
		mbta_stops[stop] = [stop_lat, stop_lon]

		message.append(stop + " is " + str(distance) + " miles away from you\n")

		# get lines that pass through each stop
		route_params = {"api_key": MBTA_key, "stop": stop_id, "format":"json"}
		routes_url = "http://realtime.mbta.com/developer/api/v2/predictionsbystop"
		response_routes = requests.get(routes_url, params=route_params)
		response_routes = response_routes.json()

		if 'mode' in response_routes:
			# name = Bus, Subway, or Commuter Rail
			for mode in response_routes['mode']:
				name = mode['mode_name']
				message.append("\t" + name + " line(s) available:\n")
				
				# get line names (route) for each mode of transit
				for route in mode['route']:
					mbta_stops[stop].append(route['route_name'])

					if route['route_name'] not in start_lines:
						start_lines.append(route['route_name'])

					temp_route = "\t\t" + route['route_name']

					time_info = str(route['direction'])
					nxt = time_info.find("'pre_away'")	# pre_away = ETA prediction in second, get index value
					after = (time_info[nxt:]).find(",") + nxt  # gets index value of where next parameter starts
					try:
						next_arr = time_info[nxt+13:after-1]	# index string to get only ETA value (excluding quotes and commas)
						next_arr = str([int(s) for s in next_arr.split() if s.isdigit()])	# just in case there were some characters left that are not digits
						next_arr = next_arr.strip('[') 	# get rid of brackets and convert ETA to float				
						next_arr = float(next_arr.strip(']'))
						mins = int(next_arr // 60)
						leftover = int(next_arr - (mins * 60))
						if mins > 0:
							message.append(temp_route + " - ETA " + str(mins) + " minutes and " + str(leftover) + " seconds")
						if mins == 0:
							message.append(temp_route + " - ETA " + str(leftover) + " seconds")
					except:
						message.append(temp_route + " - ETA information unavailable")

	return (message)

def get_destination_stops():
	global start_lines

	# get address from form 
	# address = request.form.get('loc')
	#address = '5 Gardner Terrace, Allston, MA'	# for testing purposes
	address = destination_address
	location = g.geocode(destination_address)

	dest_lat = location.latitude
	dest_lon = location.longitude
	parameters = {"api_key": MBTA_key, "lat":dest_lat, "lon":dest_lon, "format":"json"}

	#gets stops closest to current location
	stops_url= "http://realtime.mbta.com/developer/api/v2/stopsbylocation"
	response = requests.get(stops_url, params=parameters)
	response = response.json()

	dest_stops = {} 	#{stop_name: [distance from destination, stop_lat, stop_lon, line names in common with starting location]}

	for obj in response['stop']:
		stop = obj['stop_name']

		distance = round(float(obj['distance']), 2)

		# only choose stops within half a mile
		if distance >= 0.5:
			continue
		stop_id = obj['stop_id']

		stop_lat = obj['stop_lat']
		stop_lon = obj['stop_lon']

		# get lines that pass through each stop
		route_params = {"api_key": MBTA_key, "stop": stop_id, "format":"json"}
		routes_url = "http://realtime.mbta.com/developer/api/v2/routesbystop"
		response_routes = requests.get(routes_url, params=route_params)
		response_routes = response_routes.json()

		stop_lines = []

		if 'mode' in response_routes:
			for mode in response_routes['mode']:		
				# get line names (route) for each mode of transit
				for route in mode['route']:
					stop_lines.append(route['route_name'])

		# get lines that only pass through starting stops too
		compare = [x for x in stop_lines if x in start_lines]
		if len(compare) == 0:
			continue
		else:	# only create a key in dest_stops if the stop has lines in common with starting stops
			dest_stops[stop] = [distance, stop_lat, stop_lon] + compare

	#sort dictionary keys by the distance value
	sorted_stops = sorted(dest_stops.items(), key=operator.itemgetter(1))
	if len(sorted_stops) <= 3:
		top_stops = sorted_stops
	else:
		top_stops = sorted_stops[0:4]

	return (top_stops)	# top_stops = {'stop name': [distance, str(lat), str(lon), lines in common with starting stops]}


@app.route("/mbta", methods=['GET','POST'])
def get_coords():
	global latitude
	global longitude

	#send_url = 'http://freegeoip.net/json'
	#r = requests.get(send_url)
	#j = json.loads(r.text)
	#lat = j['latitude']
	#lon = j['longitude']

	lat = latitude
	lon = longitude

	parameters = {"api_key": MBTA_key, "lat":lat, "lon":lon, "format":"json"}

	mbta_info = get_mbta_api(parameters)
	return render_template('mbta.html', mbta_info=mbta_info)


@flask_login.login_required
@app.route("/Lyftsummary", methods=['GET', 'POST'])
def Lyftsummary():
	## Lyft API : Connect on home page to Lyft account - yes/ guest
	##            Call lyft from my location (connected)
 	##	      	-price estimates / hyperlink to web app with pickup/destination locations filled in
	## 	      Can connect later if guest
	global authorization_code, latitude, longitude, end_lat, end_long, DESTINATION
	# Get lat, long of current location 
	if request.method == 'GET':
		return render_template("Lyftsummary.html")
	else:
		#send_url = 'http://freegeoip.net/json'
		#r = requests.get(send_url)
		#j = json.loads(r.text)
		#latitude = j['latitude']
		#longitude = j['longitude']
		print(latitude,longitude)
		#latitude = 42.36
		#longitude = -71.06

		# Get lat, long of destination
		destination = destination_address #request.form.get('destination')
		DESTINATION = destination
		destination = destination.replace(' ', '+')
		response = requests.get('https://maps.googleapis.com/maps/api/geocode/json?address=' + destination)
		resp_json_payload = response.json()
		if (resp_json_payload['results'] == []):
			final_info = None
			return render_template("Lyftsummary.html", message="There was an error processing your address, please enter it again", data=final_info)
		destination = resp_json_payload['results'][0]['geometry']['location']
		end_lat = destination['lat']
		end_long = destination['lng']

		# Authentication
		headers = {'Content-Type': 'application/json'}
		data = '{"grant_type": "client_credentials", "scope": "public"}'
		authorization = requests.post('https://api.lyft.com/oauth/token', headers=headers, data=data, auth=HTTPBasicAuth(client_id, client_secret))
		token_info = json.loads(authorization.text)
		token_type = token_info["token_type"]
		access_token = token_info["access_token"]

		# ETA
		headers = {'Authorization': token_type + ' ' + access_token}
		lyft_request = requests.get('https://api.lyft.com/v1/eta?lat=' + str(latitude) + '&lng=' + str(longitude), headers=headers)
		print(lyft_request)
		list_of_rides = json.loads(lyft_request.text)
		print(list_of_rides)
		print( "These are your options with Ride Type and ETA based on your current location:")
		ride_type = []
		for ride in list_of_rides['eta_estimates']:
			if (ride["display_name"] == None or ride["eta_seconds"] == None):
				final_info = None
				return render_template("Lyftsummary.html", message="There was an error processing your ride request, please enter your address again", data=final_info)
			ride_type += [ride["display_name"] + ": ETA: " + str(ride["eta_seconds"]/60) + " minutes"]
			print("\t" + ride["display_name"] + ": ETA: " + str(ride["eta_seconds"]/60) + " minutes")
		
		# Cost Estimate
		lyft_request = requests.get('https://api.lyft.com/v1/cost?start_lat=' + str(latitude) + '&start_lng=' + str(longitude) + '&end_lat=' + str(end_lat) + '&end_lng=' + str(end_long), headers=headers)
		list_of_rides = json.loads(lyft_request.text)
		print( "These are your options with Ride Type, Cost Estimate, Estimated Duration, and Estimated Distance based on your current location and destination:")
		cost_estimate = []
		for ride in list_of_rides['cost_estimates']:
			cost = ((ride["estimated_cost_cents_min"] + ride["estimated_cost_cents_max"])/2) / 100
			cost_estimate += [ride["display_name"] + ": Cost Estimate: " + "$" + ("%.2f" % cost) + ": Estimated Duration: " + \
			str("%.2f" %(ride['estimated_duration_seconds']/ 60)) + " minutes" + " Estimated Distance: " + str(ride['estimated_distance_miles']) + " miles"]

			print("\t" + ride["display_name"] + ": Cost Estimate: " + "$" + ("%.2f" % cost) + ": Estimated Duration: " + \
			str("%.2f" %(ride['estimated_duration_seconds']/ 60)) + " minutes" + " Estimated Distance: " + str(ride['estimated_distance_miles']) + " miles")
		final_info = [ride_type, cost_estimate]
		# Request a Lyft (requires user login - get into user's lyft account)
		
		# Handle Redirect / Get Authorization Code
		return render_template("Lyftsummary.html", message="Search a different destination, or call a Lyft using the link below", data=final_info)

@flask_login.login_required
@app.route("/RequestLyft", methods=['GET', 'POST'])
def RequestLyft():
	global authorization_code, latitude, longitude, end_lat, end_long, DESTINATION, ride_id

	# Get Access Token	
	headers = {'Content-Type': 'application/json'}
	data = '{"grant_type": "authorization_code", "code": "' + authorization_code + '"}'
	authorization = requests.post('https://api.lyft.com/oauth/token', headers=headers, data=data, auth=HTTPBasicAuth(client_id, client_secret))
	token_info = json.loads(authorization.text)
	print(token_info)
	token_type = token_info["token_type"]
	access_token = token_info["access_token"]


	lyft_type = request.args.get('type')

	headers = {'Authorization': token_type + ' ' + access_token, 'Content-Type': 'application/json'}
	data = '{"ride_type" : "' + lyft_type + '", "origin" : {"lat" : ' + str(latitude) + ', "lng" : ' + str(longitude) + ' }, "destination" : {"lat" : ' + str(end_lat) + ', "lng" : ' + str(end_long) + ', "address" : "' + DESTINATION  + '" } }'
	
	print(headers)
	print(data)

	lyft_request = requests.post('https://api.lyft.com/v1/rides', headers=headers, data=data)
	print(lyft_request)	
	ride = json.loads(lyft_request.text)
	ride_id = ride['ride_id']
	print(ride_id)
	return render_template('requested_lyft.html')




# @app.route("/Lyftlogin", methods=['GET', 'POST'])
# def Lyftlogin():
# 	global authorization_code

# 	# Get Access Token
# 	headers = {'Content-Type': 'application/json'}
# 	data = '{"grant_type": "authorization_code", "code": "' + authorization_code + '"}'
# 	authorization = requests.post('https://api.lyft.com/oauth/token', headers=headers, data=data, auth=HTTPBasicAuth(client_id, client_secret))
# 	token_info = json.loads(authorization.text)
# 	token_type = token_info["token_type"]
# 	access_token = token_info["access_token"]
	
# 	headers = {'Authorization': token_type + ' ' + access_token}
	
# 	# User Profile Info
# 	lyft_request = requests.get('https://api.lyft.com/v1/profile', headers=headers)
# 	print(lyft_request)
# 	profile = json.loads(lyft_request.text) 
# 	print("Your profile information:\t" + "Name: " + profile['first_name'] + " " + profile['last_name'] + " , ID: " + profile['id'])  

# 	# List User's Ride History
# 	lyft_request = requests.get('https://api.lyft.com/v1/rides?start_time=2015-12-01T21:04:22Z', headers=headers)
# 	print(lyft_request)
# 	rides = json.loads(lyft_request.text)
# 	print('This is your ride history:')
# 	for ride in rides["ride_history"]:
# 		print("Date/Time of Trip: " + str(ride['dropoff']['time']) + " , Dropped off at: " + str(ride['dropoff']['address']) + " (Distance: " + str(ride['distance_miles']) + " miles)")
	
# 	# Request a Lyft
# 	#requests.post(

# 	return "hi"

@app.route("/Lyfttemp", methods=['GET', 'POST'])
def lyfttemp():
	global authorization_code

	authorization_code = request.args.get('code')

	print(authorization_code)
	return render_template('register.html')

@flask_login.login_required
@app.route("/profile", methods=['GET', 'POST'])
def profile():
	if flask_login.current_user.is_anonymous:
		message = 'Uh oh, looks like you are not logged in. Please log in to see your profile!'
		return render_template("index.html", message=message)
	else:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		cursor = conn.cursor()
		cursor.execute("SELECT email, first_name, last_name, gender, dob, address FROM Users WHERE user_id = '{0}'".format(uid))
		personal_data = cursor.fetchall()
		full_date = str(personal_data[0][4])
		
		year = full_date[:4]
		month = full_date[5:7]
		day = full_date[8:]
		print(day,month,year)
		addr_split = personal_data[0][5].split(',')
		print(addr_split)
		if len(addr_split) != 4:
			final_address = [personal_data[0][5], "N/A", "N/A", "N/A"]
		else:
			final_address = [addr_split[0], addr_split[1], addr_split[2], addr_split[3]]
		addr = final_address[0].split()
		real_addr = ''
		for i in range(len(addr)):
			if i != len(addr) - 1:
				real_addr += addr[i]+'-'
			else:
				real_addr += addr[i]
		print(real_addr)
		city = final_address[1]
		state = final_address[2]
		zipcode = final_address[3]
		profile_data = [personal_data[0][0], personal_data[0][1], personal_data[0][2], personal_data[0][3], day,month,year,real_addr,city,state,zipcode]
		return render_template("profile.html", data=profile_data)


@flask_login.login_required
@app.route("/history", methods=['GET', 'POST'])
def favorites():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()

	cursor.execute("SELECT location, access_date FROM Favorites WHERE user_id = '{0}' ORDER BY access_date DESC LIMIT 5".format(uid))
	favs = cursor.fetchall()
	address_list = []
	date_list = []
	for i in favs:
		print(i)
		latlon = str(i[0]).split('-')
		lat = str(latlon[0])[1:]
		lon = '-'+ str(latlon[1])[:-1]
		api_url = 'https://maps.googleapis.com/maps/api/geocode/json?latlng=' + str(lat) + ',' + str(lon) + '&key=' + geocode_key
		return_value = requests.get(api_url)
		return_value_json = json.loads(return_value.text)
		address = return_value_json['results'][1]['formatted_address']
		address_list += [str(i[1]) + ': ' + address]
		print(address_list)
	return render_template('history.html', history=address_list, dates=date_list)
# @app.route("/editProfile", methods=['GET', 'POST'])
# def edit_user():
# 	cursor = conn.cursor()
# 	try:
# 		if request.form.get('email') == '':
# 			cursor.execute("")
# 		email=request.form.get('email')
# 		password=request.form.get('password')
# 		first_name=request.form.get('first_name')
# 		last_name=request.form.get('last_name')
# 		dob=request.form.get('dob')
# 		gender=request.form.get('gender')
# 		address=request.form.get('address')
# 	except:
# 		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
# 		return flask.redirect(flask.url_for('register'))
# 	cursor = conn.cursor()
# 	test =  isEmailUnique(email)
# 	if test:
# 		print(cursor.execute("INSERT INTO Users (email, password, first_name, last_name, dob, gender, address) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}')".format(email, password, first_name, last_name, dob, gender, address)))
# 		conn.commit()
# 		#log user in
# 		user = User()
# 		user.id = email
# 		flask_login.login_user(user)
# 		return render_template('search.html', message='Account Created!')
# 	else:
# 		print("couldn't find all tokens")
# 		return flask.redirect(flask.url_for('register'))


if __name__ == "__main__":
	app.debug=True
	app.run()
