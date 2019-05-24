import re
import pathGrep as pg
import sys
import jinja2
import io

j2env = jinja2.Environment(
         loader     = jinja2.PackageLoader('genSimple','templates'),
         autoescape = jinja2.select_autoescape(['html', 'xml'])
       )

class GenSimple(object):
  def __init__(self, theDb, tmplName):
    self._level = 0
    self._db    = theDb
    self._fd    = io.open(tmplName, "w")
    print( '{% extends "simple.html" %}', file = self._fd )
    print( '{% block content         %}', file = self._fd )
    print( '<table id="miscTable">',      file = self._fd )
    print( '<caption>General Configuration</caption>', file = self._fd )
    print( '<tr> <td> <a href="/"     class="realLink">General Info</a> </td> </tr>', file = self._fd )
    print( '<tr> <td> <a href="/tree" class="realLink">Expert Panel</a> </td> </tr>', file = self._fd )
    print( '<tr> <td> <form method="post" action="/saveConfig?file=config/simple.yaml">', file = self._fd )
    print( '     <button class="configButton" type="submit">Save Configuration</label>', file = self._fd )
    print( '     </form> </td>',          file = self._fd )
    print( '<tr> <td>',                   file = self._fd )
    print( '	<label class="configButton">Load Configuration<input type="file" class="loadConfig"> </label>', file = self._fd )
    print( '</td> </tr>',                 file = self._fd )
    print( '<tr>',                        file = self._fd )
    self.genTab(".*TimingFrameRx/{}", [ ["ClkSel", ""], ["FidCount", ""] ])
    print( '</tr>',                       file = self._fd )
    print( '</table>',                    file = self._fd )
    nams        = []
    nams.append( ["Width",      ''] )
    nams.append( ["Delay",      ''] )
    nams.append( ["Polarity",   ''] )
    nams.append( ["Enable",     ''] )
    nams.append( ["Source",     ' class="selSourceMode"'] )
    print( '<table id="outputTable" class="outputTable">',    file = self._fd )
    print( '<caption>Trigger Output Configuration</caption>', file = self._fd )
    print( '<tr>', file = self._fd )
    print( '<th>Output</th>', file = self._fd )
    for i in range( len( theDb.pg( ".*EvrV2TriggerReg[^/]*$" ) ) - 1, -1 , -1 ):
      print('<th>{}</th>'.format(i),      file = self._fd)
    print( '</tr>',                       file = self._fd )
    self.genTab( ".*EvrV2TriggerReg.*/{}$", nams )
    print( '</table>',                    file = self._fd )
    #
    nChs = len( theDb.pg( ".*EvrV2ChannelReg[^/]*$" ) )
    itms = []
    itms.append( ["Enable",         ''] )
    itms.append( ["Count",          ''] )
    itms.append( ["DestSelMode",    ''] )
    itms.append( ["DestSelMask",    ''] )
    itms.append( ["RateSelMode",    ' class="selRateMode"'] )
    itms.append( ["ACRate",         ' class="rateModeAC isModal"']    )
    itms.append( ["ACTimeSlotMask", ' class="rateModeAC isModal"']    )
    itms.append( ["FixedRate",      ' class="rateModeFixed isModal"'] )
    itms.append( ["SequenceSelect", ' class="rateModeSeq isModal"']   )
    print( '<table id="allChannels">',      file = self._fd )
    print( '<caption>Channel Configuration</caption>', file = self._fd )
    print( '<tr    id="allChannelsRow">',   file = self._fd )
    for i in range(nChs):
      print( '<tr><td><p class="caret colmn{} chnllab">Channel {}'.format(i,i), file = self._fd )
      print( '<table id="channelTable{}" class="channelTable nested">'.format(i),   file = self._fd )
      for itm in itms:
        self.genTab( ".*EvrV2ChannelReg[\[]{}]/{}$".format(i,'{}'), [itm], colOff = i, withLab = True)
      print( '</table></p></td></tr',              file = self._fd )
    print( '</tr>',                        file = self._fd )
    print( '</table>',                     file = self._fd )
    print( '{% endblock content      %}', file = self._fd )
    self._fd.close()

  def genTab(self, patt, itms, colOff = 0, withLab = None):
    for itm in itms:
      nam         = itm[0]
      paths       = self._db.pg( patt.format(nam) )
      i           = 0
      print( "<tr{}>".format(itm[1]), file = self._fd )
      for p in paths:
        try:
          el = self._db.lkups( p.toString() )
        except KeyError as e:
          print("Failure to find key for ", p.toString())
          raise
        tag, clss, atts, xtra, xcol = el.getHtml( self._level )
        if 0 == i:
          #print( '<td display="None"><div class="tooltip"><p>', file = self._fd )
          #print( '{%- autoescape true -%}',  file = self._fd )
          with el as theel:
            tip = theel[1].getDescription()
          #print( '{%- endautoescape   -%}',  file = self._fd )
          #print( '</p></div></td>',               file = self._fd )
          if None != withLab and not withLab:
            nam = None
        else:
          if None == withLab or not withLab:
            nam = None
        desc = None
        elem = j2env.get_template('elem.html')
        clss += " toolTipper colmn{}".format(colOff + i)
        print( elem.render(
                            name    = nam,
                            tag     = tag,
                            id      = el.getHtmlId(),
                            classes = clss,
                            atts    = atts,
                            xtras   = xtra,
                            xcol    = None,
                            desc    = desc,
                            tooltip = tip,
                            level   = self._level),
                            file = self._fd )
        i += 1
      print( "</tr>", file = self._fd )
