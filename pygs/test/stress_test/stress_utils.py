import os
import sys

def get_mem_usage():
    """returns percentage and vsz mem usage of this script"""
    pid = os.getpid()
    psout = os.popen( "ps u -p %s"%pid ).read()
    
    parsed_psout = psout.split("\n")[1].split()
    
    return float(parsed_psout[3]), int( parsed_psout[4] )