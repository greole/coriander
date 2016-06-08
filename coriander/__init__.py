#!/usr/bin/python3
"""
coriander

Usage:
      coriander -h | --help
      coriander list

Options:
    -h  --help              Shows this screen
    --full                  Dislplays full output

"""
from docopt import docopt
import os
from humanize import naturalsize

def cli():
    args = docopt(__doc__)
    if args["list"]:
        list_files(".")

rule = "\n" + "-"*80

def list_files(startpath, full=False):
    print(header(startpath))
    last_parent = None
    for root, dirs, files in os.walk(startpath):
        dirs[:] = [d for d in dirs if "boundaryData" not in d]
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        if ".coriander" in dirs:
            parent = root.split("/")[-level:-1]
            if len(parent) > 0 and last_parent != parent:
                last_parent = parent
                print()
                print(parent[0]+ rule)

            dec = (True if "processor0" in dirs else False)
            procs = ("  " if not dec else "{}".format(len([_ for _ in dirs if "processor" in _])))
            time = " {0:.4f}".format(latest_time(root, dec))
            out = '{}{}/'.format(indent, os.path.basename(root)).ljust(45) + "| " + procs
            out += "  " + time + "  " + get_size(root, "processor")
            print(out)
        dirs[:] = [d for d in dirs if "processor" not in d]

def header(path):
    h = rule
    h += "\nCORIANDER CASES in "
    h += os.path.basename(os.path.abspath(path))
    f = h.ljust(45) + "| processor folder"
    f += rule
    return f


def latest_time(folder, dec):
   folder = (folder if not dec else folder + "/processor0")
   _, dirs, _ = next(os.walk(folder))
   time = [-1]
   for d in dirs:
       try:
           time.append((float(d)))
       except:
           pass
   return max(time)

def get_size(folder, name):
    _, dirs,_  = next(os.walk(folder))
    dirs = [d for d in dirs if name in d]
    sizes = [sum(os.path.getsize(os.path.join(dirpath,filename))
             for dirpath, dirnames, filenames in os.walk(os.path.join(folder,path))
             for filename in filenames)
             for path in dirs]
    return naturalsize(sum(sizes))
