#!/usr/bin/python3
from   flask          import Flask, render_template, url_for, g, request, session
from   flask_socketio import SocketIO, join_room, leave_room
import json
import genHtml
import Poller
import sys
import threading
import time

app      = Flask(__name__, static_url_path='', static_folder='static', template_folder='templates')
app.config["SECRET_KEY"] = 'xokrot!'

socketio = SocketIO(app, async_mode='eventlet', logger=False, engineio_logger=False)
poller   = Poller.Poller()

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
  print("session", session)
  ids = json.loads(data)
   # Get first results fast
  res = Poller.Result() 
  subs = session["SUBS"]
  for anid in ids:
    try:
      el  = theDb[anid]
      join_room( el.getHtmlId() )
      poller.subscribe( el )
      subs.add( el )
      res.submit( el )
      elp = el.getPath()
      print(elp.toString())
    except KeyError:
      print("Warning: key {} not found".format(anid))
  res.complete()

@socketio.on('unsubscribe')
def handle_unsubscription(data):
  print("UNSUBS", request.sid)
  ids = json.loads(data)
  subs = session["SUBS"]
  for anid in ids:
    print("checking ", anid)
    try:
      el  = theDb[anid]
      poller.unsubscribe( el )
      subs.discard( el )
      leave_room( el.getHtmlId() )
      print(theDb[anid].getPath().toString())
    except KeyError:
      print("Warning: key {} not found".format(anid))

@socketio.on('setVal')
def handle_setVal(data):
  l = json.loads(data)
  print("SETVAL", data)
  for anid, v in l:
    try:
      theDb[anid].setVal( v )
    except KeyError:
      print("Warning: key {} not found".format(anid))
    

def ticker():
  while True:
    poller.poll()
    socketio.sleep(5)

@socketio.on('connect')
def handle_connect():
  print("CONN", request.sid)
  session["SUBS"] = set()

@socketio.on('disconnect')
def handle_disconnect():
  print("DISCONN", request.sid)
  print("Session stuff was", session) 
  for el in session["SUBS"]:
    poller.unsubscribe( el )

if __name__ == '__main__':
  rp, filename = genHtml.parseOpts( sys.argv )
  genHtml.setSocketio( socketio )
  global theDb
  theDb = genHtml.writeFile( rp, "templates/guts.html" )
  for el in theDb:
    print(el)
  socketio.start_background_task( ticker )
  socketio.run(app, host='0.0.0.0', port=8000)
  print("Leaving App")
