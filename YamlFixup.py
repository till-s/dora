import pycpsw

class YamlFixup(pycpsw.YamlFixup):

  def __init__(self, argDict, args):
    super(YamlFixup, self).__init__()
    self.useNullDev_ = argDict["UseNullDev"]
    self.ip_         = "<NONE>"
    self.setIp_      = argDict["IpAddress" ]
    self.blacklist_  = []

  def __call__(self, rootNode, topNode):
    n = topNode["GuiBlacklist"]
    if n.IsDefined() and not n.IsNull():
      for it in n:
        self.blacklist_.append( it.getAs() )

    if self.useNullDev_:
      rootNode["class"].set("NullDev")

    n = pycpsw.YamlFixup.findByName(rootNode, "ipAddr")
    if n.IsDefined() and not n.IsNull():
      if None != self.setIp_:
        n["ipAddr"].set(self.setIp_)
      self.ip_ = n.getAs()

  def getInfo(self):
    return { "ipAddr": self.ip_ }

  def getBlacklist(self):
    if 0 == len( self.blacklist_ ):
      return None
    return self.blacklist_


