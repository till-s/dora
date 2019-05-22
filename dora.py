#!/usr/bin/python3
from   flask          import Flask, render_template, url_for, g, request, session, send_from_directory, Response, send_file, abort
from   flask_socketio import SocketIO, join_room, leave_room
import json
import genHtml
import Poller
import sys
import threading
import time
import pycpsw
import io
import os
import socket
import re
from   infoCollector  import InfoCollector, LongIntCollector
import pathGrep
import DoraApp
import YamlFixup
from   zeroconf       import ServiceInfo, Zeroconf, DNSQuestion, _TYPE_A, _CLASS_IN

app      = Flask(__name__, static_url_path='', static_folder='static', template_folder='templates')
app.config["SECRET_KEY"] = '7e065b7a145789087577f777da89ca062aa18101'

socketio = SocketIO(app, async_mode='eventlet', logger=False, engineio_logger=False)
poller   = Poller.Poller()

pollInterval = 2 #seconds

doraApp = DoraApp.DoraApp()

@app.route('/')
@app.route('/index.html')
def index():
  items = []
  for coll in [
    InfoCollector   (pg, "Firmware Build:", ".*AxiVersion/BuildStamp"),
    LongIntCollector(pg, "Git Hash:      ", ".*AxiVersion/GitHash", "{:x}", "LE")
    ]:
    items.append( coll.collectInfo() )
  try:
    items.append({"key": "IP Address:", "val": gblInfo["ipAddr"], "esc": True})
  except KeyError:
    pass
  items.append({"key": "Host Name:", "val": socket.gethostname(), "esc": True})
  if None != doraApp.getDebugProbesPath():
    items.append({"key": "Debug Probes File:", "val": "<a href=/debugProbes>download</a>", "esc": False})
  return render_template('info.html',
    deviceTopName = topLevelName,
    items         = items
    )

@app.route('/debugProbes')
def getDebugProbes():
  path = doraApp.getDebugProbesPath()
  if None != path:
    (d,f) = os.path.split( path )
    return send_from_directory(d, f, as_attachment=True, cache_timeout=10, mimetype='application/octet-stream')
  abort(404)


@app.route('/tree')
def expert_tree():
  return render_template(treeTemplate, deviceTopName = topLevelName)

@app.route('/getVal')
def get_val():
  p = request.args.get("path")
  d = dict()
  if None != p:
    paths = pg( p )
    try:
      d1 = list() 
      for path in paths:
        with genHtml.makeEl( path ) as el:
          d1.append({"name" : path.toString(), "value": el.getVal()} )
      d["result"] = d1
    except pycpsw.CPSWError as e:
      d["error"]  = e.what()
  return Response( json.dumps( d  ) )

@app.route("/findByName")
def find_by_name():
  p = request.args.get("path")
  d = dict()
  if None != p:
    paths = pg( p )
    try:
      d["result"] = [ path.toString() for path in paths ]
    except pycpsw.CPSWError as e:
      d["error"]  = e.what()
  return Response( json.dumps( d  ) )

@app.route('/loadConfig', methods=["POST"])
def load_config():
  p = request.args.get("path")
  j = request.args.get("json")
  d = dict()
  #print("POST got request", request.get_data())
  try:
    dstr = request.get_data().decode("UTF-8", "strict")
    print("config: ", dstr)
    if None == p:
      path = rp
    else:
      path = rp.findByName( p )
    s    = path.loadConfigFromYamlString( dstr )
    d["result"] = s
  except pycpsw.CPSWError as e:
    s = e.what()
    d["error"]  = s
  if None != j and j.upper() == "TRUE":
    s = json.dumps( d )
  else:
    s = str(s)
  #print("POST response data: ", s)
  return Response( s )
    

@app.route('/saveConfig', methods=["GET", "POST"])
def save_config():
  p = request.args.get("path")
  j = request.args.get("json")
  d = dict()
  if request.method == "POST":
    #print("POST got request", request.get_data())
    #print("POST got path",    p)
    pass
  else:
    #print("GET")
    pass
  try:
    if None == p:
      path = rp
    else:
      path = rp.findByName( p )
    tmpl      = request.get_data().decode("UTF-8", "strict")
    print('tmpl', tmpl)
    s         = path.dumpConfigToYamlString(tmpl, None, False)
    d["yaml"] = s
  except pycpsw.CPSWError as e:
    s          = e.what()
    d["error"] = s
  if None != j and j.upper() == "TRUE":
    s = json.dumps( d )
  return send_file( io.BytesIO( s.encode("UTF-8") ), mimetype="application/x-yaml", as_attachment=True, attachment_filename="config.yaml")

@app.route('/<path:path>')
def foo(path):
  return send_from_directory('', path)


@socketio.on('message')
def handle_message(data):
  #print("GOT A MESSAGE" + data)
  pass

@socketio.on('chat message')
def handle_chat_message(data):
  #print("GOT A CHAT MESSAGE" + data)
  pass

@socketio.on('subscribe')
def handle_subscription(data):
  #print("SUBS", request.sid)
  #print("session", session)
  ids = json.loads(data)
   # Get first results fast
  res = Poller.Result() 
  subs = session["SUBS"]
  for anid in ids:
    try:
      el  = theDb.lkup(anid)
      join_room( el.getHtmlId() )
      poller.subscribe( el )
      subs.add( el )
      res.submit( el )
      elp = el.getPath()
      #print(elp.toString())
    except KeyError:
      print("Warning: key {} not found".format(anid))
  res.complete()

@socketio.on('unsubscribe')
def handle_unsubscription(data):
  #print("UNSUBS", request.sid)
  ids = json.loads(data)
  subs = session["SUBS"]
  for anid in ids:
    #print("checking ", anid)
    try:
      el  = theDb.lkup(anid)
      poller.unsubscribe( el )
      subs.discard( el )
      leave_room( el.getHtmlId() )
      #print(theDb.lkup(anid).getPath().toString())
    except KeyError:
      print("Warning: key {} not found".format(anid))

@socketio.on('setVal')
def handle_setVal(data):
  l = json.loads(data)
  #print("SETVAL", data)
  for anid, v in l:
    try:
      theDb.lkup(anid).setVal( v )
    except KeyError:
      print("Warning: key {} not found".format(anid))
    

def ticker( period ):
  while True:
    poller.poll()
    socketio.sleep( period )

@socketio.on('connect')
def handle_connect():
  #print("CONN", request.sid)
  session["SUBS"] = set()

@socketio.on('disconnect')
def handle_disconnect():
  #print("DISCONN", request.sid)
  #print("Session stuff was", session) 
  for el in session["SUBS"]:
    poller.unsubscribe( el )

if __name__ == '__main__':
  global rp
  global pg
  global gblInfo
  global treeTemplate
  global theDb
  global topLevelName

  genHtml.setSocketio( socketio )

  optDict      = genHtml.parseOpts( sys.argv )

  fixYaml      = doraApp.getYamlFixup( optDict, sys.argv )

  if None == fixYaml:
    # use default
    fixYaml    = YamlFixup.YamlFixup( optDict, sys.argv )

  topLevelName = doraApp.getTopLevelName()

  yamlFile     = optDict["YamlFileName"]
  rp           = pycpsw.Path.loadYamlFile(
                   yamlFile,
                   optDict["YamlRootName"  ],
                   optDict["YamlIncDirName"],
                   fixYaml)

  httpPort     = optDict["HttpPort"]

  doraApp.initApp( rp )

  gblInfo      = fixYaml.getInfo()

  pg           = pathGrep.PathGrep( rp, patt = None, asPath = True )

  cksum        = genHtml.computeCksum( yamlFile )
  treeTemplate = "guts-{:x}.html".format( cksum )
  if os.path.isfile("templates/"+treeTemplate):
    theDb = genHtml.writeNoFile( rp, fixYaml.getBlacklist() )
  else:
    print("No template for this YAML file found; must regenerate")
    theDb = genHtml.writeFile( rp, "templates/"+treeTemplate, fixYaml.getBlacklist() )

  myname = socket.getfqdn()
  islocl = (myname.find(".") < 0)
  if islocl:
    myname = myname + ".local."
  try:
    myaddr = socket.inet_aton( socket.gethostbyname( myname ) )
  except:
    myaddr = None

  serviceInfo = ServiceInfo(type_      = "_http._tcp.local.",
                            name       = topLevelName+"._http._tcp.local.",
                            address    = myaddr,
                            port       = httpPort, 
                            properties = {'port': str(httpPort)},
                            server     = myname)
  zeroconf    = Zeroconf()
  # resolve our address via mdns:
  if None == myaddr:
    if not serviceInfo.request( zeroconf, 5000 ):
      raise RuntimeError("Unable to find my address for {}".format(myname))
  if islocl:
    q = DNSQuestion( myname, _TYPE_A, _CLASS_IN )
    # track future updates
    zeroconf.add_listener( serviceInfo, q )
  zeroconf.register_service( serviceInfo )
  try :
    socketio.start_background_task( ticker, pollInterval )
    socketio.run(app, host='0.0.0.0', port=httpPort)
  finally:
    zeroconf.unregister_service( serviceInfo )
    zeroconf.close()
