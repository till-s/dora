import threading
import time
import pycpsw
import eventlet.semaphore
import eventlet.tpool

# This must be executed from a 'normal' thread
# (pycpsw callbacks)
class Result:
  def __init__(self):
    self._lock = threading.Lock()
    self._ev   = threading.Event()
    self.reset()

  def reset(self):
    self._l = list()
    self._awaited   = -1
    self._submitted = 0
    self._ev.clear()

  def submit(self, el):
    if el.getValAsync( self ):
      self._submitted += 1

  # Executed from CPSW callback thread
  def append(self, el, val):
    with self._lock:
      self._l.append( (el, val) )
      if len( self._l ) == self._awaited:
        self._ev.set()

  # Executed from tpool ('real') thread
  def wait(self):
    # all callbacks might have arrived already
    with self._lock:
      if len( self._l ) == self._submitted:
        return
      else:
        self._awaited = self._submitted
    self._ev.wait()

  def complete(self):
    eventlet.tpool.execute( Result.wait, self )
    for e,v in self._l:
      e.update( v )
    rval    = len( self._l )
    self._l = None
    return rval

# Poll from eventlet/green thread
class Poller:

  def __init__(self):
    super(Poller, self).__init__()
    self._lock   = eventlet.semaphore.BoundedSemaphore()
    self._active = dict()
    self._res    = Result()

  # Assume only ONE green thread is executing 'poll'
  # (of this instance!)
  def poll(self):
    with self._lock:
      self._res.reset()
      for el in self._active.values():
        self._res.submit( el )
    n = self._res.complete()
    print("{} values polled".format( n ))
    
  def subscribe(self, el):
    with self._lock:
      if 1 == el.incRef():
        self._active[el.getHash()] = el

  def unsubscribe(self, el):
    with self._lock:
      if 0 == el.decRef():
        del( self._active[el.getHash()] )
