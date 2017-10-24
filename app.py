from flask import Flask, request, redirect
from flask import Flask, render_template, url_for
from flask import jsonify
import requests
import json
import datetime
from urllib.request import urlopen
import json


app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def main():
	return render_template('index.html')


@app.route("/results", methods=['POST'])
def success():
	date = request.form.get('date')
	d = datetime.datetime.strptime(date, '%m-%d-%Y')
	temp = d.strftime('%Y-%m-%d')
	my_request = urlopen("https://data.boston.gov/api/3/action/datastore_search?resource_id=12cb3883-56f5-47de-afa5-3b1cf61b257b&limit=235000")
	#my_request = urlopen("https://data.boston.gov/api/3/action/datastore_search?resource_id=12cb3883-56f5-47de-afa5-3b1cf61b257b&q=%s" % temp)
	response = my_request.read().decode("utf-8")
	json_data = json.loads(response)
	print(json_data['result']['records'])
	the_data = json_data['result']['records']
	count = 0
	print(len(the_data))
	incidents = []
	for i in range(len(the_data)):
		if temp in the_data[i]['OCCURRED_ON_DATE']:
			incidents += [the_data[i]]
		# print(the_data[i]['DISTRICT'])
	num_crimes = len(incidents)
	#dic = json.dumps(json_data)
	#print(dic['result'])
	# url = https://data.boston.gov/api/3/action/datastore_search?resource_id=12cb3883-56f5-47de-afa5-3b1cf61b257b&q=jones
	# fileobj = urllib.urlopen(url)
	# print(fileobj.read())
	return ("There were {0} crimes committed on {1}".format(num_crimes, date) )	### replace with results from API call


if __name__ == "__main__":
	app.debug = True
	app.run()
