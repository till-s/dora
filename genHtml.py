#!/usr/bin/python3

import sys
import getopt
import re
import os
import yaml_cpp
import pycpsw
import io
from   cityhash import CityHash32

_ReprOther  = 0
_ReprInt    = 1
_ReprString = 2
_ReprFloat  = 3

class LeafEl(pycpsw.AsyncIO):

  def __init__(self, path, vb = None):
    super(LeafEl,self).__init__()
    self._path       = path
    self._reprUndef  = True
    self._readOnly   = True
    self._writeOnly  = False
    self._hash       = CityHash32( path.toString() )
    self._id         = "v_{:d}".format(self._hash)
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

  def getHtml(self):
    if self.isWriteOnly():
      clss = " WO"
    else:
      clss = ""
    return "div", clss, '', []

  def getHash(self):
    return self._hash

  def getHtmlId(self):
    return self._id

  def callback(self, *args):
    pass

class ScalValEl(LeafEl):

  def __init__(self, path):
    try:
      self._svb = pycpsw.ScalVal_Base.create( path )
    except pycpsw.InterfaceNotImplementedError:
      self._svb = None

    super(ScalValEl, self).__init__(path, self._svb)

    if self.getPath().getNelms() > 1:
      if self.getRepr() != _ReprString: 
        if None != self._svb:
          if self.reprIsUndef() and self._svb.getSizeBits() == 8:
            self.setRepr( _ReprString )
          else:
            raise pycpsw.InterfaceNotImplementedError("Non-String arrays (ScalVal) not supported")
    else:
      if self.getRepr() == _ReprOther and self._svb != None:
        self.setRepr( _ReprInt )
    # if this is 'other' it is not a ScalVal but could still be a DoubleVal
    if self.getRepr() in (_ReprOther, _ReprFloat):
      try:
        pycpsw.DoubleVal.create( self.getPath() )
        self.setReadOnly( False )
      except pycpsw.InterfaceNotImplementedError:
        pycpsw.DoubleVal_RO.create( self.getPath() )
      self._isFloat = True
    else:
      try:
        pycpsw.ScalVal.create( self.getPath() )
        self.setReadOnly( False )
      except pycpsw.InterfaceNotImplementedError:
        pycpsw.ScalVal_RO.create( self.getPath() )
      self._isFloat = False

  def getHtml(self):
    tag, clss, atts, xtra = super(ScalValEl, self).getHtml()
    if None != self._svb:
      enm = self._svb.getEnum()
      if None != enm:
        tag  = "select"
        if self.isReadOnly():
          atts += ' disabled=true'
        for e in enm.getItems():
            xtra.extend('{:<{}s}<option>{}</option>'.format('', 2, e[0]))
        return tag, clss, atts, xtra
    tag  = 'input'
    atts += ' type="text" value="???"'
    if self.isReadOnly():
      atts += ' readonly'
    else:
      if self._isFloat:
        clss += " float"
      else:
        clss += " int"
    return tag, clss, atts, xtra
# self.idnt('<tr><td>{}</td><td><input type="text" class="leaf" id=0x{:x} value="{}" onchange="alert(parseInt(this.value,0))"></input>

  def callback(self, *args):
    if args[0] != None:
      socketio.emit('update', '{}'.format(args[0])) #, room=self.getHtmlId())
    
class CmdEl(LeafEl):

  def __init__(self, path):
    if path.getNelms() > 1:
      raise pycpsw.InterfaceNotImplementedError("Arrays of commands not supported")
    pycpsw.Command.create( path )
    super(CmdEl, self).__init__( path )
    self.setReadOnly( False )
    self.setWriteOnly( True )

  def getHtml(self):
    tag, clss, atts, xtra = super(CmdEl, self).getHtml()
    xtra.extend(['Execute'])
    return "button", clss, atts, xtra

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
      self.idnt('<li><span class="caret">{}</span>'.format(myName))
      self.idnt('<ul class="nested" id=n_0x{:x}>'.format(self._id))
      self._id = self._id + 1
      self._level  = self._level + self._indent
      if len(leaves) > 0:
        self.idnt('<li><table class="leafTable">')
        for l in leaves:
          try:
            if l.getNelms() > self._maxExpand:
              raise RuntimeError("Leaves with more than {} elements not supported".format( self._maxExpand ))
            if l.getNelms() > 1:
              idxRange = [ '[{}]'.format(i) for i in range(l.getNelms())]
            else:
              idxRange = [ '' ]
            for idx in idxRange:
              nam = l.getName() + idx
              pn  = here.findByName( nam )
              for ELT in [ScalValEl, CmdEl]:
                try:
                  el = ELT( pn )
                  tag, clss, atts, xtra = el.getHtml()
                  # JS integer range is only 2**64 - 2**53
                  h  = el.getHash()
                  self.idnt('<tr><td>{}</td><td><{} id={} class="leaf{}" {}>'.format(nam, tag, el.getHtmlId(), clss, atts) );
                  for xt in xtra:
                    self.idnt('{:<{}s}{}'.format('', 2, xt))
                  self.idnt('{:<{}s}</{}></td><td>{}</td>'.format('', 2, tag, l.getDescription()))
                   
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
    print('{% extends "tree/tree.html" %}', file=fd)
    print('{% block content %}',            file=fd)
    rp.explore( self )
    print('{% endblock content %}',         file=fd)

def parseOpts(oargs):

  ( opts, args ) = getopt.getopt(
                      oargs[1:],
                      "hf:",
                      ["help",
                      ])

  filename = None

  for opt in opts:
    if opt[0] in ('-h', '--help'):
      print("Usage: {}  [-h] [--help] yaml_file [root_node [inc_dir_path]]".format(oargs[0]))
      print()
      print("          yaml_file            : top-level YAML file to load (required)")
      print("          root_node            : YAML root node (default: \"root\")")
      print("          inc_dir_path         : directory where to look for included YAML files")
      print("                                 default: directory where 'yaml_file' is located")
      print()
      print("    --help/-h                  : This message")
      return
    elif opt[0] in ('-f'):
      filename = opt[1]

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

  fixYaml    = Fixup()

  rp = pycpsw.Path.loadYamlFile(
              yamlFile,
              yamlRoot,
              yamlIncDir,
              fixYaml)

  return rp, filename

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

def setSocketio(sio):
  global socketio
  socketio = sio

if __name__ == '__main__':
  rp, filename = parseOpts( sys.argv )
  writeFile(rp, filename)
