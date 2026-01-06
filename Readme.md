# SeeGestAPI
### Author: Wiktor Fajkowski

## Short Description
SeeGest is a social platform that enables users to discover and share local information via an interactive map and time-based filtering. The system consists of a cross-platform Flutter mobile application and a responsive Vue.js web portal.

This Flask-based REST API serves as the unified backend for both platforms, managing user registration, sessions, and secure authentication via Google and Facebook. It handles the full lifecycle of posts and comments while integrating Google Maps services for geospatial search and location-based suggestions.

## Using an online demo

This API is currently available at https://api.seegest.com/.
if you want to test it out, you will find an OpenAPI documentation at https://api.seegest.com/docs. More information will be also provided in the later sections of this docs.

## Local setup
If you prefer to run the API locally, you can follow instructions below.

### Project Download

1. Clone this repository to your local machine
```bash
 git clone https://github.com/kremobil/SeeGestAPI.git
```
2. Navigate to the project directory
```bash
cd ./SeeGestAPI 
```

### Prerequisites
In order to run this API locally whether using docker or python virtual environment, you will need the secrtkeys for Google Maps API key, Google OAuth token and some smtp credentials.

#### Google Cloud Platform Configuration
To generate Google API key and OAuth 2.0 Client ID you need to have a Google Cloud Platform account. You can follow the instructions [here](https://cloud.google.com/maps-platform/getting-started).
After creating the account, you will need to create a new project and navigate to APIs & Services > Credentials.
Then you need to create a new API key and enable Geocoding API and Places API (New.
You will also need to generate OAuth 2.0 Client ID credentials.

#### SMTP Configuration
You will need to create an account on a SMTP provider and generate SMTP credentials.
One of the ways to do this for testing purposes is to use gmail [app passwords](https://support.google.com/mail/answer/185833?hl=en). You can enter this [link](https://myaccount.google.com/apppasswords) and generate one for yourself, after doing so you will have all the credentials you require to run the API locally.

#### Entering the credentials
Once you have all the credentials, you can copy `.env.example` file to `.env` and enter your credentials there. or use a dediceted script which will additionally generate a random secret key for you JWT secret. To run the script:
```bash
python generate_secrets.py
```
once you have the secrets, you can proceed with one of the following methods.

### Docker setup (recommended) - Requires Docker and Docker Compose
1. Once the docker is running just enter
```bash
docker-compose up
```
2. The API will be available at https://127.0.0.1:5000/

### Python virtual environment setup - Requires Python
1. First create the virtual environment inside the project's folder (This step is optional but highly recommended)
```bash
python -m venv .venv
/.venv/Scripts/activate
```
note that it may require to enter `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` on Windows machines.
2. Install all the requirements
```bash
pip install -r requirements.txt 
```
3. Run API
```
flask run --cert=adhoc
```

### Working with the API
Once the API is running, you can use any REST client to test the API. The OpenAPI documentation can be found at https://api.seegest.com/docs or if you are running the API locally at https://127.0.0.1:5000/docs.

### API's Security
Some of the API's endpoints are secured with JWT authentication. To obtain a JWT token, you can use either use `/login`, `/facebook-login`, or `/google-login` endpoint. *Note that you need to have a token to use google or facebook login.*
After using one of those endpoints, you will receive a JWT token in the response. You can use this token to access any of the secured endpoints. In order to do so, you need to add `Authorization: Bearer <token>` header to your request.