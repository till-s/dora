import pycpsw
import threading
import pathGrep

class IrqHandler(threading.Thread):
  def __init__(self, root, actions):
    super(IrqHandler, self).__init__()
    self.daemon  = True # makes thread go away when program exits
    pg = pathGrep.PathGrep( root, asPath=True )
    self.uioIrq_ = pycpsw.ScalVal.create( root.findByName("irq") )
    self.enab_   = pycpsw.ScalVal.create( pg("/LocRegs/IrqsEnable$")[0] )
    self.pend_   = pycpsw.ScalVal_RO.create( pg("/LocRegs/IrqsPending$")[0] )
    self.mask_   = 0
    self.acts_   = actions
    for a in self.acts_:
      self.mask_ |= a.getMask()

  def enableUIO(self):
    self.uioIrq_.setVal( 1 )

  def disableUIO(self):
    self.uioIrq_.setVal( 0 )

  def waitUIO(self):
    return self.uioIrq_.getVal()

  def run(self):
    print("Entering Task")
    self.enab_.setVal( self.mask_ )
    while True:
      self.enableUIO()
      cumu = self.waitUIO()
      print("IRQ; cumulative count {}".format(cumu))
      pend = self.pend_.getVal()
      self.enab_.setVal(0)
      self.enab_.setVal(self.mask_)
      for a in self.acts_:
        if (pend & a.getMask()) != 0:
          a()
