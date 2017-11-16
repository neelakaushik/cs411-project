CREATE DATABASE crimebuddy;
USE crimebuddy;


CREATE TABLE Users 
(
	user_id int4 AUTO_INCREMENT NOT NULL,
	email varchar(255) UNIQUE,
	password varchar(255),
	first_name varchar(255),
	last_name varchar(255),
	dob date,
	gender varchar(255),
	address varchar(255),
	CONSTRAINT users_pk PRIMARY KEY (user_id)
);

CREATE TABLE Favorites 
(
favorite_id int4 AUTO_INCREMENT NOT NULL,
user_id int4,
FOREIGN KEY (user_id) REFERENCES Users(user_id),
location varchar(255),
type varchar(255),
access_date date,
CONSTRAINT favroites_pk PRIMARY KEY (favorite_id)
);

CREATE TABLE Lyft 
(
	user_id int4,
	FOREIGN KEY (user_id) REFERENCES Users(user_id),
	lyft_first_name varchar(255),
	lyft_last_name varchar(255),
	lyft_id varchar(255) UNIQUE
);

INSERT INTO Users (email, password) VALUES ('test@bu.edu', 'test');
INSERT INTO Users (email, password) VALUES ('test1@bu.edu', 'test');