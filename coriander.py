import pytest
import os
import shutil
import subprocess


# FIXME read from cli
# 0 - basic: dont run any solver
# 1 - std:   run only small cases
# 2 - extensive
test_level = 1

blockMesh  = 'blockMesh'
pisoFoam   = 'pisoFoam'
simpleFoam = 'simpleFoam'
mpirun     = "mpirun"

lastIterationCMD = 'grep "^Time" log | tail -n1'

controlDict   = 'system/controlDict'
fvSchemes     = 'system/fvSchemes'
transpProps   = 'constant/transportProperties'
RASproperties = 'constant/RASProperties'
chemistryProperties = 'constant/chemistryProperties'

FOAMVERS = os.environ.get('WM_PROJECT_VERSION',False)
STUDENTPC = ('tutpc' in os.environ.get('HOSTNAME'))

end = lambda x: 'Time = {}'.format(x)

changeEndTime = lambda x: subs('endTime[ 0-9.]*','endTime {}'.format(x), controlDict)

changeUnits = lambda x, fn: subs('\[\(\(-\| \)*[0-9]*\)*\]','[{}]'.format(x), fn)

changeViscosity = lambda x: subs('nu \[ 0 2 -1 0 0 0 0 \][ 0-9.]*','nu [ 0 2 -1 0 0 0 0 ] {}'.format(x), transpProps)

changeDeltaT = lambda x: subs('deltaT[ ]*1','deltaT {}'.format(x), controlDict)

RASTurbModel = lambda x: subs('RASModel[ A-Za-z]*','RASModel {}'.format(x), RASproperties)

TurbSwitch = lambda x: subs('turbulence[ A-Za-z]*','turbulence {}'.format(x), RASproperties)

chemistrySwitch = lambda x: subs('chemistry [a-z]*','chemistry {}'.format(x), chemistryProperties)

setUniformInternalField = lambda x, fn: subs('internalField[ ]*uniform[ 0-9.]*', 'internalField uniform {}'.format(x), fn)

uniformFixedValue = "{{type fixedValue; value uniform {};}}"
zeroGradientt = "{{type zeroGradient;{}}}"

def setBoundary(bcfield, bcname, bctype, bcvalue):
    return subs(
        "\({}\)".format(bcname) + "[ A-Za-z0-9.;{}]*",
        "\\1 {}".format(bctype.format(bcvalue)),
        bcfield)

def subs(org, new, fn):
    return 'sed -i "s/{}/{}/g" {}'.format(org, new, fn)

def derive_from_file(path, src, dest, units):
    shutil.copyfile(path + src, path + dest)
    execute_in_path(path, changeUnits(units, dest))

def execute_ret_output(cmd):
    return subprocess.getoutput(cmd)

def execute(cmd):
    return subprocess.check_call(cmd, shell=True) == 0

def get_tut_name_from_test_file(fn):
    return fn.replace('test_','').replace('.py','').split('/')[-1].upper() + "/FOAM/"

def execute_in_path(path, cmd, func=execute):
    old_dir = os.getcwd()
    os.chdir(path)
    try:
        ret = func(cmd)
    except:
        ret = False
    os.chdir(old_dir)
    return ret

def runSimulation(case_folder, cmd):
    assert execute_in_path(case_folder, cmd)
    lastIteration = execute_in_path(
            case_folder,
            lastIterationCMD,
            execute_ret_output
    )
    return lastIteration

def create_sol_folder(path):
    src = path + 'Case'
    dst = path + 'Sol'
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return dst + '/'

def copy_case_basics(src, dest):
    os.mkdir(dest)
    for d in ['/0', '/constant', '/system', '/chemistry']:
        try:
            shutil.copytree(src + d, dest + d)
        except Exception as e:
            print(e)

def test_openfoam_is_sourced():
    assert FOAMVERS

