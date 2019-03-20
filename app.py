#!/usr/bin/python3
from flask import Flask, render_template, url_for, g, request
from flask_socketio import SocketIO, join_room, leave_room
import json
import genHtml
import sys

app = Flask(__name__, static_url_path='', static_folder='static', template_folder='templates')
app.config["SECRET_KEY"] = 'xokrot!'
socketio = SocketIO(app, logger=True)
genHtml.setSocketio( socketio )

def getSocketio():
  return socketio

@app.route('/')
def hello_world():
  return render_template('guts.html')

@socketio.on('message')
def handle_message(data):
  print("GOT A MESSAGE" + data)

@socketio.on('chat message')
def handle_chat_message(data):
  print("GOT A CHAT MESSAGE" + data)

@socketio.on('subscribe')
def handle_subscription(data):
  print("SUBS", request.sid)
  ids = json.loads(data)
  for anid in ids:
    print("checking ", anid)
    el  = theDb[anid]
    join_room( el.getHtmlId() )
    elp = el.getPath()
    print(elp.toString())
    el.callback(elp.tail().getName()) 

@socketio.on('unsubscribe')
def handle_unsubscription(data):
  print("UNSUBS", request.sid)
  ids = json.loads(data)
  for anid in ids:
    print("checking ", anid)
    el  = theDb[anid]
    leave_room( el.getHtmlId() )
    print(theDb[anid].getPath().toString())


@socketio.on('disconnect')
def handle_disconnect():
  print("DISCONN", request.sid)

if __name__ == '__main__':
  rp, filename = genHtml.parseOpts( sys.argv )
  global theDb
  theDb = genHtml.writeFile( rp, "templates/guts.html" )
  for el in theDb:
    print(el)
  socketio.run(app, host='0.0.0.0', port=8000)
