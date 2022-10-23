import io
import os
import re
import tarfile

# Locate YAML tarball based on firmware name

# Kernel searches firmware in these locations
# (drivers/base/firmware_loader/main.c):
#
#    static const char * const fw_path[] = {
#        fw_path_para,
#        "/lib/firmware/updates/" UTS_RELEASE,
#        "/lib/firmware/updates",
#        "/lib/firmware/" UTS_RELEASE,
#        "/lib/firmware"
#    };
#
# The 'fw_path_para' is stored in /sys/module/firmware_class/parameters/path
#
# Note: so far, we only use 'fw_path_para' and '/lib/firmware'
#
# The firmware filename is obtained from 
#
#    /sys/bus/platform/devices/prog-fpga0/file
#

def extract(where="/tmp"):
  with io.open('/sys/bus/platform/devices/prog-fpga0/file') as f:
    fwName = f.readline().strip('\n')
  with io.open('/sys/module/firmware_class/parameters/path') as f:
    fwPath = f.readline().strip('\n')
  if 0 == len(fwPath):
    fwPath = '/lib/firmware'
  fwAbsPath = os.path.realpath( fwPath + '/' + fwName )
  print(fwAbsPath)
  tarFileAbsPath = re.sub("[.]bin([.]swab)?",".cpsw.tar.gz", fwAbsPath)
  print(tarFileAbsPath)
  with tarfile.open(tarFileAbsPath, "r") as f:
    def is_within_directory(directory, target):
        
        abs_directory = os.path.abspath(directory)
        abs_target = os.path.abspath(target)
    
        prefix = os.path.commonprefix([abs_directory, abs_target])
        
        return prefix == abs_directory
    
    def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
    
        for member in tar.getmembers():
            member_path = os.path.join(path, member.name)
            if not is_within_directory(path, member_path):
                raise Exception("Attempted Path Traversal in Tar File")
    
        tar.extractall(path, members, numeric_owner=numeric_owner) 
        
    
    safe_extract(f, where)
    topdir = f.getnames()[0]
  return where + '/' + topdir
