from flask import Flask, request, redirect
from flask import Flask, render_template, url_for
from flask import jsonify
import requests
import json

app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def main():
	return render_template('index.html')


@app.route("/results", methods=['POST'])
def success():
	date = request.form.get('date')
	
	return ("date = %s " % date)	### replace with results from API call


if __name__ == "__main__":
	app.debug = True
	app.run()
