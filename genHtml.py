#!/usr/bin/python3

import sys
import getopt
import re
import os
import yaml_cpp
import pycpsw
import io
import json
from   cityhash import CityHash32
import flask_socketio
import eventlet.semaphore
import jinja2

_ReprOther  = 0
_ReprInt    = 1
_ReprString = 2
_ReprFloat  = 3

_useTemplates = True

j2env = jinja2.Environment(
         loader     = jinja2.PackageLoader('genHtml','templates'),
         autoescape = jinja2.select_autoescape(['html', 'xml'])
       )

def setSocketio(sio):
  global _socketio
  _socketio = sio

class LeafEl(pycpsw.AsyncIO):

  def __init__(self, path, arraysOk = False, vb = None):
    super(LeafEl,self).__init__()
    self._path       = path
    self._reprUndef  = True
    self._readOnly   = True
    self._writeOnly  = False
    self._hash       = CityHash32( path.toString() )
    self._id         = "v_{:d}".format(self._hash)
    self._refcnt     = 0
    self._res        = list()
    self._arraysOk   = arraysOk
    try:
      if None == vb:
        vb = pycpsw.Val_Base.create( self._path )

      self._repr = { "NONE" : _ReprOther, "CUSTOM_0" : _ReprInt, "IEEE_754" : _ReprFloat, "ASCII" : _ReprString }.get( vb.getEncoding() )
      if None == self._repr:
        self._repr = _ReprOther
      else:
        self._reprUndef = False
    except pycpsw.InterfaceNotImplementedError:
      self._repr = _ReprOther

  def getRef(self):
    return self._refcnt

  def arraysOk(self):
    return self._arraysOk

  def incRef(self):
    if self._refcnt == 0:
      self.create()
    self._refcnt += 1
    return self._refcnt

  def decRef(self):
    self._refcnt -= 1
    if 0 == self._refcnt:
      self.destroy()
    return self._refcnt

  def reprIsUndef(self):
    return self._reprUndef

  def getRepr(self):
    return self._repr

  def setRepr(self, representation):
    self._repr = representation

  def getPath(self):
    return self._path

  def setReadOnly(self, ro):
    self._readOnly = ro

  def isReadOnly(self):
    return self._readOnly

  def setWriteOnly(self, wo):
    self._writeOnly = wo

  def isWriteOnly(self):
    return self._writeOnly

  def getHtml(self, level):
    if self.isWriteOnly():
      clss = " WO"
    else:
      clss = ""
    return "div", clss, '', [], ''

  def getHash(self):
    return self._hash

  def getHtmlId(self):
    return self._id

  def create(self):
    if self._fact != None:
      self._val = self._fact.create( self.getPath() )

  def destroy(self):
    self._val = None

  def callback(self, *args):
    ## Assume lit pop is atomic (thread safe)!
    r = self._res.pop(0)
    r.append( self, args )

  def update(self, args):
    pass

  def getValAsync(self, result):
    if not self.isWriteOnly() and self._val != None:
      ## Assume list append is atomic (thread safe)!
      self._res.append( result )
      self._val.getValAsync( self )
      return True
    return False

  def setVal(self, val):
    if not self.isReadOnly() and self._val != None:
      self._val.setVal( val )

  def getVal(self):
    if not self.isWriteOnly() and self._val != None:
      return self._val.getVal()
    return None

class ScalValEl(LeafEl):

  _checkId   = 0

  @staticmethod
  def checkId():
    ScalValEl._checkId += 1
    return ScalValEl._checkId

  def __init__(self, path, arraysOk = False):
    self._isSigned = False
    try:
      self._svb = pycpsw.ScalVal_Base.create( path )
      self._isSigned = self._svb.isSigned()
    except pycpsw.InterfaceNotImplementedError:
      self._svb = None
    self._cachedVal = None

    super(ScalValEl, self).__init__(path, arraysOk, self._svb)

    if self.getPath().getNelms() > 1:
      if self.getRepr() != _ReprString: 
        if None != self._svb:
          if self.reprIsUndef() and self._svb.getSizeBits() == 8:
            self.setRepr( _ReprString )
          elif not self.arraysOk():
            raise pycpsw.InterfaceNotImplementedError("Non-String arrays (ScalVal) not supported")
    else:
      if self.getRepr() == _ReprOther and self._svb != None:
        self.setRepr( _ReprInt )
    # if this is 'other' it is not a ScalVal but could still be a DoubleVal
    if self.getRepr() in (_ReprOther, _ReprFloat):
      try:
        self._fact = pycpsw.DoubleVal
        self.create()
        self.setReadOnly( False )
      except pycpsw.InterfaceNotImplementedError:
        self._fact = pycpsw.DoubleVal_RO
        self.create()
      self._isFloat = True
    else:
      try:
        self._fact = pycpsw.ScalVal
        self.create()
        self.setReadOnly( False )
      except pycpsw.InterfaceNotImplementedError:
        self._fact = pycpsw.ScalVal_RO
        self.create()
      self._isFloat = False
    self.destroy()

  def isSigned(self):
    return self._isSigned

  def getHtml(self, level):
    if self.arraysOk():
      raise RuntimeError("Cannot generate HTML for ScalVal array")
    tag, clss, atts, xtra, xcol = super(ScalValEl, self).getHtml( level )
    enm = None
    if None != self._svb:
      enm = self._svb.getEnum()
      if None != enm:
        tag  = "select"
        if self.isReadOnly():
          atts += ' disabled=true'
        for e in enm.getItems():
            xtra.append('{:<{}s}<option>{}</option>'.format('', 2, e[0]))
        return tag, clss, atts, xtra, xcol
    tag  = 'input'
    atts += ' type="text" value="???"'
    if self.isReadOnly():
      atts += ' readonly'
    if self._isFloat:
      clss += " float"
    else:
      clss += " int"
    if None == enm and not self._isFloat and _ReprString != self.getRepr():
      if not self.isSigned():
        checked = ' checked'
      else:
        checked = ''
      if _useTemplates:
        xcol = j2env.get_template("hexcheck.html").render(id=self.checkId(), checked=checked, level=level)
      else:
        xcol = '<input type="checkbox" id="c_{:x}" class="hexFmt {}" {}><div class="tooltip"><p>Toggle Hex Display Format.</p><p>(Input format always accepts \'0x\' prefix.)</p></div>'.format( self.checkId(), checked, checked )
    return tag, clss, atts, xtra, xcol

  def update(self, args):
    if self.arraysOk():
      raise RuntimeError("Cannot update for ScalVal array")
    if args[0] != None:
      if _ReprString == self.getRepr():
        print("decoding {}".format(bytearray(args[0]))) 
        barr = bytearray(args[0]) 
        try:
          end = barr.index(0)
        except ValueError:
          end = len(barr)
        val = barr[0:end].decode('ascii')
      else:
        val = args[0]
      self._cachedVal = val
      d = [ ( self.getHtmlId(), val ) ]
      _socketio.emit('update', json.dumps( d ), room=self.getHtmlId())

    
class CmdEl(LeafEl):

  def __init__(self, path, arraysOk = False):
    super(CmdEl, self).__init__( path, arraysOk )

    if path.getNelms() > 1 and not self.arraysOk():
      raise pycpsw.InterfaceNotImplementedError("Arrays of commands not supported")
    self._fact = pycpsw.Command
    # verify we can create
    self.create()
    self.destroy()

    self.setReadOnly( False )
    self.setWriteOnly( True )

  def getHtml(self, level):
    if self.arraysOk():
      raise RuntimeError("Cannot generate HTML for CmdVal array")
    tag, clss, atts, xtra, xcol = super(CmdEl, self).getHtml( level )
    xtra.append('Execute')
#FLOX    xtra.append('<td></td>')
    clss += " cmd"
    return "button", clss, atts, xtra, xcol

  def setVal(self, val):
    self._val.execute()

class Fixup(pycpsw.YamlFixup):
  def __init__(self):
    super(Fixup, self).__init__()

  def __call__(self, rootNode, topNode):
    rootNode["class"].set("NullDev")

class HtmlVisitor(pycpsw.PathVisitor):

  _indent    =  2
  _maxExpand = 10

  def __init__(self):
    super(HtmlVisitor, self).__init__()
    self._level  = 0
    self._id     = 0
    self._dict   = dict()
    self._fd     = sys.stdout

  def idnt(self, formatted):
    print("{:<{}s}{}".format('',self._level, formatted), file=self._fd)

  def visitPre(self, here):
    h = here.tail().isHub()
    if None != h:
      leaves = []
      for child in h.getChildren(): 
        if None == child.isHub():
          leaves.append( child )
      p = here.parent()
      myName = h.getName()
      if None != p:
        if 1 < p.findByName( myName ).tail().getNelms():
          myName = "{}[{}]".format(myName, here.getTailFrom())
      self.idnt('<li class="dir"><span class="caret">{}</span>'.format(myName))
      self.idnt('<ul class="nested" id=n_0x{:x}>'.format(self._id))
      self._id = self._id + 1
      self._level  = self._level + self._indent
      if len(leaves) > 0:
        self.idnt('<li><table class="leafTable">')
        for l in leaves:
          try:
            nelms = l.getNelms()
            if nelms > 1:
               try:
                 vb = pycpsw.Val_Base.create( here.findByName( l.getName() ) )
                 if vb.getEncoding() == "ASCII":
                   # don't expand strings
                   nelms = 1
               except pycpsw.CPSWError:
                 pass
            if nelms > self._maxExpand:
              raise RuntimeError("Leaves with more than {} elements not supported".format( self._maxExpand ))
            if nelms > 1:
              idxRange = [ '[{}]'.format(i) for i in range(l.getNelms())]
            else:
              idxRange = [ '' ]
            for idx in idxRange:
              nam = l.getName() + idx
              pn  = here.findByName( nam )
              for ELT in [ScalValEl, CmdEl]:
                try:
                  el = ELT( pn )
                  tag, clss, atts, xtra, xcol = el.getHtml( self._level )
                  # JS integer range is only 2**64 - 2**53
                  h  = el.getHash()
                 
                  if _useTemplates:
                    leaf = j2env.get_template('leaf.html')
                    print( leaf.render(
                              name    = nam,
                              tag     = tag,
                              id      = el.getHtmlId(),
                              classes = clss,
                              atts    = atts,
                              xtras   = xtra,
                              xcol    = xcol,
                              desc    = l.getDescription(),
                              level   = self._level),
                            file = self._fd )
                  else:
                    self.idnt('<tr><td>{}</td><td><{} id={} class="leaf{}" {}>'.format(nam, tag, el.getHtmlId(), clss, atts) );
                    for xt in xtra:
                      self.idnt('{:<{}s}{}'.format('', 2, xt))
                    self.idnt('{:<{}s}</{}></td><td>{}</td><td>{}</td></tr>'.format('', 2, tag, xcol, l.getDescription()))
                   
#                val = pycpsw.ScalVal_Base.create( here.findByName( nam ) )
#                enm = val.getEnum()
#                if None != enm:
#                  self.idnt('<tr><td>{}</td><td><select class="leaf" id={}>'.format(nam, self._id));
#                  for e in enm.getItems():
#                    self.idnt('{:<{}s}<option>{}</option>'.format('', 2, e[0]))
#                  self.idnt('{:<{}s}</tr>'.format('', 2, l.getDescription()))
#                else:
#                  self.idnt('<tr><td>{}</td><td><input type="text" class="leaf" id={} value="{}" onchange="alert(parseInt(this.value,0))"></input></td><td>{}</td></tr>'.format(
#                    nam,
#                    self._id,
#                    'xxx',
#                    l.getDescription()
#                  ))
                  self._id = self._id+1
                  self._dict[h] = el
                  break
                except pycpsw.InterfaceNotImplementedError:
                  pass
              else:
                self.idnt('<tr><td>{}</td><td id="leaf" class="notsupported">(not supported)</td><td>{}</td></tr>'.format(
                  nam,
                  l.getDescription()
                ))
                print("WARNING: unable to create leaf node for {}/{}".format(here, nam), file=sys.stderr)
          except RuntimeError as e:
            self.idnt('<tr><td>{}</td><td id="leaf" class="notsupported">(not supported)</td><td>{}</td></tr>'.format(
              l.getName(),
              l.getDescription()
            ))
            print("WARNING: unable to create leaf node for {}/{}".format(here, l.getName()), file=sys.stderr)
            print(e, file=sys.stderr)
        self.idnt('</table></li>')
    return True

  def visitPost(self, here):
    h = here.tail().isHub()
    if None != h:
      self._level = self._level - self._indent
      self.idnt('</ul>')
      self.idnt('</li>')
    return

  def getDict(self):
    return self._dict

  def genHtmlFile(self, rp, fd):
    self._fd   = fd
    self._dict = {}
    print('{% extends "tree/tree.html" %}',             file=fd)
    print('{% block content %}',                        file=fd)
    rp.explore( self )
    print('{% endblock content %}',                     file=fd)

def parseOpts(oargs):

  ( opts, args ) = getopt.getopt(
                      oargs[1:],
                      "hFf:",
                      ["help",
                      ])

  filename = None
  fixYaml  = Fixup()

  for opt in opts:
    if opt[0] in ('-h', '--help'):
      print("Usage: {}  [-h] [-F] [--help] yaml_file [root_node [inc_dir_path]]".format(oargs[0]))
      print()
      print("          yaml_file            : top-level YAML file to load (required)")
      print("          root_node            : YAML root node (default: \"root\")")
      print("          inc_dir_path         : directory where to look for included YAML files")
      print("                                 default: directory where 'yaml_file' is located")
      print("          -F                   : no YAML Fixup which removes all communication")
      print()
      print("    --help/-h                  : This message")
      return
    elif opt[0] in ('-f'):
      filename = opt[1]
    elif opt[0] in ('-F'):
      fixYaml  = None

  if len(args) > 0:
    yamlFile = args[0]
  else:
    print("usage: {} [options] <yaml_file> [yaml_root_node_name='root' [yaml_inc_dir=''] ]".format(oargs[0]))
    sys.exit(1)
  if len(args) > 1:
    yamlRoot = args[1]
  else:
    yamlRoot = "root"
  if len(args) > 2:
    yamlIncDir = args[2]
  else:
    yamlIncDir = None

  rp = pycpsw.Path.loadYamlFile(
              yamlFile,
              yamlRoot,
              yamlIncDir,
              fixYaml)

  return rp, filename

def makeEl(p):
  print("Making el for '{}'".format(p.toString()))
  for ELT in [ScalValEl, CmdEl]:
    try:
      el = ELT( p, True )
      return el
    except pycpsw.InterfaceNotImplementedError:
      pass
  raise pycpsw.InterfaceNotImplementedError("This node has no supported interface")

def writeFile(rp, filename):
  if None != filename:
    fd = io.open(filename,"w")
  else:
    fd = sys.stdout

  vis = HtmlVisitor()

  vis.genHtmlFile( rp, fd )

  if None != filename:
    fd.close()

  return vis.getDict()

if __name__ == '__main__':
  rp, filename = parseOpts( sys.argv )
  writeFile(rp, filename)
