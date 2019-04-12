# Installation

## Dependencies
* Python 3
* Python Flask
* NodeJS
* npm

They are all avaialbe through all common package repositories, Python Flask can also be installed with pip.

### Ubuntu
`apt install python3 python3-pip nodejs npm` and `pip3 install flask`

## Dependency installation
After cloning the repository and installing the above packages, go into the `gui` folder and run `npm install`.

## Usage
To start the server, go to the `engine` directory and run `export FLASK_APP=server_flask.py` and `flask run`. If you want to start the server in the background, run `flask run &`.
To start the UI, go to the `gui` directory and run `npm start`.