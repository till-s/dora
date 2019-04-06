import pycpsw
import genHtml

class InfoCollector(object):
  def __init__(self, grepper, title, patt, fmt = "{}"):
    super(InfoCollector, self).__init__()
    self.title_       = title
    self.fmt_         = fmt
    found = grepper( patt )
    print("FOUND ",found)
    if None != found and len(found) > 0:
      self.path_ = found[0]
    else:
      self.path_ = None

  def makeEl(self):
    return genHtml.makeEl( self.path_ )
  
  def collectInfo(self):
    if None == self.path_:
      return None
    with self.makeEl() as el:
      val = el.getVal()
    print("GOT VAL: ", val)
    return {"key" : self.title_, "val" : self.fmt_.format( val ) }

class LongIntCollector(InfoCollector):
  def __init__(self, grepper, title, patt, endian="LE"):
    super(LongIntCollector, self).__init__( grepper, title, patt )
    self.endian_ = endian

  def makeEl(self):
    return genHtml.ScalValEl( self.path_, arraysOk = True, array2Int = self.endian_ )
