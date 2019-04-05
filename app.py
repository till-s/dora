#!/usr/bin/python3
from   flask          import Flask, render_template, url_for, g, request, session, send_from_directory, Response, send_file
from   flask_socketio import SocketIO, join_room, leave_room
import json
import genHtml
import Poller
import sys
import threading
import time
import pycpsw
import io

app      = Flask(__name__, static_url_path='', static_folder='static', template_folder='templates')
app.config["SECRET_KEY"] = '7e065b7a145789087577f777da89ca062aa18101'

socketio = SocketIO(app, async_mode='eventlet', logger=False, engineio_logger=False)
poller   = Poller.Poller()

@app.route('/')
def hello_world():
  return render_template('guts.html')

@app.route('/getVal')
def get_val():
  p = request.args.get("path")
  d = dict()
  if None != p:
    try:
      print("Making")
      el = genHtml.makeEl( rp.findByName( p ) )
      print("Creating")
      el.create()
      print("Getting")
      d["value"] = el.getVal()
      print("Got {}".format(d["value"]))
      el.destroy()
    except pycpsw.CPSWError as e:
      d["error"] = e.what()
  return Response( json.dumps( d  ) )

@app.route('/loadConfig', methods=["POST"])
def load_config():
  p = request.args.get("path")
  j = request.args.get("json")
  d = dict()
  print("POST got request", request.get_data())
  try:
    dstr = request.get_data().decode("UTF-8", "strict")
    path = rp.findByName( p )
    s    = path.loadConfigFromYamlString( dstr )
    d["result"] = s
  except pycpsw.CPSWError as e:
    s = e.what()
    d["error"]  = s
  if None != j and j:
    s = json.dumps( d )
  return Response( s )
    

@app.route('/saveConfig', methods=["GET", "POST"])
def save_config():
  p = request.args.get("path")
  j = request.args.get("json")
  d = dict()
  if request.method == "POST":
    print("POST got request", request.get_data())
    print("POST got path",    p)
  else:
    print("GET")
  try:
    path      = rp.findByName( p )
    tmpl      = request.get_data().decode("UTF-8", "strict")
    s         = path.dumpConfigToYamlString(tmpl, None, False).decode('UTF-8', 'strict')
    d["yaml"] = s
  except pycpsw.CPSWError as e:
    s          = e.what()
    d["error"] = s
  if None != j and j:
    s = json.dumps( d )
  
  return send_file( io.BytesIO( s.encode("UTF-8") ), mimetype="application/x-yaml", as_attachment=True, attachment_filename="config.yaml")

@app.route('/<path:path>')
def foo(path):
  return send_from_directory('', path)


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
  global rp
  rp, filename = genHtml.parseOpts( sys.argv )
  genHtml.setSocketio( socketio )
  global theDb
  theDb = genHtml.writeFile( rp, "templates/guts.html" )
  for el in theDb:
    print(el)
  socketio.start_background_task( ticker )
  socketio.run(app, host='0.0.0.0', port=8000)
  print("Leaving App")
