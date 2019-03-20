import threading
import time

class Poller(threading.Thread):

  def __init__(self, period):
    super(Poller, self).__init__()
    self._period = period
    self._lock   = threading.Lock()
    self._active = dict()
    self._now    = time.time()

  def run(self):
    while True:
      self._now   += self._period
      time.sleep(self._now - time.time())
      print("tick")
      with self._lock:
        for el in self._active.values():
          print("polling {}".format(el.getHtmlId()))
          el.getValAsync()

  def subscribe(self, el):
    with self._lock:
      if 1 == el.incRef():
        self._active[el.getHash()] = el

  def unsubscribe(self, el):
    with self._lock:
      if 0 == el.decRef():
        del( self._active[el.getHash()] )
