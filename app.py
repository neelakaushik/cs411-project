from flask import Flask, request, redirect
from flask import Flask, render_template, url_for
from flask import jsonify
import requests
import json
import datetime

app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def main():
	return render_template('index.html')


@app.route("/results", methods=['POST'])
def success():
	date = request.form.get('date')
	d = datetime.datetime.strptime(date, '%m-%d-%Y')
	temp = d.strftime('%Y-%m-%d')

	
	return ("date = %s " % temp)	### replace with results from API call


if __name__ == "__main__":
	app.debug = True
	app.run()
