import pycpsw
import time
import pathGrep

class ClockSwitchAction(object):
  def __init__(self, root, yamlDir):
    super(ClockSwitchAction, self).__init__()
    pg = pathGrep.PathGrep( root, asPath=True )
    self.clkSel_     = pycpsw.ScalVal.create( pg("/TimingFrameRx/ClkSel$")[0] )
    self.clkSta_     = self.clkSel_.getVal()
    self.rrst_       = pycpsw.Command.create( pg("/TimingFrameRx/C_RxReset")[0] )
    self.si5344Path_ = pg("/Si5344$")[0]
    self.yamlDir_    = yamlDir

  def __call__(self):
    newSta = self.clkSel_.getVal(forceNumeric=True)
    if ( newSta != self.clkSta_ ):
      if 1 == newSta:
        print("Setting clock to LCLS2")
        configFile="Si5344-185.yaml"
      else:
        print("Setting clock to LCLS1")
        configFile="Si5344-119.yaml"
      n = self.si5344Path_.loadConfigFromYamlFile( self.yamlDir_ + configFile )
      print("{} config vals written".format(n))
      self.clkSta_ = newSta
      time.sleep(1.5)
      self.rrst_.execute()

  def getMask(self):
    return 1
